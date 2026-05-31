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

try:
    from src.hrtf_engine import HRTFDatabase, MonauralSpatialEncoder
except ImportError:
    from hrtf_engine import HRTFDatabase, MonauralSpatialEncoder

try:
    from src.optimized_convolver import OverlapSaveConvolver
except ImportError:
    from optimized_convolver import OverlapSaveConvolver


class RealtimeProcessor:
    """Real-time stereo-to-mono spatial audio processor.

    Captures stereo input via sounddevice, separates left and right channels,
    encodes each with :class:`MonauralSpatialEncoder` at opposing azimuths
    (L at -30°, R at +30°), sums to mono with anti-clip normalisation, and
    writes the result to a mono output stream.

    Args:
        input_device: Input device index (``None`` = system default).
        output_device: Output device index (``None`` = system default).
        sample_rate: Sample rate in Hz. Must be > 0. Default 48000.
        block_size: Processing block size in samples. Must be a positive
            multiple of 64. Default 512.
        ear: Functional ear — ``"left"`` or ``"right"``. Default ``"left"``.

    Raises:
        ValueError: If *sample_rate* ≤ 0, *block_size* is not a positive
            multiple of 64, or *ear* is not ``"left"`` / ``"right"``.
    """

    def __init__(
        self,
        input_device: int | None = None,
        output_device: int | None = None,
        sample_rate: int = 48000,
        block_size: int = 512,
        ear: str = "left",
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

        # ── configuration ─────────────────────────────────────────────────
        self._input_device: int | None = input_device
        self._output_device: int | None = output_device
        self._sample_rate: int = sample_rate
        self._block_size: int = block_size
        self._ear: str = ear

        # ── HRTF engine (synthetic mode — no .sofa file required) ──────────
        self._hrtf_db: HRTFDatabase = HRTFDatabase("dummy.sofa", ear=ear)
        self._encoder: MonauralSpatialEncoder = MonauralSpatialEncoder(
            self._hrtf_db,
            sample_rate=sample_rate,
        )

        # ── precompute OverlapSaveConvolvers for each channel ────────────
        hrtf_left: np.ndarray = self._hrtf_db.get_filter(-30.0, 0.0)
        hrtf_right: np.ndarray = self._hrtf_db.get_filter(30.0, 0.0)
        self._convolver_left: OverlapSaveConvolver = OverlapSaveConvolver(
            hrtf_left, block_size=block_size,
        )
        self._convolver_right: OverlapSaveConvolver = OverlapSaveConvolver(
            hrtf_right, block_size=block_size,
        )

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
           3. Convolve each channel with its precomputed
              :class:`OverlapSaveConvolver` (L at -30° IR, R at +30° IR).
           4. Sum both encoded signals and apply anti-clip normalisation
              (peak limited to 0.95).
           5. Write the mono result to *outdata*.
           6. Measure callback interval; warn on stderr if > 11 ms.

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

        # Convolve each channel with precomputed HRTF via overlap-save FFT
        left_encoded: np.ndarray = self._convolver_left.process(left_ch)
        right_encoded: np.ndarray = self._convolver_right.process(right_ch)

        # Sum and anti-clip normalisation (peak limited to 0.95)
        mixed: np.ndarray = left_encoded + right_encoded
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
