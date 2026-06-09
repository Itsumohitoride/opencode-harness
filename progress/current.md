# Sesion actual

- **Feature:** 23 — fix_audio_loop (mute default render endpoint)
- **Estado:** in_progress
- **Branch harness:** develop
- **Branch src:** feature/23-fix_audio_loop
- **Inicio:** 2026-06-09

## Plan

1. Add `#include <endpointvolume.h>` + Windows headers to Application.cpp
2. Add `muteDefaultRenderEndpoint(bool)` static helper before Pimpl
3. Call `muteDefaultRenderEndpoint(true)` in `startAudio()` before deviceManager.initialise()
4. Call `muteDefaultRenderEndpoint(false)` in `stopAudio()` after cleanup
5. Handle edge case: unmute on deviceManager.initialise() failure
6. Build + verify
