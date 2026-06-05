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

## Stack: C++/JUCE

### Build system
| Aspect | Convention |
|--------|-----------|
| CMake | 3.25 minimum, CMakePresets.json |
| Generator | Visual Studio 17 2022, x64 |
| C++ standard | C++20 |
| JUCE | 8.0.13 via CPM (auto-download) |
| Compiler flags | `/arch:AVX2 /fp:fast /MP` |

### Style
| Aspect | Convention |
|--------|-----------|
| Header guard | `#pragma once` |
| Naming: classes | PascalCase |
| Naming: methods/functions | camelCase |
| Naming: member variables | camelCase with `_` suffix |
| Naming: constants | kPrefixedCamelCase |
| Naming: files | PascalCase.cpp/.h |
| Indentation | 4 spaces (JUCE default) |

### Audio callback rules (CRITICAL)
- NO memory allocation in audio thread (no `new`, `malloc`, `std::vector::push_back`)
- NO mutex locks in audio thread (use `std::atomic` with relaxed ordering)
- NO file I/O, network, or system calls in audio thread
- NO exceptions in audio thread
- Pre-allocate all DSP objects in `prepareToPlay()` / `audioDeviceAboutToStart()`
- Use `juce::AudioBuffer<float>` for sample data
- Use `juce::dsp::ProcessSpec` for sample rate / block size configuration

### Platform-specific
| Aspect | Convention |
|--------|-----------|
| Windows | `WIN32_EXECUTABLE TRUE` for tray app |
| COM | Balance CoInitialize/CoUninitialize, prefer RAII wrappers |
| WASAPI | Use raw Win32 for loopback (JUCE has no loopback support) |
| MMCSS | Register capture thread with "Pro Audio" class |

### Tests
| Aspect | Convention |
|--------|-----------|
| Framework | JUCE unit test class or CTest |
| Location | `tests/` or inline in module |
| HRTF IR | Synthetic impulse (dirac) for unit tests |
| Float comparison | Use `approximatelyEqual()` or absolute tolerance |

### Error handling
| Error type | Mechanism |
|------------|----------|
| COM errors | `HRESULT` checks with `jassert` or `juce::Result` |
| Audio device failure | `AudioDeviceManager::initialise()` returns error string |
| File not found | `juce::File::exists()` before access |