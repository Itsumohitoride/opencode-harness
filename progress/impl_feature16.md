# Feature 16 — soft_compressor

## Cambios realizados

### `src/realtime_processor.py`

1. Constructor `__init__`:
   - Nuevo parámetro `compress: float = 0.0` después de `low_cut`
   - Validación `0.0 <= compress <= 1.0` con `ValueError`
   - Atributo `self._compress`
   - Parámetros fijos del compressor:
     - `_comp_threshold`: 0.25 (-12dB linear)
     - `_comp_ratio`: 3.0 (3:1)
     - `_comp_knee`: 2.0 (6dB knee width)
     - `_comp_attack`: 1.0ms
     - `_comp_release`: 50.0ms
   - Coeficientes precomputados: `_comp_attack_coeff`, `_comp_release_coeff`
   - Estado: `_comp_env` (envelope follower), `_comp_gain_reduction`

2. Nuevo método `_apply_compressor(samples) -> np.ndarray`:
   - RMS block-level detection
   - Envelope follower con ataque/relajación entre bloques
   - Soft-knee gain computer: región knee cuadrática
   - Dry/wet blend: `wet = compress * 0.5`, max 50% wet

3. Pipeline `_process_block`:
   - Compresor insertado DESPUÉS de low-cut, ANTES de anti-clip
   - Pipeline: → low-cut → compressor → anti-clip

4. CLI:
   - Nuevo flag `--compress` (0.0-1.0, default 0.0)
   - `main()` pasa `compress=args.compress` al constructor

5. Docstrings actualizados (Args, Raises, pipeline doc)

### `tests/test_realtime_processor.py`

Nueva clase `TestSoftCompressor` con 15 tests:
- `test_compress_default` / `test_compress_custom` / `test_compress_zero`
- `test_compress_raises_if_negative` / `test_compress_raises_if_over_one`
- `test_compressor_params_exist` / `test_compressor_coefficients_exist`
- `test_apply_compressor_method_exists`
- `test_compress_zero_output_unchanged`
- `test_compress_positive_modifies_output`
- `test_compressor_never_increases_peak`
- `test_compressor_reduces_crest_factor`
- `test_compressor_does_not_introduce_nan`
- `test_compressor_maintains_public_api`
- `test_compressor_envelope_state_persists`

## Resultado

```
138 passed in 1.64s
```

Todos los tests existentes (123) + nuevos (15) pasan.
