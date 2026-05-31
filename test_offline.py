"""Offline spatial audio test — process stereo WAV files.

Reads a stereo WAV, separates channels into left and right sources,
applies monaural spatial encoding with opposite azimuths (±30°),
mixes to mono, and writes the result as a 16-bit mono WAV.

Dependencies:
  - numpy, soundfile
  - src.hrtf_engine (HRTFDatabase, MonauralSpatialEncoder)

Example:
  python src/test_offline.py input_stereo.wav output_mono.wav
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from src.hrtf_engine import HRTFDatabase, MonauralSpatialEncoder


def process_file(
    input_path: str,
    output_path: str,
    sample_rate: int = 48000,
) -> None:
    """Process a stereo WAV file through spatial encoding.

    Reads a stereo WAV, encodes left channel at -30° azimuth and
    right channel at +30° azimuth (elevation=0°, distance=1.0),
    mixes to mono with anti-clip normalization, and writes as
    16-bit mono WAV.

    Args:
        input_path: Path to input stereo WAV file.
        output_path: Path for output mono WAV file.
        sample_rate: Sample rate in Hz (default 48000).

    Raises:
        FileNotFoundError: If input file does not exist.
        ValueError: If input audio is not stereo (not 2 channels).
        sf.SoundFileError: If file format is invalid.
    """
    input_path_obj = Path(input_path)
    if not input_path_obj.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Read input WAV
    data, file_sr = sf.read(str(input_path_obj))
    if data.ndim != 2 or data.shape[1] != 2:
        raise ValueError(f"Input must be stereo (2 channels), got shape {data.shape}")

    # Separate channels
    left_channel: np.ndarray = data[:, 0].astype(np.float32)
    right_channel: np.ndarray = data[:, 1].astype(np.float32)

    # Initialize HRTF engine (synthetic mode)
    hrtf_db = HRTFDatabase(sofa_path="", ear="left")
    encoder = MonauralSpatialEncoder(hrtf_db, sample_rate=sample_rate)

    # Encode each source with opposite azimuths
    encoded_left = encoder.encode_source(
        left_channel, azimuth=-30.0, elevation=0.0, distance=1.0
    )
    encoded_right = encoder.encode_source(
        right_channel, azimuth=30.0, elevation=0.0, distance=1.0
    )

    # Mix to mono with anti-clip normalization
    mixed: np.ndarray = encoded_left.astype(np.float64) + encoded_right.astype(
        np.float64
    )
    peak = float(np.max(np.abs(mixed)))
    if peak > 1.0 and peak > 0.0:
        mixed = mixed / peak

    # Write output as 16-bit mono WAV
    sf.write(
        str(Path(output_path)),
        mixed.astype(np.float32),
        sample_rate,
        subtype="PCM_16",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with input_path and output_path attributes.
    """
    parser = argparse.ArgumentParser(
        description="MonoSpatial — Offline spatial audio test",
    )
    parser.add_argument(
        "input_path",
        type=str,
        help="Path to input stereo WAV file",
    )
    parser.add_argument(
        "output_path",
        type=str,
        help="Path for output mono WAV file",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=48000,
        dest="sample_rate",
        help="Sample rate in Hz (default: 48000)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point for CLI.

    Args:
        argv: Optional argument list (for testing). Defaults to sys.argv[1:].
    """
    args = parse_args(argv)
    try:
        process_file(
            input_path=args.input_path,
            output_path=args.output_path,
            sample_rate=args.sample_rate,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except sf.SoundFileError as e:
        print(f"Error: Invalid audio file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
