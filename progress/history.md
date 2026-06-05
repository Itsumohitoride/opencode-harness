# Bitácora histórica (append-only)

> Cada vez que se cierra una sesión, su resumen se añade aquí.
> No edites entradas anteriores. Solo añades al final.

---

## Feature 11 � elevation_cues
**Estado:** done | **Modelo:** big-pickle | **Costo:** .00 | **Duraci�n:** 15min
**Descripci�n:** Discriminaci�n de elevaci�n � boost 7.5-10.5kHz (arriba) + cut 3.5-6.5kHz (abajo). Flag --ud-intensity (0.0-1.0, default 0.3). Integrado en pipeline: head shadow ? front/back ? elevation ? anti-clip.
**Tests:** 70 tests realtime, 0 failing. 19 tests nuevos (TestElevationCue).

## Feature 12 � hrtf_axis_control
**Estado:** done | **Modelo:** big-pickle | **Costo:** .00 | **Duraci�n:** 10min
**Descripci�n:** Control de intensidad por eje espacial. --lr-intensity (0.0-1.0, default 1.0) para head shadow L/R. Unificado con --fb-intensity y --ud-intensity existentes.
**Tests:** 81 tests realtime, 0 failing. 11 tests nuevos (TestLrIntensity).

## Feature 13 — presence_boost
**Estado:** done | **Modelo:** big-pickle | **Costo:** \.00 | **Duración:** 10min
**Descripción:** Presence boost (bandpass 3-5kHz) para claridad de voces/detalles. Flag --clarity (0.0-1.0, default 0.0=off). Aplica SOS al canal ipsolateral, escalado por clarity * 0.3.
**Tests:** 95 tests realtime, 0 failing. 15 tests nuevos (TestPresenceBoost).

## Feature 14 — high_shelf_boost
**Estado:** done | **Modelo:** big-pickle | **Costo:** \.00 | **Duración:** 10min
**Descripción:** High-shelf boost >2kHz para brillo en canal ipsolateral. Flag --brillo (0.0-1.0, default 0.0=off). SOS highpass 2kHz escalado por brillo * 0.3.
**Tests:** 109 tests realtime, 0 failing. 14 tests nuevos (TestHighShelfBoost).

## Feature 15 — low_cut_filter
**Estado:** done | **Modelo:** big-pickle | **Costo:** \.00 | **Duración:** 10min
**Descripción:** Highpass 80Hz anti-rumble post-sum. Flag --low-cut (0.0-1.0, default 0.0=off). Butter 4th order, blend dry/wet progresivo.
**Tests:** 123 tests realtime, 0 failing. 14 tests nuevos (TestLowCutFilter).

## Feature 16 — soft_compressor
**Estado:** done | **Modelo:** big-pickle | **Costo:** \.00 | **Duración:** 10min
**Descripción:** Soft-knee compressor post-sum. Flag --compress (0.0-1.0, default 0.0=off). Threshold -12dB, ratio 3:1, knee 6dB, attack 1ms, release 50ms. Dry/wet blend progresivo.
**Tests:** 138 tests realtime, 0 failing. 15 tests nuevos (TestSoftCompressor).

## Feature 19c — hrtf_engine_cpp
**Estado:** testing | **Modelo:** big-pickle | **Costo:** \$0.00 | **Duración:** 1 sesión
**Descripción:** Port HRTFDatabase + MonauralSpatialEncoder completo de Python a C++/JUCE. HrtfDatabase con HRTF sintético (ventana Gaussiana × seno portador, pico 1.0) + LRU cache. SpatialAudioProcessor con pipeline completo: head shadow (lowpass 4kHz + blend) → presence boost (bandpass 3-5kHz) → brillo (highshelf 2kHz) → suma mono → front/back notch (8kHz + delay 12ms) → elevation cues (bandpass up 7.5-10.5kHz / down 3.5-6.5kHz) → low-cut (highpass 80Hz) → compressor (soft-knee, ratio 3:1, threshold 0.25) → anti-clip (pico ≤ 0.95).
**Archivos:** DSP/HrtfDatabase.h/.cpp, DSP/SpatialAudioProcessor.h/.cpp, DSP/HrtfDatabaseTest.h, Audio/AudioPipeline.h/.cpp (mod), App/Application.h/.cpp (mod).
**Build:** Rafear.exe 6.7 MB Release, 0 errores, 0 warnings.

## Feature 19 � C++/JUCE migration
**Estado:** done | **Modelo:** big-pickle | **Duraci�n:** 2026-06-04
**Descripci�n:** Reescribir Rafear de Python MVP a aplicaci�n nativa C++/JUCE.
- 19a: JUCE project scaffold (CMakeLists.txt, CPM, presets, MainComponent placeholder)
- 19b: WASAPI loopback capture (raw Win32, AbstractFifo RingBuffer)
- 19c: HRTF engine + SpatialAudioProcessor (head shadow, presence, brillo, front/back, elevation, low-cut, compressor, anti-clip)
- 19e: System tray config window (sliders, device selectors, parameter control via atomics)
- 19f: Audio starts/stops only via Start button (no auto-start)
**PR:** https://github.com/Itsumohitoride/Rafear/pull/17
