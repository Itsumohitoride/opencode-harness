"""HRTF Engine for Rafear — HRTF database loading and monaural spatial encoding.

Provides two main classes:
  - HRTFDatabase: loads .sofa files via libmysofa, interpolates azimuth/elevation,
    caches filters. Falls back to synthetic HRTF when libmysofa is unavailable.
  - MonauralSpatialEncoder: applies HRTF convolution, spectral elevation cues,
    front-back cues, distance gain, and mixes multiple sources.

Dependencies:
  - numpy, scipy (required)
  - libmysofa (optional, for real .sofa file loading)

Example:
  >>> db = HRTFDatabase("subject.sofa", ear="left")
  >>> encoder = MonauralSpatialEncoder(db, sample_rate=48000)
  >>> signal = np.random.randn(48000).astype(np.float32)
  >>> out = encoder.encode_source(signal, azimuth=30.0, elevation=15.0)
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

try:
    import libmysofa

    _HAS_LIBMYSOFA = True
except ImportError:
    _HAS_LIBMYSOFA = False


def _validate_azimuth(azimuth: float) -> None:
    """Validate azimuth is within [-180, 180]."""
    if not -180.0 <= azimuth <= 180.0:
        raise ValueError(f"azimuth must be in [-180, 180], got {azimuth}")


def _validate_elevation(elevation: float) -> None:
    """Validate elevation is within [-90, 90]."""
    if not -90.0 <= elevation <= 90.0:
        raise ValueError(f"elevation must be in [-90, 90], got {elevation}")


def _validate_distance(distance: float) -> None:
    """Validate distance is >= 0.1."""
    if distance < 0.1:
        raise ValueError(f"distance must be >= 0.1, got {distance}")


def _synthetic_hrtf(
    azimuth: float,
    elevation: float,
    sample_rate: int = 48000,
) -> np.ndarray:
    """Generate a synthetic HRTF impulse response for testing.

    Produces a realistic-looking bandpass IR that varies with angle.
    Used when libmysofa is not available or no .sofa file is provided.

    Args:
        azimuth: Horizontal angle in degrees (-180 to 180).
        elevation: Vertical angle in degrees (-90 to 90).
        sample_rate: Sample rate in Hz.

    Returns:
        numpy.ndarray: Synthetic impulse response (float32, ~64 samples).
    """
    ir_len = min(64, sample_rate // 10)  # ~1.3ms at 48kHz
    t = np.arange(ir_len, dtype=np.float64) / sample_rate

    # Center frequency shifts with azimuth (simplified HRTF model)
    center_hz = 2000 + 1500 * np.sin(np.deg2rad(azimuth + 90))
    # Bandwidth varies with elevation
    bandwidth_hz = 1000 + 500 * np.sin(np.deg2rad(elevation + 45))

    # Simple gaussian-windowed tone as synthetic IR
    carrier = np.sin(2.0 * np.pi * center_hz * t)
    envelope = np.exp(-((t - 0.0005) ** 2) / (2.0 * (1.0 / bandwidth_hz) ** 2))

    ir = carrier * envelope
    # Normalize peak to 0 dB
    peak = np.max(np.abs(ir))
    if peak > 0:
        ir = ir / peak
    return ir.astype(np.float32)


_SYNTHETIC_SOS_CACHE: dict[float, Any] = {}


def _get_spectral_sos(
    elevation: float,
    sample_rate: int,
) -> np.ndarray | None:
    """Get SOS filter coefficients for spectral elevation cue.

    Args:
        elevation: Elevation angle in degrees.
        sample_rate: Sample rate in Hz.

    Returns:
        SOS array or None if no filtering needed.
    """
    if elevation > 20.0:
        # Boost 7.5-10.5 kHz for high elevations
        sos = butter(2, [7500, 10500], btype="bandpass", fs=sample_rate, output="sos")
        return sos
    elif elevation < -20.0:
        # Cut 3.5-6.5 kHz for low elevations
        sos = butter(2, [3500, 6500], btype="bandpass", fs=sample_rate, output="sos")
        return sos
    return None


class HRTFDatabase:
    """Loads HRTF data from .sofa files and interpolates filters.

    Uses libmysofa for actual .sofa loading. Falls back to synthetic
    HRTF when libmysofa is not installed.

    Caches interpolated filters by (azimuth, elevation) rounded to
    1 decimal place for fast reuse.
    """

    def __init__(self, sofa_path: str, ear: str = "left") -> None:
        """Initialize HRTFDatabase.

        Args:
            sofa_path: Path to .sofa HRTF file.
            ear: Ear to use — "left" (index 0) or "right" (index 1).

        Raises:
            FileNotFoundError: If .sofa file does not exist.
            ImportError: Propagated from libmysofa if not installed.
        """
        self._ear_index: int = 0 if ear == "left" else 1
        self._cache: dict[tuple[float, float], np.ndarray] = {}
        self._synthetic: bool = not _HAS_LIBMYSOFA
        self._sofa_path: str = sofa_path
        self._hrtf: Any = None

        if _HAS_LIBMYSOFA:
            try:
                self._hrtf = libmysofa.load(sofa_path)
            except FileNotFoundError:
                raise FileNotFoundError(f"HRTF .sofa file not found: {sofa_path}")
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to load HRTF .sofa file '{sofa_path}': {exc}"
                ) from exc
        else:
            # Synthetic mode: no file loading needed.
            # The sofa_path is stored for reference only.
            pass

    def get_filter(self, azimuth: float, elevation: float) -> np.ndarray:
        """Get HRTF filter for the given azimuth and elevation.

        Results are cached by (azimuth, elevation) rounded to 1 decimal.

        Args:
            azimuth: Horizontal angle in degrees (-180 to 180).
            elevation: Vertical angle in degrees (-90 to 90).

        Returns:
            Impulse response as float32 numpy array.

        Raises:
            ValueError: If azimuth or elevation are out of range.
        """
        _validate_azimuth(azimuth)
        _validate_elevation(elevation)

        key = (round(azimuth, 1), round(elevation, 1))
        if key in self._cache:
            return self._cache[key]

        if self._synthetic:
            ir = _synthetic_hrtf(azimuth, elevation)
        else:
            filter_left, filter_right, _ = self._hrtf.interpolate(
                azimuth, elevation, 0.0
            )
            ir = filter_left if self._ear_index == 0 else filter_right
            ir = np.asarray(ir, dtype=np.float32)

        self._cache[key] = ir
        return ir

    def get_filter_optimized(
        self, azimuth: float, elevation: float
    ) -> tuple[np.ndarray, np.ndarray]:
        """Get HRTF filter with precomputed FFT for optimized convolution.

        Args:
            azimuth: Horizontal angle in degrees (-180 to 180).
            elevation: Vertical angle in degrees (-90 to 90).

        Returns:
            Tuple of (impulse_response, ir_frequency_domain) as float32 arrays.
            ir_freq is the rfft of the IR zero-padded to the next power of 2.

        Raises:
            ValueError: If azimuth or elevation are out of range.
        """
        ir = self.get_filter(azimuth, elevation)
        fft_size = 2 ** int(np.ceil(np.log2(len(ir) + 512 - 1)))
        ir_freq = np.fft.rfft(ir, n=fft_size).astype(np.complex64)
        return ir, ir_freq

    @property
    def is_synthetic(self) -> bool:
        """Whether this database is using synthetic HRTF (fallback mode)."""
        return self._synthetic


class MonauralSpatialEncoder:
    """Applies spatial audio cues to mono signals using HRTF.

    Pipeline: HRTF convolution → spectral elevation cue → front-back cue
    → distance gain → output.
    """

    def __init__(self, hrtf_db: HRTFDatabase, sample_rate: int = 48000) -> None:
        """Initialize MonauralSpatialEncoder.

        Args:
            hrtf_db: HRTFDatabase instance for filter retrieval.
            sample_rate: Sample rate in Hz (default 48000).
        """
        self.hrtf_db: HRTFDatabase = hrtf_db
        self.sample_rate: int = sample_rate

    def apply_spectral_elevation_cue(
        self, signal: np.ndarray, elevation: float
    ) -> np.ndarray:
        """Apply spectral shaping that simulates elevation perception.

        Boosts 7.5-10.5 kHz band for elevations > 20° (pinna boosting).
        Attenuates 3.5-6.5 kHz band for elevations < -20°.

        Args:
            signal: Input audio signal (float32 1D array).
            elevation: Elevation angle in degrees (-90 to 90).

        Returns:
            Processed signal with spectral cues applied (same shape).

        Raises:
            ValueError: If elevation is out of range.
        """
        _validate_elevation(elevation)
        sos = _get_spectral_sos(elevation, self.sample_rate)
        if sos is None:
            return signal.copy().astype(np.float32)

        filtered = sosfilt(sos, signal.astype(np.float64))
        if elevation > 20.0:
            output = signal.astype(np.float32) + filtered.astype(np.float32) * 0.4
        else:
            output = signal.astype(np.float32) - filtered.astype(np.float32) * 0.3
        return output.astype(np.float32)

    def apply_front_back_cue(self, signal: np.ndarray, azimuth: float) -> np.ndarray:
        """Apply cues to differentiate front from back.

        For sounds behind (azimuth > 90° or < -90°):
          - Notch filter at 7.5-8.5 kHz (pinna shadow)
          - Short delay + attenuation to simulate rear reflection

        Args:
            signal: Input audio signal (float32 1D array).
            azimuth: Azimuth angle in degrees (-180 to 180).

        Returns:
            Processed signal (same shape).

        Raises:
            ValueError: If azimuth is out of range.
        """
        _validate_azimuth(azimuth)
        output = signal.copy().astype(np.float32)

        if abs(azimuth) > 90.0:
            # Notch filter at 7.5-8.5 kHz
            sos = butter(
                2, [7500, 8500], btype="bandstop", fs=self.sample_rate, output="sos"
            )
            output = sosfilt(sos, output.astype(np.float64)).astype(np.float32)

            # Short delay + reverb to simulate rear reflection (~12ms)
            delay_samples = int(0.012 * self.sample_rate)
            reverb = np.zeros_like(output)
            if delay_samples < len(output):
                reverb[delay_samples:] = output[:-delay_samples] * 0.25
            output = output + reverb
            output = output.astype(np.float32)

        return output

    def encode_source(
        self,
        signal: np.ndarray,
        azimuth: float,
        elevation: float,
        distance: float = 1.0,
    ) -> np.ndarray:
        """Full spatial encoding pipeline for one source.

        Applies: HRTF convolution → spectral elevation cue → front-back cue
        → distance gain.

        Args:
            signal: Input mono audio signal (float32 1D array).
            azimuth: Horizontal angle in degrees (-180 to 180).
            elevation: Vertical angle in degrees (-90 to 90).
            distance: Distance in meters (>= 0.1). Gain scales as 1/d^2.

        Returns:
            Spatially encoded audio signal (same length as input, float32).

        Raises:
            ValueError: If any parameter is out of range.
        """
        _validate_azimuth(azimuth)
        _validate_elevation(elevation)
        _validate_distance(distance)

        signal_f = signal.astype(np.float32)

        # Step 1: HRTF convolution
        hrtf_filter = self.hrtf_db.get_filter(azimuth, elevation)
        output = fftconvolve(signal_f, hrtf_filter, mode="same").astype(np.float32)

        # Step 2: Spectral elevation cue
        output = self.apply_spectral_elevation_cue(output, elevation)

        # Step 3: Front-back cue
        output = self.apply_front_back_cue(output, azimuth)

        # Step 4: Distance gain (1 / d^2)
        gain = 1.0 / max(1.0, distance**2)
        output = output * gain

        return output.astype(np.float32)

    def mix_sources(
        self, sources: list[tuple[np.ndarray, float, float, float]]
    ) -> np.ndarray:
        """Mix multiple spatial audio sources into a single mono signal.

        Each source is a tuple of (signal, azimuth, elevation, distance).
        Output is normalized to peak at 0.95 if clipping would occur.

        Args:
            sources: List of (signal, azimuth, elevation, distance) tuples.
                     Empty list returns zeros(1).

        Returns:
            Mixed mono signal (float32 1D array).
        """
        if not sources:
            return np.zeros(1, dtype=np.float32)

        max_len = max(len(s[0]) for s in sources)
        output = np.zeros(max_len, dtype=np.float64)

        for signal, azimuth, elevation, distance in sources:
            encoded = self.encode_source(signal, azimuth, elevation, distance)
            output[: len(encoded)] += encoded.astype(np.float64)

        # Normalize to prevent clipping (peak = 0.95)
        peak = float(np.max(np.abs(output)))
        if peak > 0.95 and peak > 0.0:
            output = output * (0.95 / peak)

        return output.astype(np.float32)
