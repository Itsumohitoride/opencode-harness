"""Overlap-save FFT convolver optimized for low-latency audio processing.

MonoSpatial uses this module for HRTF convolution with block-based audio
processing. The ``OverlapSaveConvolver`` precomputes the FFT of the impulse
response and maintains overlap state between blocks to deliver continuous
linear convolution with minimum latency.

Typical usage::

    convolver = OverlapSaveConvolver(ir, block_size=512)
    output = convolver.process(input_block)
    convolver.reset()

Dependencies: numpy
"""

from __future__ import annotations

import numpy as np


def _next_power_of_two(x: int) -> int:
    """Return the smallest power of two that is >= *x*.

    Args:
        x: A positive integer.

    Returns:
        The next power of two.
    """
    return 1 << (x - 1).bit_length()


class OverlapSaveConvolver:
    """FFT-based overlap-save convolution optimized for low latency.

    Precomputes the impulse-response FFT once and processes audio in
    blocks of *block_size* samples.  An internal state buffer carries
    the filter tail across consecutive ``process()`` calls so that the
    overall result is equivalent to a single full linear convolution.

    Args:
        ir: Impulse response — 1-D float32 array.  Any length is
            supported (non-power-of-two included).
        block_size: Processing block size in samples.  Must be > 0
            and either a power of two or a multiple of 64.
            Defaults to 512.
        sample_rate: Audio sample rate in Hz.  Only used to compute
            the :attr:`latency_ms` property.  Defaults to 48000.

    Raises:
        ValueError: If *ir* is not a 1-D float32 array, if it is
            empty, or if *block_size* is not valid.
    """

    def __init__(
        self,
        ir: np.ndarray,
        block_size: int = 512,
        sample_rate: int = 48000,
    ) -> None:
        # --- validate ir ---------------------------------------------------
        if not isinstance(ir, np.ndarray) or ir.ndim != 1:
            raise ValueError(f"ir must be a 1-D numpy array, got {ir.ndim}D")
        if ir.dtype != np.float32:
            raise ValueError(f"ir must be float32, got {ir.dtype}")
        if ir.shape[0] == 0:
            raise ValueError("ir must not be empty")

        # --- validate block_size -------------------------------------------
        if block_size <= 0:
            raise ValueError(f"block_size must be > 0, got {block_size}")
        is_power_of_two = (block_size & (block_size - 1)) == 0
        is_multiple_of_64 = block_size % 64 == 0
        if not (is_power_of_two or is_multiple_of_64):
            raise ValueError(
                f"block_size must be a power of 2 or a multiple of 64, got {block_size}"
            )

        # --- store configuration -------------------------------------------
        self._ir_len: int = ir.shape[0]
        self._block_size: int = block_size
        self._sample_rate: int = sample_rate

        # --- precompute FFT of ir ------------------------------------------
        # FFT size must be >= M + B - 1 to hold the linear convolution result
        fft_len = _next_power_of_two(self._ir_len + block_size - 1)
        self._H: np.ndarray = np.fft.rfft(ir.astype(np.float32, copy=False), n=fft_len)
        self._fft_len: int = fft_len

        # --- overlap state (last M-1 input samples) ------------------------
        self._state: np.ndarray = np.zeros(max(self._ir_len - 1, 0), dtype=np.float32)

        # --- pre-allocated working buffer ----------------------------------
        self._segment: np.ndarray = np.zeros(fft_len, dtype=np.float32)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def latency_samples(self) -> int:
        """Latency in samples — always one *block_size*."""
        return self._block_size

    @property
    def latency_ms(self) -> float:
        """Latency in milliseconds at the configured sample rate."""
        return self._block_size / self._sample_rate * 1000.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, block: np.ndarray) -> np.ndarray:
        """Process one block of audio.

        Args:
            block: Input block — 1-D float32 array whose length must
                equal *block_size*.

        Returns:
            1-D float32 array of the same length as **block**.

        Raises:
            ValueError: If **block** is not a 1-D float32 array or
                has the wrong length.
        """
        B = self._block_size
        M = self._ir_len
        N = self._fft_len

        # --- validate block ------------------------------------------------
        if not isinstance(block, np.ndarray) or block.ndim != 1:
            raise ValueError(f"block must be a 1-D numpy array, got {block.ndim}D")
        if block.dtype != np.float32:
            raise ValueError(f"block must be float32, got {block.dtype}")
        if block.shape[0] != B:
            raise ValueError(f"block must have length {B}, got {block.shape[0]}")

        # --- build extended segment ----------------------------------------
        #  [overlap state (M-1) | block (B) | zeros to FFT length]
        self._segment[: M - 1] = self._state
        self._segment[M - 1 : M - 1 + B] = block
        self._segment[M - 1 + B :] = 0

        # --- FFT → multiply → IFFT -----------------------------------------
        S = np.fft.rfft(self._segment)
        Y = S * self._H
        y = np.fft.irfft(Y, n=N)

        # --- valid output (skip first M-1 contaminated samples) ------------
        out = y[M - 1 : M - 1 + B].copy()

        # --- update state (last M-1 input samples) -------------------------
        if M > 1:
            if B >= M - 1:
                self._state[:] = block[-(M - 1) :]
            else:
                # B < M-1 : keep (M-1-B) old samples + B new samples
                n_keep = (M - 1) - B
                self._state[:n_keep] = self._state[B:]
                self._state[n_keep:] = block

        return out

    def reset(self) -> None:
        """Reset the overlap state to zeros.

        Call this when switching between audio sources to prevent
        filter ringing from the previous source bleeding into the
        new signal.
        """
        self._state.fill(0.0)
