# MonoSpatial — Plan Arquitectural
### Audio 3D Monoaural para Gaming y Accesibilidad

---

## El Problema

El audio 3D tradicional (binaural) usa diferencias interaurales — diferencias de tiempo (ITD) y nivel (ILD) entre ambos oídos. Con un solo oído funcional, eso desaparece. Pero el cerebro monoaural no es ciego espacialmente: usa:

- **Spectral shaping del pabellón**: el oído externo filtra frecuencias según el ángulo de elevación
- **Early reflections**: los primeros rebotes de la cabeza, hombros y torso
- **Monaural HRTF**: la función de transferencia de un solo canal que codifica posición en el espectro

---

## Pipeline General

```
Game Audio Output
      |
      v
┌─────────────────┐
│  Stereo / 5.1   │  <- Capturar ANTES de que salga al hardware
│  Spatial Audio  │
└────────┬────────┘
         |
    Downmix a mono
         |
    HRTF Monoaural
         |
    Output -> audifono unico
```

---

## Fase 1 — Investigación y Baseline (4-6 semanas)

### 1.1 Captura de HRTF Monoaural personalizada

El HRTF varía por persona. Para máxima efectividad:

```
Opciones (de más a menos preciso):
├── HRTF por foto 3D del pabellón auricular (algoritmos como HUTUBS)
├── HRTF genérico de base de datos pública (MIT KEMAR, CIPIC, SADIE II)
└── HRTF ajustable por el usuario mediante calibración auditiva
```

Para el MVP se usa **SADIE II** (Cambridge University), con excelente resolución espectral monoaural.

### 1.2 Análisis del pipeline de audio del juego

Interceptar el audio antes de que llegue al hardware del sistema operativo, hacer downmix inteligente y aplicar los filtros HRTF correspondientes al canal de salida monoaural.

---

## Fase 2 — Arquitectura del Sistema (6-8 semanas)

### Capa 1 — Audio Interceptor

Un driver de audio virtual que se sienta entre el juego y el hardware. En Windows se usa WASAPI loopback o un Virtual Audio Cable customizado.

```
┌────────────────────────────────────────────┐
│           VIRTUAL AUDIO DEVICE             │
│                                            │
│  Input: Game Stereo/Surround               │
│  Output: Processed Mono -> Physical Device │
│                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Channel  │  │  Spatial │  │  HRTF    │ │
│  │ Analyzer │->│ Decoder  │->│ Encoder  │ │
│  └──────────┘  └──────────┘  └──────────┘ │
└────────────────────────────────────────────┘
```

### Capa 2 — Spatial Decoder

Toma el audio multicanal y extrae la información posicional de cada fuente sonora. Mapea cada canal (L, R, C, LFE, SL, SR) a su ángulo espacial estándar correspondiente.

### Capa 3 — Monaural HRTF Encoder

El corazón del sistema. Para cada fuente espacial aplica el filtro HRTF del ángulo correspondiente mediante convolución en dominio frecuencial (overlap-add) para mantener latencia menor a 10ms — crítico para gaming.

---

## Fase 3 — Cues Auditivos Monoaurales Adicionales (4 semanas)

### 3.1 Spectral Coloring por elevación

El pabellón auricular filtra distintas frecuencias según la altura del sonido. Cue 100% monoaural:

```
Sonido desde arriba    -> boost en 8-10 kHz
Sonido desde adelante  -> plano (referencia)
Sonido desde atrás     -> notch en 8 kHz + boost en 12 kHz
Sonido desde abajo     -> cut en 4-6 kHz
```

### 3.2 Early Reflections sintéticas

```
Source -> Direct path (0ms)
       -> Head shadow reflection (0.3-0.7ms, -6dB)
       -> Shoulder reflection (1.2ms, -12dB)
       -> Torso reflection (3ms, -18dB)
```

### 3.3 Amplitude Mapping como fallback

Para ángulos donde el HRTF monoaural es ambiguo (front-back confusion), se usa volumen relativo como cue secundario — los sonidos de atrás llevan una leve reverberación de sala.

---

## Fase 4 — UI y Calibración (3-4 semanas)

App companion con:

- Selector de perfil HRTF (genérico o personalizado)
- Selector de oído funcional (izquierdo / derecho)
- Sliders de elevación, intensidad HRTF y reverb trasero
- Test de calibración interactivo con feedback inmediato
- Ajuste automático de parámetros hasta 80%+ de acierto

---

## Stack Tecnológico

```
Capa de Driver:    Windows -> WASAPI + PortAudio
                   Linux   -> PipeWire / JACK
                   Mac     -> CoreAudio HAL

DSP Engine:        Python (prototipo) -> C++ con JUCE (producción)
                   Librería HRTF: libmysofa (open source, lee .sofa files)
                   FFT: FFTW3 (la más rápida disponible)

App Companion:     Tauri (Rust + Web UI, liviano, cross-platform)

HRTF Database:     SADIE II (Cambridge) — licencia libre para investigación
                   CIPIC (UC Davis) — 45 sujetos, excelente para monoaural
```

---

## Roadmap Resumido

```
Semana 1-6:   Investigación HRTF + prototipo Python con CIPIC
Semana 7-14:  Driver de audio virtual + pipeline DSP en C++/JUCE
Semana 15-18: Spectral cues + early reflections
Semana 19-22: UI de calibración + user testing
Semana 23-26: Optimización de latencia + empaquetado como app
```

---

## Fundamento Científico

El cerebro necesita **entrenamiento** para reinterpretar HRTF monoaural. Los papers de audición monoaural (Hofman et al., 1998; Van Wanrooij & Van Opstal, 2004) muestran que la plasticidad neuronal permite adaptar estos cues en pocas semanas de uso continuo. No es efecto inmediato, pero funciona con práctica.
