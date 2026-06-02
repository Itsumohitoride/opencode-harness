# Feature 15 — low_cut_filter — Implementación

**Estado:** implementada y verificada
**Tests:** 123 passed (109 existentes + 14 nuevos)
**Branch:** feature/15-low_cut_filter

## Cambios realizados

### src/realtime_processor.py

1. **Constructor (`__init__`)**:
   - Nuevo parámetro `low_cut: float = 0.0` después de `brillo`
   - Validación: `0.0 <= low_cut <= 1.0`, raises `ValueError` si fuera de rango
   - Inicialización de `_low_cut`, `_low_cut_sos` (butter 4to orden, 80Hz highpass)
   - `_zi_low_cut: np.ndarray | None = None` en sección de estado de filtros

2. **`_process_block`**:
   - Pipeline actualizado en docstring (paso 9: low-cut anti-rumble)
   - Low-cut aplicado DESPUÉS de elevation cues y ANTES de anti-clip
   - Blend: `dry * (1 - low_cut * 0.5) + wet * (low_cut * 0.5)`
   - Persistencia de estado `_zi_low_cut` entre bloques

3. **`parse_args`**:
   - Nuevo flag `--low-cut` (float, default 0.0, 0=off)

4. **`main()`**:
   - Pasa `low_cut=args.low_cut` al constructor

### tests/test_realtime_processor.py

- Nueva clase `TestLowCutFilter` con 14 tests:
  - Default/custom/zero values
  - ValueError en out-of-range
  - Existencia y tipo de SOS filter
  - Verificación de highpass via sosfreqz
  - Zi state inicial y después de bloque
  - Output sin cambios con low_cut=0
  - Output modificado con low_cut>0
  - Reducción de 40Hz content (RMS < 50%)
  - No introduce NaN/Inf
  - Mantiene API pública

## Pipeline completo

1. Head shadow (L/R blending via lr_intensity)
2. Presence boost (clarity)
3. High-shelf boost (brillo)
4. Sum a mono
5. Front/back cues (fb_intensity)
6. Elevation cues (elevation)
7. **Low-cut filter (low_cut) — anti-rumble** ← NUEVO
8. Anti-clip
