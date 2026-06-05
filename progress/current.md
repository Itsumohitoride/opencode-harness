# Sesion actual

- **Feature:** 19e — System tray config window with parameter controls
- **Estado:** in_progress
- **Branch harness:** develop
- **Branch src:** feature/19e-config-window
- **Inicio:** 2026-06-04

## Decisiones

- All DSP params become atomic for runtime changes
- Internal helpers take params as args for consistency within one callback
- RafearTrayIcon subclasses SystemTrayIconComponent for right-click menu

## Plan

1. Make all float params atomic in SpatialAudioProcessor.h + add setParam()
2. Update SpatialAudioProcessor.cpp — store() in prepare, load atomics in process()
3. Rewrite MainComponent.h as full config window with sliders/selectors
4. Rewrite MainComponent.cpp with layout and parameter controls
5. Update Application.h — add RafearTrayIcon + forward declare MainComponent with AudioPipeline&
6. Update Application.cpp — wire tray menu, pass pipeline to MainComponent
7. Build and fix any compilation errors
