# BitÃ¡cora histÃ³rica (append-only)

> Cada vez que se cierra una sesiÃ³n, su resumen se aÃ±ade aquÃ­.
> No edites entradas anteriores. Solo aÃ±ades al final.

---

## Feature 11 — elevation_cues
**Estado:** done | **Modelo:** big-pickle | **Costo:** .00 | **Duración:** 15min
**Descripción:** Discriminación de elevación — boost 7.5-10.5kHz (arriba) + cut 3.5-6.5kHz (abajo). Flag --ud-intensity (0.0-1.0, default 0.3). Integrado en pipeline: head shadow ? front/back ? elevation ? anti-clip.
**Tests:** 70 tests realtime, 0 failing. 19 tests nuevos (TestElevationCue).

## Feature 12 — hrtf_axis_control
**Estado:** done | **Modelo:** big-pickle | **Costo:** .00 | **Duración:** 10min
**Descripción:** Control de intensidad por eje espacial. --lr-intensity (0.0-1.0, default 1.0) para head shadow L/R. Unificado con --fb-intensity y --ud-intensity existentes.
**Tests:** 81 tests realtime, 0 failing. 11 tests nuevos (TestLrIntensity).

## Feature 13 â€” presence_boost
**Estado:** done | **Modelo:** big-pickle | **Costo:** \.00 | **DuraciÃ³n:** 10min
**DescripciÃ³n:** Presence boost (bandpass 3-5kHz) para claridad de voces/detalles. Flag --clarity (0.0-1.0, default 0.0=off). Aplica SOS al canal ipsolateral, escalado por clarity * 0.3.
**Tests:** 95 tests realtime, 0 failing. 15 tests nuevos (TestPresenceBoost).

## Feature 14 â€” high_shelf_boost
**Estado:** done | **Modelo:** big-pickle | **Costo:** \.00 | **DuraciÃ³n:** 10min
**DescripciÃ³n:** High-shelf boost >2kHz para brillo en canal ipsolateral. Flag --brillo (0.0-1.0, default 0.0=off). SOS highpass 2kHz escalado por brillo * 0.3.
**Tests:** 109 tests realtime, 0 failing. 14 tests nuevos (TestHighShelfBoost).
