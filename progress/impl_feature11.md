# Feature 11: elevation_cues — Implementation Report

## Files modified

| File | Change |
|------|--------|
| `src/realtime_processor.py` | Added elevation cue: SOS filters (up 7.5-10.5kHz, down 3.5-6.5kHz), `elevation` param, `_process_block` integration, `--ud-intensity` CLI arg, zi state persistence |
| `tests/test_realtime_processor.py` | Fixed 2 failing passthrough tests (`fb_intensity=0.0, elevation=0.0`). Added `TestElevationCue` class (19 tests) |

## Implementation details

### `src/realtime_processor.py`

- **`__init__`**: Added `elevation: float = 0.3` parameter. Precomputes `_elevation_up_sos` (butter bandpass 7500-10500Hz) and `_elevation_down_sos` (butter bandpass 3500-6500Hz). Validates `0.0 <= elevation <= 1.0`. Initializes `_zi_elevation_up` and `_zi_elevation_down` as `None`.

- **`_process_block`**: After front/back cue, before anti-clip: applies elevation cue. Bandpass-filtered signal adds 40% boost (up) and subtracts 30% cut (down), scaled by `self._elevation` intensity.

- **`parse_args`**: Added `--ud-intensity` (float, default 0.3).

- **`main`**: Passes `elevation=args.ud_intensity` to `RealtimeProcessor`.

### `tests/test_realtime_processor.py`

- **Fixed 2 tests**: `test_ear_left_passthrough_left_channel` and `test_ear_right_passthrough_right_channel` now use `fb_intensity=0.0, elevation=0.0` to avoid front/back and elevation cue modifying the passthrough output.

- **New `TestElevationCue` class**: 19 tests covering:
  - Default/custom/zero elevation intensity
  - Validation (negative, >1)
  - SOS filter existence, type, bandpass characteristics (via `sosfreqz`)
  - Zi state initialization and persistence after block processing
  - Output unchanged when elevation=0
  - Output modified when elevation>0
  - No NaN/Inf introduced
  - Works with various block sizes (64-1024)
  - Works with both ear=left and ear=right
  - Public API unchanged

## Test count

- **Before**: 171 tests (2 failing)
- **After**: 190 tests (0 failing)
- **New tests added**: 19
- **Test modules not touched**: `test_hrtf_engine.py`, `test_convolver.py`, `test_calibration_ui.py`, `test_offline.py`
