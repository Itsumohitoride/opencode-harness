# BitÃ¡cora histÃ³rica (append-only)

> Cada vez que se cierra una sesiÃ³n, su resumen se aÃ±ade aquÃ­.
> No edites entradas anteriores. Solo aÃ±ades al final.

---

## Feature 11 ï¿½ elevation_cues
**Estado:** done | **Modelo:** big-pickle | **Costo:** .00 | **Duraciï¿½n:** 15min
**Descripciï¿½n:** Discriminaciï¿½n de elevaciï¿½n ï¿½ boost 7.5-10.5kHz (arriba) + cut 3.5-6.5kHz (abajo). Flag --ud-intensity (0.0-1.0, default 0.3). Integrado en pipeline: head shadow ? front/back ? elevation ? anti-clip.
**Tests:** 70 tests realtime, 0 failing. 19 tests nuevos (TestElevationCue).

## Feature 12 ï¿½ hrtf_axis_control
**Estado:** done | **Modelo:** big-pickle | **Costo:** .00 | **Duraciï¿½n:** 10min
**Descripciï¿½n:** Control de intensidad por eje espacial. --lr-intensity (0.0-1.0, default 1.0) para head shadow L/R. Unificado con --fb-intensity y --ud-intensity existentes.
**Tests:** 81 tests realtime, 0 failing. 11 tests nuevos (TestLrIntensity).

## Feature 13 â€” presence_boost
**Estado:** done | **Modelo:** big-pickle | **Costo:** \.00 | **DuraciÃ³n:** 10min
**DescripciÃ³n:** Presence boost (bandpass 3-5kHz) para claridad de voces/detalles. Flag --clarity (0.0-1.0, default 0.0=off). Aplica SOS al canal ipsolateral, escalado por clarity * 0.3.
**Tests:** 95 tests realtime, 0 failing. 15 tests nuevos (TestPresenceBoost).

## Feature 14 â€” high_shelf_boost
**Estado:** done | **Modelo:** big-pickle | **Costo:** \.00 | **DuraciÃ³n:** 10min
**DescripciÃ³n:** High-shelf boost >2kHz para brillo en canal ipsolateral. Flag --brillo (0.0-1.0, default 0.0=off). SOS highpass 2kHz escalado por brillo * 0.3.
**Tests:** 109 tests realtime, 0 failing. 14 tests nuevos (TestHighShelfBoost).

## Feature 15 â€” low_cut_filter
**Estado:** done | **Modelo:** big-pickle | **Costo:** \.00 | **DuraciÃ³n:** 10min
**DescripciÃ³n:** Highpass 80Hz anti-rumble post-sum. Flag --low-cut (0.0-1.0, default 0.0=off). Butter 4th order, blend dry/wet progresivo.
**Tests:** 123 tests realtime, 0 failing. 14 tests nuevos (TestLowCutFilter).

## Feature 16 â€” soft_compressor
**Estado:** done | **Modelo:** big-pickle | **Costo:** \.00 | **DuraciÃ³n:** 10min
**DescripciÃ³n:** Soft-knee compressor post-sum. Flag --compress (0.0-1.0, default 0.0=off). Threshold -12dB, ratio 3:1, knee 6dB, attack 1ms, release 50ms. Dry/wet blend progresivo.
**Tests:** 138 tests realtime, 0 failing. 15 tests nuevos (TestSoftCompressor).

## Feature 19c â€” hrtf_engine_cpp
**Estado:** testing | **Modelo:** big-pickle | **Costo:** \$0.00 | **DuraciÃ³n:** 1 sesiÃ³n
**DescripciÃ³n:** Port HRTFDatabase + MonauralSpatialEncoder completo de Python a C++/JUCE. HrtfDatabase con HRTF sintÃ©tico (ventana Gaussiana Ã— seno portador, pico 1.0) + LRU cache. SpatialAudioProcessor con pipeline completo: head shadow (lowpass 4kHz + blend) â†’ presence boost (bandpass 3-5kHz) â†’ brillo (highshelf 2kHz) â†’ suma mono â†’ front/back notch (8kHz + delay 12ms) â†’ elevation cues (bandpass up 7.5-10.5kHz / down 3.5-6.5kHz) â†’ low-cut (highpass 80Hz) â†’ compressor (soft-knee, ratio 3:1, threshold 0.25) â†’ anti-clip (pico â‰¤ 0.95).
**Archivos:** DSP/HrtfDatabase.h/.cpp, DSP/SpatialAudioProcessor.h/.cpp, DSP/HrtfDatabaseTest.h, Audio/AudioPipeline.h/.cpp (mod), App/Application.h/.cpp (mod).
**Build:** Rafear.exe 6.7 MB Release, 0 errores, 0 warnings.

## Feature 19 — C++/JUCE migration
**Estado:** done | **Modelo:** big-pickle | **Duración:** 2026-06-04
**Descripción:** Reescribir Rafear de Python MVP a aplicación nativa C++/JUCE.
- 19a: JUCE project scaffold (CMakeLists.txt, CPM, presets, MainComponent placeholder)
- 19b: WASAPI loopback capture (raw Win32, AbstractFifo RingBuffer)
- 19c: HRTF engine + SpatialAudioProcessor (head shadow, presence, brillo, front/back, elevation, low-cut, compressor, anti-clip)
- 19e: System tray config window (sliders, device selectors, parameter control via atomics)
- 19f: Audio starts/stops only via Start button (no auto-start)
**PR:** https://github.com/Itsumohitoride/Rafear/pull/17

## Session: 2026-06-08 â€” Feature 22e (fix_dropdown_popup_background)
**Date:** 2026-06-08 23:56 UTC
**Feature:** 22e â€” fix_dropdown_popup_background
**Branch src:** feature/22-ui_redesign_notion
**Commit:** 7f3405d
**PR:** https://github.com/Itsumohitoride/Rafear/pull/19

### What was done
1. Fixed ComboBox dropdown popup white background by overriding drawPopupMenuBackgroundWithOptions in RafearLookAndFeel
2. Changed getPopupMenuBorderSize from 1 to 0 to eliminate white border gap
3. Applied custom RafearLookAndFeel to system tray icon right-click context menu (was using default JUCE)
4. Build: succeeded
5. Review: APPROVED

### Cost
- Model: big pickle
- Tokens: 70K in / 30K out
- Cost: - Duration: 10min
- Agents: leader, implementer, reviewer

## Feature 23 — fix_audio_loop
**Estado:** done | **Modelo:** big-pickle | **Costo:** .00 | **Duración:** 10min
**Descripción:** Eliminar bucle infinito mutando endpoint default render con IAudioEndpointVolume. WASAPI loopback captura pre-volume, usuario escucha SOLO procesado por audífonos.

### Cambios
1. Application.cpp — helper muteDefaultRenderEndpoint(bool), llamado en startAudio/stopAudio
2. WasapiCapture.h/cpp — getDefaultRenderDeviceName() static para comparación output vs default render
3. MainComponent.h/cpp — device list, onStart validation, output selector
4. Build: succeeded
5. Review: APPROVED

### Cost
- Model: big-pickle
- Tokens: 50K in / 50K out
- Cost: .00
- Duration: 10min
- Agents: leader, implementer, reviewer

## Feature 24 — fix_realtime_params
**Estado:** done | **Modelo:** big-pickle | **Costo:** .00 | **Duración:** 20min
**Descripción:** Arreglar params en tiempo real — slider + ear no se aplicaban al start ni durante ejecución.

### Cambios
1. MainComponent::onStartStopClick() — mover onParamSliderChange() DESPUÉS de onStart()
2. AudioPipeline::audioDeviceIOCallbackWithContext() — copiar mono procesado a TODOS los canales de output (no solo canal 0)
3. Build: succeeded
4. Review: APPROVED

### Cost
- Model: big-pickle
- Tokens: 65K in / 65K out
- Cost: .00
- Duration: 20min
- Agents: leader, implementer, reviewer
