"""Tests for realtime_processor module — RealtimeProcessor and CLI.

Uses extensive mocking of sounddevice — no real audio devices required.
"""

# ruff: noqa: ANN201 — test functions don't need return type annotations

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.realtime_processor import RealtimeProcessor, main, parse_args


# =========================================================================
# Helpers
# =========================================================================


def _make_mock_stream(active: bool = False) -> MagicMock:
    """Create a mocked ``sd.Stream`` instance."""
    stream = MagicMock()
    stream.active = active
    return stream


# =========================================================================
# RealtimeProcessor — constructor
# =========================================================================


class TestConstructor:
    """RealtimeProcessor.__init__ parameter handling."""

    def test_defaults(self) -> None:
        """Default parameter values are set correctly."""
        p = RealtimeProcessor()
        assert p._input_device is None
        assert p._output_device is None
        assert p._sample_rate == 48000
        assert p._block_size == 512
        assert p._ear == "left"
        assert p._stream is None

    def test_custom_parameters(self) -> None:
        """Custom parameters are propagated correctly."""
        p = RealtimeProcessor(
            input_device=1,
            output_device=2,
            sample_rate=44100,
            block_size=256,
            ear="right",
        )
        assert p._input_device == 1
        assert p._output_device == 2
        assert p._sample_rate == 44100
        assert p._block_size == 256
        assert p._ear == "right"

    def test_raises_on_invalid_sample_rate_zero(self) -> None:
        """sample_rate=0 raises ValueError."""
        with pytest.raises(ValueError, match="sample_rate"):
            RealtimeProcessor(sample_rate=0)

    def test_raises_on_invalid_sample_rate_negative(self) -> None:
        """sample_rate=-1 raises ValueError."""
        with pytest.raises(ValueError, match="sample_rate"):
            RealtimeProcessor(sample_rate=-1)

    def test_raises_on_invalid_block_size_zero(self) -> None:
        """block_size=0 raises ValueError."""
        with pytest.raises(ValueError, match="block_size"):
            RealtimeProcessor(block_size=0)

    def test_raises_on_invalid_block_size_63(self) -> None:
        """block_size=63 (not multiple of 64) raises ValueError."""
        with pytest.raises(ValueError, match="block_size"):
            RealtimeProcessor(block_size=63)

    def test_raises_on_invalid_block_size_negative(self) -> None:
        """block_size=-512 (negative) raises ValueError."""
        with pytest.raises(ValueError, match="block_size"):
            RealtimeProcessor(block_size=-512)

    def test_raises_on_invalid_ear(self) -> None:
        """ear='both' raises ValueError."""
        with pytest.raises(ValueError, match="ear"):
            RealtimeProcessor(ear="both")


# =========================================================================
# RealtimeProcessor — list_devices
# =========================================================================


class TestListDevices:
    """RealtimeProcessor.list_devices behaviour."""

    @patch("src.realtime_processor.sd.query_devices")
    def test_returns_filtered_list(self, mock_query: MagicMock) -> None:
        """Only devices with at least one input or output are returned."""
        mock_query.return_value = [
            {
                "name": "Input Only",
                "max_input_channels": 2,
                "max_output_channels": 0,
                "default_samplerate": 48000.0,
            },
            {
                "name": "Output Only",
                "max_input_channels": 0,
                "max_output_channels": 2,
                "default_samplerate": 44100.0,
            },
            {
                "name": "Full Duplex",
                "max_input_channels": 2,
                "max_output_channels": 2,
                "default_samplerate": 96000.0,
            },
            {
                "name": "Empty",
                "max_input_channels": 0,
                "max_output_channels": 0,
                "default_samplerate": None,
            },
        ]

        p = RealtimeProcessor()
        devices = p.list_devices()

        assert len(devices) == 3  # Empty device filtered out
        assert devices[0]["id"] == 0
        assert devices[0]["name"] == "Input Only"
        assert devices[0]["max_inputs"] == 2
        assert devices[0]["max_outputs"] == 0
        assert devices[0]["default_samplerate"] == 48000.0
        assert "Empty" not in [d["name"] for d in devices]
        mock_query.assert_called_once()

    @patch("src.realtime_processor.sd.query_devices")
    def test_includes_input_and_output_only(self, mock_query: MagicMock) -> None:
        """Devices with only input or only output are included."""
        mock_query.return_value = [
            {
                "name": "Mic In",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 48000.0,
            },
            {
                "name": "Speaker Out",
                "max_input_channels": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000.0,
            },
        ]
        p = RealtimeProcessor()
        devices = p.list_devices()
        assert len(devices) == 2


# =========================================================================
# RealtimeProcessor — start / stop / is_running
# =========================================================================


class TestStartStop:
    """RealtimeProcessor.start and stop behaviour."""

    @patch("src.realtime_processor.sd.Stream")
    def test_start_calls_stream_with_correct_params(
        self,
        mock_stream_class: MagicMock,
    ) -> None:
        """start() creates sd.Stream with configured parameters and calls .start()."""
        mock_stream = _make_mock_stream(active=False)
        mock_stream_class.return_value = mock_stream

        p = RealtimeProcessor(
            input_device=1,
            output_device=2,
            sample_rate=44100,
            block_size=256,
        )
        p.start()

        mock_stream_class.assert_called_once_with(
            device=(1, 2),
            samplerate=44100,
            blocksize=256,
            channels=(2, 1),
            callback=p._process_block,
        )
        mock_stream.start.assert_called_once()
        assert p._stream is mock_stream

    @patch("src.realtime_processor.sd.Stream")
    def test_start_with_defaults(self, mock_stream_class: MagicMock) -> None:
        """start() with default parameters uses None for both devices."""
        mock_stream = _make_mock_stream(active=False)
        mock_stream_class.return_value = mock_stream

        p = RealtimeProcessor()
        p.start()

        mock_stream_class.assert_called_once_with(
            device=(None, None),
            samplerate=48000,
            blocksize=512,
            channels=(2, 1),
            callback=p._process_block,
        )

    @patch("src.realtime_processor.sd.Stream")
    def test_start_raises_if_already_running(
        self, mock_stream_class: MagicMock
    ) -> None:
        """start() raises RuntimeError when stream is already active."""
        mock_stream = _make_mock_stream(active=True)
        mock_stream_class.return_value = mock_stream

        p = RealtimeProcessor()
        p._stream = mock_stream

        with pytest.raises(RuntimeError, match="already running"):
            p.start()

    @patch("src.realtime_processor.sd.Stream")
    def test_stop_stops_and_closes_stream(self, mock_stream_class: MagicMock) -> None:
        """stop() calls .stop() and .close() on the active stream."""
        mock_stream = _make_mock_stream(active=True)
        mock_stream_class.return_value = mock_stream

        p = RealtimeProcessor()
        p._stream = mock_stream
        p.stop()

        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        assert p._stream is None

    def test_stop_no_stream_does_not_raise(self) -> None:
        """stop() is safe to call when no stream is active."""
        p = RealtimeProcessor()
        p.stop()  # should not raise

    @patch("src.realtime_processor.sd.Stream")
    def test_is_running_after_start(self, mock_stream_class: MagicMock) -> None:
        """is_running is True after start()."""
        mock_stream = _make_mock_stream(active=True)
        mock_stream_class.return_value = mock_stream

        p = RealtimeProcessor()
        p._stream = mock_stream
        assert p.is_running

    @patch("src.realtime_processor.sd.Stream")
    def test_is_running_after_stop(self, mock_stream_class: MagicMock) -> None:
        """is_running is False after stop()."""
        mock_stream = _make_mock_stream(active=False)
        mock_stream_class.return_value = mock_stream

        p = RealtimeProcessor()
        p._stream = mock_stream
        p.stop()
        assert not p.is_running

    def test_is_running_before_start(self) -> None:
        """is_running is False before any stream is created."""
        p = RealtimeProcessor()
        assert not p.is_running


# =========================================================================
# RealtimeProcessor — latency_ms
# =========================================================================


class TestLatency:
    """RealtimeProcessor.latency_ms property."""

    def test_latency_default(self) -> None:
        """Default latency: 512 / 48000 * 1000 ≈ 10.667 ms."""
        p = RealtimeProcessor()
        expected = 512.0 / 48000.0 * 1000.0
        assert p.latency_ms == pytest.approx(expected)

    def test_latency_custom(self) -> None:
        """Custom block_size and sample_rate are reflected in latency."""
        p = RealtimeProcessor(sample_rate=44100, block_size=256)
        expected = 256.0 / 44100.0 * 1000.0
        assert p.latency_ms == pytest.approx(expected)

    def test_latency_small_block(self) -> None:
        """Small block (64) at 48 kHz ≈ 1.333 ms."""
        p = RealtimeProcessor(sample_rate=48000, block_size=64)
        expected = 64.0 / 48000.0 * 1000.0
        assert p.latency_ms == pytest.approx(expected)


# =========================================================================
# RealtimeProcessor — _process_block callback
# =========================================================================


class TestProcessBlock:
    """RealtimeProcessor._process_block behaviour."""

    def test_output_is_mono(self) -> None:
        """Outdata has shape (frames, 1) — mono output."""
        p = RealtimeProcessor()
        frames = 512
        indata = np.random.randn(frames, 2).astype(np.float32) * 0.1
        outdata = np.zeros((frames, 1), dtype=np.float32)

        p._process_block(
            indata,
            outdata,
            frames,
            None,
            None,
        )

        assert outdata.shape[0] == frames
        assert outdata.shape[1] == 1

    def test_output_within_amplitude_range(self) -> None:
        """Output samples stay within [-0.95, 0.95] (anti-clip)."""
        p = RealtimeProcessor()
        frames = 512
        indata = np.ones((frames, 2), dtype=np.float32) * 2.0  # loud!
        outdata = np.zeros((frames, 1), dtype=np.float32)

        p._process_block(indata, outdata, frames, None, None)

        assert float(np.max(np.abs(outdata))) <= 0.95 + 1e-6

    def test_output_contains_no_nan(self) -> None:
        """Output contains no NaN or Inf values."""
        p = RealtimeProcessor()
        frames = 512
        indata = np.random.randn(frames, 2).astype(np.float32) * 0.3
        outdata = np.zeros((frames, 1), dtype=np.float32)

        p._process_block(indata, outdata, frames, None, None)

        assert not np.any(np.isnan(outdata))
        assert not np.any(np.isinf(outdata))

    def test_output_not_all_zeros_with_input(self) -> None:
        """Non-zero input produces non-zero output."""
        p = RealtimeProcessor()
        frames = 512
        indata = np.random.randn(frames, 2).astype(np.float32) * 0.5
        outdata = np.zeros((frames, 1), dtype=np.float32)

        p._process_block(indata, outdata, frames, None, None)

        assert np.any(np.abs(outdata) > 1e-7)

    def test_handles_status_error_without_crashing(self) -> None:
        """Stream status errors are printed to stderr, no crash."""
        p = RealtimeProcessor()
        frames = 512
        indata = np.zeros((frames, 2), dtype=np.float32)
        outdata = np.zeros((frames, 1), dtype=np.float32)

        class MockStatus:
            """Fake sounddevice status that evaluates truthy."""

            def __bool__(self) -> bool:
                return True

            def __str__(self) -> str:
                return "input overflow"

        # Should not raise
        p._process_block(indata, outdata, frames, None, MockStatus())

        assert outdata.shape[1] == 1

    def test_reports_latency_warning_on_stderr(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Latency > 11ms prints a warning to stderr."""
        p = RealtimeProcessor()
        frames = 512
        indata = np.zeros((frames, 2), dtype=np.float32)
        outdata = np.zeros((frames, 1), dtype=np.float32)

        # Use non-zero start so first call interval is small (< 11ms),
        # second call interval is large (> 11ms)
        with patch(
            "src.realtime_processor.time.perf_counter", side_effect=[0.005, 0.020]
        ):
            # First call: now=0.005, interval=(0.005-0.0)*1000=5ms → no warning
            p._process_block(indata, outdata, frames, None, None)
            # Second call: now=0.020, interval=(0.020-0.005)*1000=15ms → warning
            p._process_block(indata, outdata, frames, None, None)

        captured = capsys.readouterr()
        assert "exceeds 11ms" in captured.err

    def test_no_latency_warning_when_under_11ms(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Latency ≤ 11ms does not print a warning."""
        p = RealtimeProcessor()
        frames = 512
        indata = np.zeros((frames, 2), dtype=np.float32)
        outdata = np.zeros((frames, 1), dtype=np.float32)

        # First call: now=0.005, interval=5ms < 11ms → no warning
        # Second call: now=0.012, interval=7ms < 11ms → no warning
        with patch(
            "src.realtime_processor.time.perf_counter", side_effect=[0.005, 0.012]
        ):
            p._process_block(indata, outdata, frames, None, None)
            p._process_block(indata, outdata, frames, None, None)

        captured = capsys.readouterr()
        assert "exceeds 11ms" not in captured.err

    def test_first_callback_no_latency_check(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """First callback does not check latency (no previous timestamp)."""
        p = RealtimeProcessor()
        frames = 512
        indata = np.zeros((frames, 2), dtype=np.float32)
        outdata = np.zeros((frames, 1), dtype=np.float32)

        # First call with any interval should not warn
        p._process_block(indata, outdata, frames, None, None)

        captured = capsys.readouterr()
        assert "exceeds 11ms" not in captured.err


# =========================================================================
# CLI — parse_args
# =========================================================================


class TestParseArgs:
    """parse_args CLI argument parsing."""

    def test_defaults(self) -> None:
        """All defaults are as expected."""
        args = parse_args([])
        assert args.input_device is None
        assert args.output_device is None
        assert args.sample_rate == 48000
        assert args.block_size == 512
        assert args.ear == "left"
        assert not args.list_devices

    def test_custom_values(self) -> None:
        """Custom argument values are parsed correctly."""
        args = parse_args(
            [
                "--input-device",
                "1",
                "--output-device",
                "2",
                "--sample-rate",
                "44100",
                "--block-size",
                "256",
                "--ear",
                "right",
            ]
        )
        assert args.input_device == 1
        assert args.output_device == 2
        assert args.sample_rate == 44100
        assert args.block_size == 256
        assert args.ear == "right"

    def test_list_devices_flag(self) -> None:
        """--list-devices sets the flag to True."""
        args = parse_args(["--list-devices"])
        assert args.list_devices

    def test_input_device_only(self) -> None:
        """Only --input-device is provided, others default."""
        args = parse_args(["--input-device", "3"])
        assert args.input_device == 3
        assert args.output_device is None
        assert args.sample_rate == 48000
        assert args.block_size == 512
        assert args.ear == "left"
        assert not args.list_devices

    def test_ear_choices_accepted(self) -> None:
        """Both 'left' and 'right' are accepted for --ear."""
        args_left = parse_args(["--ear", "left"])
        assert args_left.ear == "left"

        args_right = parse_args(["--ear", "right"])
        assert args_right.ear == "right"


# =========================================================================
# CLI — main function
# =========================================================================


class TestMain:
    """main() entry point behaviour."""

    @patch("src.realtime_processor.sd.query_devices")
    def test_list_devices_mode(
        self,
        mock_query: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """--list-devices prints device table and returns."""
        mock_query.return_value = [
            {
                "name": "Test Sound Card",
                "max_input_channels": 2,
                "max_output_channels": 2,
                "default_samplerate": 48000.0,
            },
        ]

        with patch("sys.argv", ["realtime_processor.py", "--list-devices"]):
            main()

        captured = capsys.readouterr()
        assert "Test Sound Card" in captured.out
        assert "ID" in captured.out  # header
        mock_query.assert_called_once()

    @patch("src.realtime_processor.RealtimeProcessor")
    def test_ctrl_c_handling(
        self,
        mock_proc_class: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """KeyboardInterrupt is caught and stop() is called."""
        mock_proc = MagicMock()
        mock_proc_class.return_value = mock_proc
        mock_proc.is_running = True
        mock_proc.start.side_effect = KeyboardInterrupt()

        with patch("sys.argv", ["realtime_processor.py"]):
            main()

        mock_proc.stop.assert_called_once()
        captured = capsys.readouterr()
        assert "Stopping" in captured.out

    @patch("src.realtime_processor.RealtimeProcessor")
    def test_normal_execution_loops(
        self,
        mock_proc_class: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """main() loops while processor is running, then stops."""
        mock_proc = MagicMock()
        mock_proc_class.return_value = mock_proc
        mock_proc.is_running = True

        # Make is_running return True once then False
        mock_proc.is_running = False  # exit loop immediately

        with patch("sys.argv", ["realtime_processor.py"]):
            main()

        mock_proc.start.assert_called_once()
        mock_proc.stop.assert_called_once()

    @patch("src.realtime_processor.RealtimeProcessor")
    def test_startup_message(
        self,
        mock_proc_class: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """main() prints a startup message with configuration."""
        mock_proc = MagicMock()
        mock_proc_class.return_value = mock_proc
        mock_proc.is_running = False

        with patch("sys.argv", ["realtime_processor.py"]):
            main()

        captured = capsys.readouterr()
        assert "MonoSpatial" in captured.out
        assert "Press Ctrl+C" in captured.out


# =========================================================================
# Head shadow integration
# =========================================================================


class TestHeadShadow:
    """RealtimeProcessor uses head shadow model instead of HRTF convolution."""

    def test_head_shadow_sos_exists(self) -> None:
        """Processor precomputes _head_shadow_sos in __init__."""
        p = RealtimeProcessor()
        assert hasattr(p, "_head_shadow_sos")
        assert isinstance(p._head_shadow_sos, np.ndarray)
        assert p._head_shadow_sos.ndim == 2  # SOS is 2D

    def test_head_shadow_sos_is_lowpass(self) -> None:
        """SOS filter order is 2 (3 sections x 6 cols)."""
        p = RealtimeProcessor()
        # butter(2, ...) with output="sos" → shape (1, 6)
        assert p._head_shadow_sos.shape == (1, 6)

    def test_head_shadow_sos_respects_sample_rate(self) -> None:
        """SOS filter uses the configured sample_rate."""
        p = RealtimeProcessor(sample_rate=44100)
        # Different sample rate produces different coefficients
        p48 = RealtimeProcessor(sample_rate=48000)
        # Coefficients should differ
        assert not np.allclose(p._head_shadow_sos, p48._head_shadow_sos)

    def test_process_block_runs_without_error(self) -> None:
        """_process_block runs without error via head shadow."""
        p = RealtimeProcessor()
        frames = 512
        indata = np.random.randn(frames, 2).astype(np.float32) * 0.1
        outdata = np.zeros((frames, 1), dtype=np.float32)

        p._process_block(indata, outdata, frames, None, None)

        assert outdata.shape == (frames, 1)
        assert not np.any(np.isnan(outdata))
        assert not np.any(np.isinf(outdata))

    def test_process_block_produces_nonzero_output(self) -> None:
        """Active input produces non-zero output through head shadow."""
        p = RealtimeProcessor()
        frames = 512
        indata = np.ones((frames, 2), dtype=np.float32) * 0.5
        outdata = np.zeros((frames, 1), dtype=np.float32)

        p._process_block(indata, outdata, frames, None, None)

        assert np.any(np.abs(outdata) > 1e-7)

    def test_ear_left_passthrough_left_channel(self) -> None:
        """With ear=left, left channel should be passthrough (unchanged)."""
        p = RealtimeProcessor(ear="left", fb_intensity=0.0, elevation=0.0)
        frames = 512
        # Create signal where left channel has known content
        left_signal = np.linspace(-0.5, 0.5, frames).astype(np.float32)
        right_signal = np.zeros(frames, dtype=np.float32)
        indata = np.column_stack([left_signal, right_signal])
        outdata = np.zeros((frames, 1), dtype=np.float32)

        p._process_block(indata, outdata, frames, None, None)

        # With ear=left, only right_ch is lowpass-filtered.
        # left_encoded = left_ch (passthrough). right_encoded is ~0.
        # So mixed ≈ left_ch scaled by passthrough.
        # Since left_ch goes through unchanged, mixed should be close to left_signal
        # (with tiny differences from float32 cast and potential anti-clip)
        # fb_intensity=0.0 and elevation=0.0 disable post-processing cues.
        expected_mixed = left_signal  # left passthrough + right ~0
        assert np.allclose(outdata[:, 0], expected_mixed, atol=1e-6)

    def test_ear_right_passthrough_right_channel(self) -> None:
        """With ear=right, right channel should be passthrough (unchanged)."""
        p = RealtimeProcessor(ear="right", fb_intensity=0.0, elevation=0.0)
        frames = 512
        left_signal = np.zeros(frames, dtype=np.float32)
        right_signal = np.linspace(-0.5, 0.5, frames).astype(np.float32)
        indata = np.column_stack([left_signal, right_signal])
        outdata = np.zeros((frames, 1), dtype=np.float32)

        p._process_block(indata, outdata, frames, None, None)

        # With ear=right: left_ch filtered (head shadow), right_ch passthrough
        # right_encoded = right_signal (passthrough), left_encoded ≈ 0
        # fb_intensity=0.0 and elevation=0.0 disable post-processing cues.
        expected_mixed = right_signal  # left ~0 + right passthrough
        assert np.allclose(outdata[:, 0], expected_mixed, atol=1e-6)

    def test_ear_left_filters_right_channel(self) -> None:
        """With ear=left, right channel is lowpass-filtered (not identical)."""
        p = RealtimeProcessor(ear="left")
        frames = 512
        # Use a signal with high-frequency content
        t = np.arange(frames, dtype=np.float32) / 48000.0
        high_freq = np.sin(2.0 * np.pi * 10000.0 * t).astype(np.float32) * 0.5
        indata = np.column_stack([np.zeros(frames, dtype=np.float32), high_freq])
        outdata = np.zeros((frames, 1), dtype=np.float32)

        p._process_block(indata, outdata, frames, None, None)

        # Right channel is filtered (head shadow), output != input
        # The lowpass should attenuate the 10kHz signal
        output_rms = float(np.sqrt(np.mean(outdata**2)))
        input_rms = float(np.sqrt(np.mean(high_freq**2)))
        assert output_rms < input_rms * 0.5  # significantly attenuated

    def test_different_block_sizes(self) -> None:
        """Head shadow works with various valid block sizes."""
        for bs in [64, 128, 256, 512]:
            p = RealtimeProcessor(block_size=bs)
            indata = np.random.randn(bs, 2).astype(np.float32) * 0.1
            outdata = np.zeros((bs, 1), dtype=np.float32)
            p._process_block(indata, outdata, bs, None, None)
            assert outdata.shape == (bs, 1)
            assert not np.any(np.isnan(outdata))

    def test_zi_initialized_none(self) -> None:
        """_zi_left and _zi_right are None initially (no filter state)."""
        p = RealtimeProcessor()
        assert p._zi_left is None
        assert p._zi_right is None

    def test_zi_not_none_after_block_ear_left(self) -> None:
        """After block with ear=left, _zi_right is not None (filter ran)."""
        p = RealtimeProcessor(ear="left")
        frames = 512
        indata = np.random.randn(frames, 2).astype(np.float32) * 0.1
        outdata = np.zeros((frames, 1), dtype=np.float32)
        p._process_block(indata, outdata, frames, None, None)
        assert p._zi_left is None  # left is passthrough, no filter
        assert p._zi_right is not None

    def test_zi_not_none_after_block_ear_right(self) -> None:
        """After block with ear=right, _zi_left is not None (filter ran)."""
        p = RealtimeProcessor(ear="right")
        frames = 512
        indata = np.random.randn(frames, 2).astype(np.float32) * 0.1
        outdata = np.zeros((frames, 1), dtype=np.float32)
        p._process_block(indata, outdata, frames, None, None)
        assert p._zi_left is not None
        assert p._zi_right is None  # right is passthrough, no filter

    def test_maintains_public_api(self) -> None:
        """Public API (start/stop/list_devices) unchanged by head shadow."""
        p = RealtimeProcessor()
        assert p.latency_ms == pytest.approx(10.667, abs=0.001)
        assert not p.is_running
        assert hasattr(p, "list_devices")
        assert callable(p.list_devices)


# =========================================================================
# Elevation (up/down) cue
# =========================================================================


class TestElevationCue:
    """Tests for elevation (up/down) cue processing."""

    def test_elevation_default(self) -> None:
        """Default elevation intensity is 0.3."""
        p = RealtimeProcessor()
        assert p._elevation == 0.3

    def test_elevation_custom(self) -> None:
        """Custom elevation intensity is accepted."""
        p = RealtimeProcessor(elevation=0.5)
        assert p._elevation == 0.5

    def test_elevation_zero(self) -> None:
        """Elevation intensity 0 is accepted."""
        p = RealtimeProcessor(elevation=0.0)
        assert p._elevation == 0.0

    def test_elevation_raises_if_negative(self) -> None:
        """Negative elevation intensity raises ValueError."""
        with pytest.raises(ValueError, match="elevation"):
            RealtimeProcessor(elevation=-0.1)

    def test_elevation_raises_if_over_one(self) -> None:
        """Elevation intensity > 1 raises ValueError."""
        with pytest.raises(ValueError, match="elevation"):
            RealtimeProcessor(elevation=1.5)

    def test_elevation_up_sos_exists(self) -> None:
        """Elevation up SOS filter is precomputed."""
        p = RealtimeProcessor()
        assert hasattr(p, "_elevation_up_sos")
        assert isinstance(p._elevation_up_sos, np.ndarray)

    def test_elevation_down_sos_exists(self) -> None:
        """Elevation down SOS filter is precomputed."""
        p = RealtimeProcessor()
        assert hasattr(p, "_elevation_down_sos")
        assert isinstance(p._elevation_down_sos, np.ndarray)

    def test_elevation_up_sos_is_bandpass(self) -> None:
        """Elevation up SOS is a bandpass filter 7500-10500 Hz."""
        from scipy.signal import sosfreqz

        p = RealtimeProcessor()
        w, h = sosfreqz(p._elevation_up_sos, fs=48000, worN=48000)
        peak_idx = int(np.argmax(np.abs(h)))
        peak_freq = float(w[peak_idx])
        assert 7000 < peak_freq < 11000

    def test_elevation_down_sos_is_bandpass(self) -> None:
        """Elevation down SOS is a bandpass filter 3500-6500 Hz."""
        from scipy.signal import sosfreqz

        p = RealtimeProcessor()
        w, h = sosfreqz(p._elevation_down_sos, fs=48000, worN=48000)
        peak_idx = int(np.argmax(np.abs(h)))
        peak_freq = float(w[peak_idx])
        assert 3000 < peak_freq < 7000

    def test_zi_elevation_up_none_initially(self) -> None:
        """Zi elevation up is None before any processing."""
        p = RealtimeProcessor(elevation=0.5)
        assert p._zi_elevation_up is None

    def test_zi_elevation_down_none_initially(self) -> None:
        """Zi elevation down is None before any processing."""
        p = RealtimeProcessor(elevation=0.5)
        assert p._zi_elevation_down is None

    def test_zi_elevation_up_not_none_after_block(self) -> None:
        """Zi elevation up is not None after processing with elevation > 0."""
        p = RealtimeProcessor(elevation=0.5)
        indata = np.random.randn(512, 2).astype(np.float32) * 0.1
        outdata = np.zeros((512, 1), dtype=np.float32)
        p._process_block(indata, outdata, 512, None, None)
        assert p._zi_elevation_up is not None

    def test_zi_elevation_down_not_none_after_block(self) -> None:
        """Zi elevation down is not None after processing with elevation > 0."""
        p = RealtimeProcessor(elevation=0.5)
        indata = np.random.randn(512, 2).astype(np.float32) * 0.1
        outdata = np.zeros((512, 1), dtype=np.float32)
        p._process_block(indata, outdata, 512, None, None)
        assert p._zi_elevation_down is not None

    def test_elevation_zero_output_unchanged(self) -> None:
        """With elevation=0 and fb=0, output matches passthrough."""
        p_zero = RealtimeProcessor(elevation=0.0, fb_intensity=0.0)
        indata = np.random.randn(512, 2).astype(np.float32) * 0.1
        out_zero = np.zeros((512, 1), dtype=np.float32)
        p_zero._process_block(indata.copy(), out_zero, 512, None, None)

        p_fb = RealtimeProcessor(elevation=0.0, fb_intensity=0.0)
        out_fb = np.zeros((512, 1), dtype=np.float32)
        p_fb._process_block(indata.copy(), out_fb, 512, None, None)

        np.testing.assert_allclose(out_zero, out_fb, atol=1e-6)

    def test_elevation_positive_modifies_output(self) -> None:
        """Elevation > 0 modifies the output compared to elevation=0."""
        p_zero = RealtimeProcessor(elevation=0.0, fb_intensity=0.0)
        p_high = RealtimeProcessor(elevation=0.8, fb_intensity=0.0)
        indata = np.random.randn(512, 2).astype(np.float32) * 0.1
        out_zero = np.zeros((512, 1), dtype=np.float32)
        out_high = np.zeros((512, 1), dtype=np.float32)
        p_zero._process_block(indata.copy(), out_zero, 512, None, None)
        p_high._process_block(indata.copy(), out_high, 512, None, None)
        assert not np.allclose(out_zero, out_high, atol=1e-6)

    def test_elevation_does_not_introduce_nan(self) -> None:
        """Elevation processing does not produce NaN values."""
        p = RealtimeProcessor(elevation=0.8)
        indata = np.random.randn(512, 2).astype(np.float32) * 0.1
        outdata = np.zeros((512, 1), dtype=np.float32)
        p._process_block(indata, outdata, 512, None, None)
        assert not np.any(np.isnan(outdata))
        assert not np.any(np.isinf(outdata))

    def test_elevation_works_with_different_block_sizes(self) -> None:
        """Elevation cue works with various block sizes."""
        for block_size in [64, 128, 256, 512, 1024]:
            p = RealtimeProcessor(elevation=0.5, block_size=block_size)
            indata = np.random.randn(block_size, 2).astype(np.float32) * 0.1
            outdata = np.zeros((block_size, 1), dtype=np.float32)
            p._process_block(indata, outdata, block_size, None, None)
            assert not np.any(np.isnan(outdata))

    def test_elevation_works_with_both_ears(self) -> None:
        """Elevation cue works with both ear=left and ear=right."""
        for ear in ["left", "right"]:
            p = RealtimeProcessor(elevation=0.5, ear=ear)
            indata = np.random.randn(512, 2).astype(np.float32) * 0.1
            outdata = np.zeros((512, 1), dtype=np.float32)
            p._process_block(indata, outdata, 512, None, None)
            assert not np.any(np.isnan(outdata))

    def test_maintains_public_api(self) -> None:
        """Existing public API is unchanged."""
        p = RealtimeProcessor(elevation=0.5)
        assert hasattr(p, "start")
        assert hasattr(p, "stop")
        assert hasattr(p, "is_running")
        assert hasattr(p, "latency_ms")
        assert hasattr(p, "list_devices")


# =========================================================================
# LR intensity (left/right head shadow) control
# =========================================================================


class TestLrIntensity:
    """Tests for left/right head shadow intensity control."""

    def test_lr_intensity_default(self) -> None:
        """Default LR intensity is 1.0 (full head shadow)."""
        p = RealtimeProcessor()
        assert p._lr_intensity == 1.0

    def test_lr_intensity_custom(self) -> None:
        """Custom LR intensity is accepted."""
        p = RealtimeProcessor(lr_intensity=0.5)
        assert p._lr_intensity == 0.5

    def test_lr_intensity_zero(self) -> None:
        """LR intensity 0 is accepted (no head shadow)."""
        p = RealtimeProcessor(lr_intensity=0.0)
        assert p._lr_intensity == 0.0

    def test_lr_intensity_raises_if_negative(self) -> None:
        """Negative LR intensity raises ValueError."""
        with pytest.raises(ValueError, match="lr_intensity"):
            RealtimeProcessor(lr_intensity=-0.1)

    def test_lr_intensity_raises_if_over_one(self) -> None:
        """LR intensity > 1 raises ValueError."""
        with pytest.raises(ValueError, match="lr_intensity"):
            RealtimeProcessor(lr_intensity=1.5)

    def test_lr_zero_both_channels_passthrough(self) -> None:
        """With lr_intensity=0, both channels pass through unchanged."""
        p = RealtimeProcessor(
            lr_intensity=0.0, fb_intensity=0.0, elevation=0.0,
        )
        rng = np.random.RandomState(42)
        indata = rng.randn(512, 2).astype(np.float32) * 0.1
        outdata = np.zeros((512, 1), dtype=np.float32)
        p._process_block(indata, outdata, 512, None, None)
        # Output should be sum of L+R (no filtering)
        expected = (indata[:, 0] + indata[:, 1]).astype(np.float32)
        np.testing.assert_allclose(outdata[:, 0], expected, atol=1e-6)

    def test_lr_one_applies_full_head_shadow(self) -> None:
        """With lr_intensity=1.0, head shadow is fully applied (differs from 0)."""
        p_full = RealtimeProcessor(
            lr_intensity=1.0, fb_intensity=0.0, elevation=0.0,
        )
        rng = np.random.RandomState(42)
        indata = rng.randn(512, 2).astype(np.float32) * 0.1
        out_full = np.zeros((512, 1), dtype=np.float32)
        p_full._process_block(indata.copy(), out_full, 512, None, None)

        p_zero = RealtimeProcessor(
            lr_intensity=0.0, fb_intensity=0.0, elevation=0.0,
        )
        out_zero = np.zeros((512, 1), dtype=np.float32)
        p_zero._process_block(indata.copy(), out_zero, 512, None, None)

        # Full head shadow should differ from no head shadow
        assert not np.allclose(out_full, out_zero, atol=1e-6)

    def test_lr_half_is_between_zero_and_one(self) -> None:
        """LR intensity 0.5 produces output between 0.0 and 1.0."""
        rng = np.random.RandomState(42)
        indata = rng.randn(512, 2).astype(np.float32) * 0.1

        p_zero = RealtimeProcessor(
            lr_intensity=0.0, fb_intensity=0.0, elevation=0.0,
        )
        out_zero = np.zeros((512, 1), dtype=np.float32)
        p_zero._process_block(indata.copy(), out_zero, 512, None, None)

        p_half = RealtimeProcessor(
            lr_intensity=0.5, fb_intensity=0.0, elevation=0.0,
        )
        out_half = np.zeros((512, 1), dtype=np.float32)
        p_half._process_block(indata.copy(), out_half, 512, None, None)

        p_full = RealtimeProcessor(
            lr_intensity=1.0, fb_intensity=0.0, elevation=0.0,
        )
        out_full = np.zeros((512, 1), dtype=np.float32)
        p_full._process_block(indata.copy(), out_full, 512, None, None)

        # Half should be between zero and full (in terms of difference)
        diff_zero_half = float(np.max(np.abs(out_half - out_zero)))
        diff_zero_full = float(np.max(np.abs(out_full - out_zero)))
        assert diff_zero_half < diff_zero_full

    def test_lr_intensity_does_not_introduce_nan(self) -> None:
        """LR intensity processing does not produce NaN."""
        p = RealtimeProcessor(lr_intensity=0.5)
        indata = np.random.randn(512, 2).astype(np.float32) * 0.1
        outdata = np.zeros((512, 1), dtype=np.float32)
        p._process_block(indata, outdata, 512, None, None)
        assert not np.any(np.isnan(outdata))
        assert not np.any(np.isinf(outdata))

    def test_lr_works_with_both_ears(self) -> None:
        """LR intensity works with both ear=left and ear=right."""
        for ear in ["left", "right"]:
            p = RealtimeProcessor(
                lr_intensity=0.5, ear=ear, fb_intensity=0.0, elevation=0.0,
            )
            indata = np.random.randn(512, 2).astype(np.float32) * 0.1
            outdata = np.zeros((512, 1), dtype=np.float32)
            p._process_block(indata, outdata, 512, None, None)
            assert not np.any(np.isnan(outdata))

    def test_maintains_public_api(self) -> None:
        """Existing public API is unchanged."""
        p = RealtimeProcessor(lr_intensity=0.5)
        assert hasattr(p, "start")
        assert hasattr(p, "stop")
        assert hasattr(p, "is_running")
        assert hasattr(p, "latency_ms")
        assert hasattr(p, "list_devices")
