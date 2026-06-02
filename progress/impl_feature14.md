# Feature 14 — high_shelf_boost

**Estado:** in_progress
**Branch:** feature/14-high_shelf_boost
**Modelo:** big-pickle

## Cambios realizados

### `src/realtime_processor.py`

1. **Constructor `__init__`**:
   - Add `brillo: float = 0.0` parámetro después de `clarity`
   - Validación: `0.0 <= brillo <= 1.0` (ValueError si fuera de rango)
   - Atributos: `self._brillo`, `self._high_shelf_sos` (butter highpass 2kHz, order 2), `self._zi_high_shelf` (estado filtro, None inicial)

2. **`_process_block`**:
   - Pipeline order actualizado: head shadow → presence boost → **high-shelf boost (brillo)** → sum → front/back → elevation → anti-clip
   - High-shelf boost aplicado al canal ipsolateral después de presence boost y antes del sum
   - Usa `sosfilt` con persistencia de estado `_zi_high_shelf` entre bloques
   - Escalado por `self._brillo * 0.3`
   - Si `brillo == 0.0`, el bloque se salta sin procesamiento

3. **`parse_args`**:
   - Add `--brillo` flag (type=float, default=0.0)

4. **`main()`**:
   - Pasa `brillo=args.brillo` al constructor

### `tests/test_realtime_processor.py`

- Nueva clase `TestHighShelfBoost` con 14 tests:
  - `test_brillo_default`, `test_brillo_custom`, `test_brillo_zero`
  - `test_brillo_raises_if_negative`, `test_brillo_raises_if_over_one`
  - `test_high_shelf_sos_exists`, `test_high_shelf_is_highpass`
  - `test_zi_high_shelf_none_initially`, `test_zi_high_shelf_not_none_after_block`
  - `test_brillo_zero_output_unchanged`, `test_brillo_positive_modifies_output`
  - `test_brillo_does_not_introduce_nan`
  - `test_brillo_works_with_both_ears`
  - `test_maintains_public_api`

## Verificación

```bash
python -m pytest tests/ -v --tb=short
# 109 passed (95 existing + 14 new)
```

## Acceptance Checklist

- [x] High-shelf boost >2kHz para brillo en canal ipsolateral
- [x] Flag `--brillo` (0.0-1.0, default 0.0=off)
- [x] No afecta canal contralateral ni latencia
- [x] Block-size 512 sin buffer underrun
- [x] Todos los tests existentes pasan
