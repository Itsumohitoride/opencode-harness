# Session actual

- **Feature en curso:** 12 — hrtf_axis_control
- **Branch:** feature/12-hrtf_axis_control
- **Inicio:** 2026-05-31
- **Agente:** implementer

## Plan
- Add `lr_intensity` param to RealtimeProcessor.__init__ with validation
- Modify `_process_block` to blend head shadow by lr_intensity
- Add `--lr-intensity` CLI arg
- Pass `lr_intensity` to constructor in main()
- Write tests for lr_intensity (default, custom, 0, 1, valid/invalid ranges, behavior)
- Verify existing tests still pass (70 baseline)
