# Convenciones de Código — MonoSpatial (Python DSP)

## Stack: Python

### Estilo
| Aspecto | Convención |
|---------|-----------|
| Formateo | `ruff format` |
| Linter | `ruff check` |
| Línea máxima | 100 caracteres |
| Strings | Comillas dobles `"` |
| Interpolación | f-strings siempre |
| Imports | stdlib → numpy/scipy → locales (separados por línea en blanco) |
| Type hints | Obligatorios en toda función pública |

### Nombres
| Tipo | Convención | Ejemplo |
|------|-----------|---------|
| Archivos | `snake_case` | `hrtf_engine.py` |
| Clases | `PascalCase` | `MonauralSpatialEncoder` |
| Métodos | `snake_case` | `encode_source()` |
| Constantes | `UPPER_SNAKE` | `BLOCK_SIZE` |
| Privadas | Prefijo `_` | `_cache` |
| Variables de audio | nombre descriptivo + unidad implícita | `signal`, `azimuth`, `elevation` |

### Señales de Audio (convenciones de naming)
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `signal` | `np.ndarray` | Señal de audio 1D (muestras float32) |
| `sample_rate` / `sr` | `int` | Frecuencia de muestreo en Hz |
| `azimuth` | `float` | Ángulo horizontal en grados (-180 a +180) |
| `elevation` | `float` | Ángulo vertical en grados (-90 a +90) |
| `distance` | `float` | Distancia en metros (≥ 0.1) |
| `ir` | `np.ndarray` | Impulse response (filtro HRTF) |
| `block_size` / `frames` | `int` | Tamaño de bloque de procesamiento |

### Tests
- Ubicación: `tests/test_<módulo>.py`
- Framework: `pytest`
- Señales de prueba: generar con `np.random.randn()` o `np.sin()`
- Validar: forma del array, rango, latencia, no silent output
- No depender de archivos .sofa externos para tests unitarios (usar IR sintética)

### Manejo de errores
- Validar entrada al inicio de cada función pública
- `ValueError` para parámetros fuera de rango (azimuth > 180, distancia < 0)
- `FileNotFoundError` para .sofa no encontrado
- No silenciar errores de audio (`sounddevice` callback debe reportar status)

### Performance (critical path)
- Precomputar FFTs de filtros que no cambian (caché por azimuth/elevation)
- Evitar `np.append` o `np.concatenate` en hot path — preasignar buffers
- Usar `np.float32` para señales (no float64) — ahorra memoria y ancho de banda
- Overlap-save para convolución larga (>512 taps)

### Documentación de módulos
Cada módulo debe tener docstring al inicio explicando:
1. Qué hace
2. Parámetros de entrada/salida principales
3. Dependencias externas
4. Ejemplo breve de uso (si aplica)