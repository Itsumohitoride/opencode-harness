"""Realtime audio processor for MonoSpatial — captures stereo audio via
sounddevice, applies monaural spatial encoding per channel, and outputs
processed mono audio in real time.

Provides:
  - RealtimeProcessor: sounddevice stream manager with HRTF processing callback
  - parse_args: CLI argument parsing
  - main: entry point with Ctrl+C graceful shutdown

Dependencies:
  - sounddevice (installed with PortAudio backend)
  - numpy
  - hrtf_engine (MonauralSpatialEncoder, HRTFDatabase)

Example:
  >>> p = RealtimeProcessor(ear="left")
  >>> p.start()
  >>> # ... audio flows until Ctrl+C ...
  >>> p.stop()
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

import numpy as np
import sounddevice as sd
from scipy.signal import butter, sosfilt

try:
    from src.hrtf_engine import HRTFDatabase, MonauralSpatialEncoder
except ImportError:
    from hrtf_engine import HRTFDatabase, MonauralSpatialEncoder


class RealtimeProcessor:
    """Real-time stereo-to-mono spatial audio processor.

    Captures stereo input via sounddevice, separates left and right channels,
    applies head shadow filtering (ipsilateral passthrough, contralateral
    lowpass at ~4kHz), applies optional front/back cue (notch + delay),
    sums to mono with anti-clip normalisation, and writes the result to a
    mono output stream.

    Args:
        input_device: Input device index (``None`` = system default).
        output_device: Output device index (``None`` = system default).
        sample_rate: Sample rate in Hz. Must be > 0. Default 48000.
        block_size: Processing block size in samples. Must be a positive
            multiple of 64. Default 512.
        ear: Functional ear — ``"left"`` or ``"right"``. Default ``"left"``.
        fb_intensity: Front/back cue intensity 0.0-1.0. 0 = off. Default 0.3.
        elevation: Up/down elevation cue intensity 0.0-1.0. 0 = off.
            Default 0.3.
        lr_intensity: Left/right head shadow intensity 0.0-1.0.
            0 = no head shadow. Default 1.0 (full head shadow).
        clarity: Presence boost 3-5kHz clarity 0.0-1.0.
            0 = off. Default 0.0.

    Raises:
        ValueError: If *sample_rate* ≤ 0, *block_size* is not a positive
            multiple of 64, *ear* is not ``"left"`` / ``"right"``,
            *fb_intensity* is outside [0.0, 1.0], *elevation* is outside
            [0.0, 1.0], *lr_intensity* is outside [0.0, 1.0], or *clarity*
            is outside [0.0, 1.0].
    """

    def __init__(
        self,
        input_device: int | None = None,
        output_device: int | None = None,
        sample_rate: int = 48000,
        block_size: int = 512,
        ear: str = "left",
        fb_intensity: float = 0.3,
        elevation: float = 0.3,
        lr_intensity: float = 1.0,
        clarity: float = 0.0,
    ) -> None:
        # ── parameter validation ──────────────────────────────────────────
        if sample_rate <= 0:
            raise ValueError(f"sample_rate must be > 0, got {sample_rate}")
        if block_size <= 0 or block_size % 64 != 0:
            raise ValueError(
                f"block_size must be a positive multiple of 64, got {block_size}"
            )
        if ear not in ("left", "right"):
            raise ValueError(f"ear must be 'left' or 'right', got {ear!r}")
        if not 0.0 <= fb_intensity <= 1.0:
            raise ValueError(
                f"fb_intensity must be between 0.0 and 1.0, got {fb_intensity}"
            )
        if not 0.0 <= clarity <= 1.0:
            raise ValueError(
                f"clarity must be between 0.0 and 1.0, got {clarity}"
            )

        # ── configuration ─────────────────────────────────────────────────
        self._input_device: int | None = input_device
        self._output_device: int | None = output_device
        self._sample_rate: int = sample_rate
        self._block_size: int = block_size
        self._ear: str = ear

            # ── elevation (up/down) cue params ─────────────────────────────
        if not 0.0 <= elevation <= 1.0:
            raise ValueError(
                f"elevation must be between 0.0 and 1.0, got {elevation}"
            )
        self._elevation: float = elevation

        # ── clarity (presence boost) params ────────────────────────────────
        self._clarity: float = clarity  # 0.0-1.0, default 0.0

        # Presence boost SOS (bandpass 3-5kHz)
        self._presence_sos: np.ndarray = butter(
            2, [3000, 5000], btype="bandpass", fs=sample_rate, output="sos",
        )

        # ── lr_intensity (left/right head shadow) params ──────────────────
        if not 0.0 <= lr_intensity <= 1.0:
            raise ValueError(
                f"lr_intensity must be between 0.0 and 1.0, got {lr_intensity}"
            )
        self._lr_intensity: float = lr_intensity

        # Precompute bandpass SOS for elevation up (7.5-10.5kHz boost)
        self._elevation_up_sos: np.ndarray = butter(
            2, [7500, 10500], btype="bandpass", fs=sample_rate, output="sos",
        )

        # Precompute bandpass SOS for elevation down (3.5-6.5kHz cut)
        self._elevation_down_sos: np.ndarray = butter(
            2, [3500, 6500], btype="bandpass", fs=sample_rate, output="sos",
        )

        # ── front/back cue params ────────────────────────────────────────
        self._fb_intensity: float = fb_intensity

        # Precompute notch filter SOS for rear sounds (~8kHz pinna notch)
        self._rear_notch_sos: np.ndarray = butter(
            2, [7500, 8500], btype="bandstop", fs=sample_rate, output="sos",
        )

        # Precompute delay line for rear reflection (~12ms)
        self._rear_delay_samples: int = int(0.012 * sample_rate)

        # ── HRTF engine (synthetic mode — no .sofa file required) ──────────
        self._hrtf_db: HRTFDatabase = HRTFDatabase("dummy.sofa", ear=ear)
        self._encoder: MonauralSpatialEncoder = MonauralSpatialEncoder(
            self._hrtf_db,
            sample_rate=sample_rate,
        )

        # ── head shadow filter (precompute sos) ─────────────────────
        # Lowpass a ~4kHz simula la atenuacion de la cabeza
        # para el canal contralateral
        self._head_shadow_sos: np.ndarray = butter(
            2, 4000, btype="low", fs=sample_rate, output="sos",
        )

        # ── filter state (sosfilt zi persistence between blocks) ─────────
        # Avoids transient at block boundaries that causes low/high freq
        # interference when processing contralateral channel.
        # Initialised to None; first call uses zero state and stores zf.
        self._zi_left: np.ndarray | None = None
        self._zi_right: np.ndarray | None = None
        self._zi_rear_notch: np.ndarray | None = None
        self._zi_elevation_up: np.ndarray | None = None
        self._zi_elevation_down: np.ndarray | None = None
        self._zi_presence: np.ndarray | None = None

        # ── stream state ──────────────────────────────────────────────────
        self._stream: sd.Stream | None = None

        # ── latency tracking ──────────────────────────────────────────────
        self._last_callback_time: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_devices(self) -> list[dict[str, Any]]:
        """Query available audio devices.

        Returns:
            List of dictionaries, each with keys ``id``, ``name``,
            ``max_inputs``, ``max_outputs``, and ``default_samplerate``.
            Only devices with at least one input OR one output channel
            are included.
        """
        devices = sd.query_devices()
        result: list[dict[str, Any]] = []
        for idx, dev in enumerate(devices):
            if dev["max_input_channels"] > 0 or dev["max_output_channels"] > 0:
                result.append(
                    {
                        "id": idx,
                        "name": dev["name"],
                        "max_inputs": dev["max_input_channels"],
                        "max_outputs": dev["max_output_channels"],
                        "default_samplerate": dev["default_samplerate"],
                    }
                )
        return result

    def start(self) -> None:
        """Open and start the audio stream.

        Configures stereo input, mono output, and registers the internal
        processing callback.

        Raises:
            RuntimeError: If the stream is already active.
        """
        if self._stream is not None and self._stream.active:
            raise RuntimeError("Stream is already running")

        self._stream = sd.Stream(
            device=(self._input_device, self._output_device),
            samplerate=self._sample_rate,
            blocksize=self._block_size,
            channels=(2, 1),  # stereo in, mono out
            callback=self._process_block,
        )
        self._stream.start()

    def stop(self) -> None:
        """Stop and close the audio stream.

        Safe to call even when no stream is active.
        """
        if self._stream is not None:
            if self._stream.active:
                self._stream.stop()
            self._stream.close()
            self._stream = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """``True`` if the audio stream is currently active."""
        return self._stream is not None and self._stream.active

    @property
    def latency_ms(self) -> float:
        """Processing latency in milliseconds (``block_size / sample_rate * 1000``)."""
        return self._block_size / self._sample_rate * 1000.0

    # ------------------------------------------------------------------
    # Internal callback
    # ------------------------------------------------------------------

    def _process_block(
        self,
        indata: np.ndarray,
        outdata: np.ndarray,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags,
    ) -> None:
        """Process one audio block from the sounddevice stream.

        Pipeline:
           1. Report stream *status* issues to stderr (non-fatal).
           2. Split stereo input into left and right channels.
           3. Apply head shadow: ipsilateral channel passthrough,
              contralateral channel lowpass at ~4kHz.
              Filter state (``zi``) is persisted between blocks to
              avoid transient interference at block boundaries.
           4. Sum both channels.
           5. Apply front/back cue: notch at ~8kHz + delay + attenuation
              for rear-sound simulation (if ``_fb_intensity > 0``).
           6. Anti-clip normalisation (peak limited to 0.95).
           7. Write the mono result to *outdata*.
           8. Measure callback interval; warn on stderr if > 11 ms.

        Args:
            indata: Input buffer, shape ``(frames, 2)`` (stereo float32).
            outdata: Output buffer, shape ``(frames, 1)`` (mono float32).
            frames: Number of audio frames in this block.
            time_info: Sounddevice time-info object (unused).
            status: Sounddevice callback status.
        """
        if status:
            print(f"Stream status: {status}", file=sys.stderr)

        # Separate stereo channels
        left_ch: np.ndarray = indata[:, 0].astype(np.float32, copy=False)
        right_ch: np.ndarray = indata[:, 1].astype(np.float32, copy=False)

        # Head shadow model with intensity control:
        # Canal ipsolateral (oido funcional): passthrough (transparente)
        # Canal contralateral: lowpass ~4kHz (cabeza bloquea agudos)
        # El resultado filtrado se mezcla con el original según _lr_intensity
        if self._ear == "right":
            # Left channel is contralateral (right ear functional)
            left_filtered, self._zi_left = sosfilt(
                self._head_shadow_sos, left_ch,
                zi=self._zi_left
                if self._zi_left is not None
                else np.zeros((1, 2)),
            )
            left_filtered = left_filtered.astype(np.float32)
            # Blend original + filtered según lr_intensity
            left_encoded = left_ch.astype(np.float32) * (1.0 - self._lr_intensity) + left_filtered * self._lr_intensity
            right_encoded = right_ch.astype(np.float32)
        else:  # ear=left (default)
            left_encoded = left_ch.astype(np.float32)
            # Right channel is contralateral (left ear functional)
            right_filtered, self._zi_right = sosfilt(
                self._head_shadow_sos, right_ch,
                zi=self._zi_right
                if self._zi_right is not None
                else np.zeros((1, 2)),
            )
            right_filtered = right_filtered.astype(np.float32)
            # Blend original + filtered según lr_intensity
            right_encoded = right_ch.astype(np.float32) * (1.0 - self._lr_intensity) + right_filtered * self._lr_intensity

        # Presence boost para canal ipsolateral (claridad de voz/detalles)
        if self._clarity > 0:
            if self._ear == "right":
                # right ear functional -> right channel is ipsolateral
                presence, self._zi_presence = sosfilt(
                    self._presence_sos, right_ch,
                    zi=self._zi_presence if self._zi_presence is not None
                    else np.zeros((self._presence_sos.shape[0], 2)),
                )
                right_encoded = right_encoded.astype(np.float32) + presence.astype(np.float32) * self._clarity * 0.3
            else:  # ear=left
                presence, self._zi_presence = sosfilt(
                    self._presence_sos, left_ch,
                    zi=self._zi_presence if self._zi_presence is not None
                    else np.zeros((self._presence_sos.shape[0], 2)),
                )
                left_encoded = left_encoded.astype(np.float32) + presence.astype(np.float32) * self._clarity * 0.3

        # Sum both channels
        mixed: np.ndarray = left_encoded + right_encoded

        # Front/back cue (sutil, aplicado al mix completo)
        if self._fb_intensity > 0:
            # Notch ~8kHz (pinna shadow para sonidos detras)
            rear_notch, self._zi_rear_notch = sosfilt(
                self._rear_notch_sos, mixed,
                zi=self._zi_rear_notch
                if self._zi_rear_notch is not None
                else np.zeros((self._rear_notch_sos.shape[0], 2)),
            )
            # Delay + atenuacion para simulacion de reflexion trasera
            rear_reverb = np.zeros_like(mixed)
            if self._rear_delay_samples < len(mixed):
                rear_reverb[self._rear_delay_samples:] = (
                    mixed[:-self._rear_delay_samples] * 0.25 * self._fb_intensity
                )
            # Mezclar: senal original + version "trasera" atenuada
            mixed = mixed + (rear_notch * 0.3 + rear_reverb) * self._fb_intensity

        # Elevation cue (aplicado al mix completo)
        if self._elevation > 0:
            # Boost arriba (>20°): mezclar senal original + bandpass filtrado * 0.4
            up_filtered, self._zi_elevation_up = sosfilt(
                self._elevation_up_sos, mixed,
                zi=self._zi_elevation_up
                if self._zi_elevation_up is not None
                else np.zeros((self._elevation_up_sos.shape[0], 2)),
            )
            # Cut abajo (<-20°): restar bandpass filtrado * 0.3
            down_filtered, self._zi_elevation_down = sosfilt(
                self._elevation_down_sos, mixed,
                zi=self._zi_elevation_down
                if self._zi_elevation_down is not None
                else np.zeros((self._elevation_down_sos.shape[0], 2)),
            )
            # En la práctica real se usaría un azimuth/elevation por fuente,
            # pero aquí aplicamos ambos cues sutiles al mix completo para simular
            # ambiente 3D genérico (similar a cómo front/back cue se aplica al mix)
            mixed = mixed + (up_filtered * 0.4 - down_filtered * 0.3) * self._elevation

        # Anti-clip normalisation (peak limited to 0.95) — after all processing
        peak: float = float(np.max(np.abs(mixed)))
        if peak > 0.95 and peak > 0.0:
            mixed = mixed * (0.95 / peak)

        # Write to output buffer (mono)
        outdata[:] = mixed.reshape(-1, 1)

        # Latency monitoring
        now: float = time.perf_counter()
        if self._last_callback_time > 0:
            callback_interval_ms: float = (now - self._last_callback_time) * 1000.0
            if callback_interval_ms > 11.0:
                print(
                    f"Warning: callback interval {callback_interval_ms:.1f}ms "
                    f"exceeds 11ms",
                    file=sys.stderr,
                )
        self._last_callback_time = now


# =========================================================================
# CLI
# =========================================================================


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the realtime processor.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Parsed ``argparse.Namespace``.
    """
    parser = argparse.ArgumentParser(
        description="MonoSpatial — realtime monaural spatial audio processor",
    )
    parser.add_argument(
        "--input-device",
        type=int,
        default=None,
        help="Input device index (default: system default)",
    )
    parser.add_argument(
        "--output-device",
        type=int,
        default=None,
        help="Output device index (default: system default)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=48000,
        help="Sample rate in Hz (default: 48000)",
    )
    parser.add_argument(
        "--block-size",
        type=int,
        default=512,
        help="Block size in samples, must be multiple of 64 (default: 512)",
    )
    parser.add_argument(
        "--ear",
        type=str,
        default="left",
        choices=["left", "right"],
        help="Functional ear (default: left)",
    )
    parser.add_argument(
        "--fb-intensity",
        type=float,
        default=0.3,
        help="Front/back cue intensity 0.0-1.0 (default: 0.3, 0=off)",
    )
    parser.add_argument(
        "--ud-intensity",
        type=float,
        default=0.3,
        help="Up/down elevation cue intensity 0.0-1.0 (default: 0.3, 0=off)",
    )
    parser.add_argument(
        "--lr-intensity",
        type=float,
        default=1.0,
        help="Left/right head shadow intensity 0.0-1.0 (default: 1.0, 0=off)",
    )
    parser.add_argument(
        "--clarity",
        type=float,
        default=0.0,
        help="Presence boost 3-5kHz clarity 0.0-1.0 (default: 0.0, 0=off)",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio devices and exit",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Entry point for the realtime processor CLI.

    Parses arguments, optionally lists devices and exits, then creates
    a :class:`RealtimeProcessor` and runs until :class:`KeyboardInterrupt`.
    """
    args: argparse.Namespace = parse_args()

    # --list-devices mode
    if args.list_devices:
        _print_devices()
        return

    processor = RealtimeProcessor(
        input_device=args.input_device,
        output_device=args.output_device,
        sample_rate=args.sample_rate,
        block_size=args.block_size,
        ear=args.ear,
        fb_intensity=args.fb_intensity,
        elevation=args.ud_intensity,
        lr_intensity=args.lr_intensity,
        clarity=args.clarity,
    )

    try:
        print(
            f"Starting MonoSpatial realtime processor (ear={args.ear}, "
            f"sr={args.sample_rate}, block={args.block_size})...",
        )
        print("Press Ctrl+C to stop.")
        processor.start()
        while processor.is_running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        processor.stop()
        print("Stopped.")
        sys.stdout.flush()


def _print_devices() -> None:
    """Query and print available audio devices to stdout."""
    proc = RealtimeProcessor()
    devices = proc.list_devices()
    print(f"{'ID':<5} {'Name':<50} {'Inputs':<8} {'Outputs':<8} {'Rate':<10}")
    print("-" * 81)
    for dev in devices:
        rate_str: str = (
            f"{dev['default_samplerate']:.0f}" if dev["default_samplerate"] else "N/A"
        )
        print(
            f"{dev['id']:<5} {dev['name']:<50} "
            f"{dev['max_inputs']:<8} {dev['max_outputs']:<8} {rate_str:<10}",
        )


if __name__ == "__main__":
    main()
