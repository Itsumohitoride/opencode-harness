# BitÃ¡cora histÃ³rica (append-only)

> Cada vez que se cierra una sesiÃ³n, su resumen se aÃ±ade aquÃ­.
> No edites entradas anteriores. Solo aÃ±ades al final.

---

## Feature 11 — elevation_cues
**Estado:** done | **Modelo:** big-pickle | **Costo:** .00 | **Duración:** 15min
**Descripción:** Discriminación de elevación — boost 7.5-10.5kHz (arriba) + cut 3.5-6.5kHz (abajo). Flag --ud-intensity (0.0-1.0, default 0.3). Integrado en pipeline: head shadow ? front/back ? elevation ? anti-clip.
**Tests:** 70 tests realtime, 0 failing. 19 tests nuevos (TestElevationCue).
