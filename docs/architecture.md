# MonoSpatial — Arquitectura del Sistema
## Audio 3D Monoaural para Gaming y Accesibilidad

## Propósito

MonoSpatial permite a personas con audición monoaural (un solo oído funcional)
percibir la dirección espacial de los sonidos en videojuegos, usando filtros
HRTF (Head-Related Transfer Function) aplicados sobre una sola salida de audio.

### El problema

El audio 3D tradicional (binaural) requiere dos oídos para funcionar: usa
diferencias interaurales de tiempo (ITD) y nivel (ILD). Con un solo oído,
esas diferencias no existen. Pero el cerebro monoaural sí puede percibir
espacialidad mediante:

- **Spectral shaping**: el pabellón auricular filtra frecuencias según elevación
- **Early reflections**: rebotes en cabeza, hombros y torso
- **HRTF monoaural**: la función de transferencia de UN canal que codifica
  posición en el espectro

## Pipeline de Procesamiento

```
Audio del juego (Stereo/Surround)
       │
       ▼
┌──────────────────────────────┐
│  Captura de audio            │
│  (WASAPI loopback / Virtual  │
│   Audio Cable / sounddevice) │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Channel Analyzer            │
│  Separa canales L/R/C/Surr   │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Monaural HRTF Encoder       │
│  ┌────────────────────────┐  │
│  │ HRTFDatabase           │  │
│  │  - Carga archivos .sofa│  │
│  │  - Interpolación       │  │
│  │  - Caché de filtros    │  │
│  ├────────────────────────┤  │
│  │ MonauralSpatialEncoder │  │
│  │  - Convolución HRTF    │  │
│  │  - Spectral elevation  │  │
│  │  - Front-back cues     │  │
│  │  - Distance gain       │  │
│  │  - Mezcla de fuentes   │  │
│  └────────────────────────┘  │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Salida → Audífono único     │
│  (canal mono procesado)      │
└──────────────────────────────┘
```

## Capas del Sistema

### Capa 1 — HRTF Engine (núcleo)
- **HRTFDatabase**: carga archivos `.sofa` vía libmysofa, interpolación
  azimut/elevación, caché LRU de filtros.
- **MonauralSpatialEncoder**: aplica HRTF por convolución, añade spectral
  cues de elevación, front-back confusion resolve, y gain por distancia.
- **OverlapSaveConvolver**: FFT-based convolution optimizada para latencia
  < 10ms.

### Capa 2 — Procesamiento en Tiempo Real
- Captura audio del juego via sounddevice (WASAPI).
- Procesa por bloques de 512 samples (~10.6ms a 48kHz).
- Mantiene latencia total bajo 11ms (crítico para gaming).

### Capa 3 — Calibración y UI
- App PyQt6 para ajuste de parámetros personalizados.
- Test interactivo de discriminación front/back.
- Sliders para intensidad HRTF, reverb trasero.
- Perfil de oído funcional (izquierdo/derecho).

## Stack Tecnológico

| Componente       | Tecnología                          |
|------------------|-------------------------------------|
| Prototipo        | Python 3.12+                        |
| Producción       | C++ con JUCE (plan futuro)          |
| HRTF Loading     | libmysofa (lee formato .sofa)       |
| Convolución      | numpy FFT / scipy fftconvolve       |
| Audio I/O        | sounddevice (PortAudio wrapper)     |
| UI               | PyQt6                               |
| HRTF Database    | SADIE II (Cambridge) / CIPIC (Davis)|

## Latencia Objetivo

| Block Size | Latencia  | Uso                    |
|------------|-----------|------------------------|
| 256        | ~5.3ms    | Producción C++/JUCE    |
| 512        | ~10.6ms   | Python MVP (aceptable) |
| 1024       | ~21ms     | Prototipo / debug      |

Límite para gaming: **< 11ms** de latencia de procesamiento.

## Estructura del Código

```
src/
  hrtf_engine.py          ← HRTFDatabase + MonauralSpatialEncoder
  optimized_convolver.py  ← OverlapSaveConvolver
  test_offline.py         ← Test con archivos WAV
  realtime_processor.py   ← Procesamiento en vivo
  calibration_ui.py       ← App de calibración PyQt6
tests/
  test_hrtf_engine.py     ← Tests unitarios del engine
  test_convolver.py       ← Tests del convolver optimizado
```

## Principios de Diseño

1. **Latencia predecible**: sin allocations en hot path, FFT precomputada.
2. **Calidad perceptiva**: los filtros deben sonar naturales, no artificiales.
3. **Sin fugas**: mezcla con normalización antirrecorte (peak limiting).
4. **Configurable**: parámetros ajustables por el usuario (calibración).
5. **Offline-first**: se puede verificar con archivos antes de tiempo real.