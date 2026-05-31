# MonoSpatial

Audio 3D monoaural para gaming y accesibilidad.

## Requisitos

- Python 3.12+
- Windows (WASAPI/CABLE)

### Dependencias

pip install numpy scipy soundfile sounddevice PyQt6

(Opcional: libmysofa para carga de .sofa reales)

---

## Nivel 1 — Test offline

Genera WAV estéreo de prueba:
```
python -c "
import numpy as np, soundfile as sf
sr = 48000
t = np.arange(sr * 3) / sr
left = np.sin(2 * np.pi * 440 * t) * 0.5
right = np.sin(2 * np.pi * 880 * t) * 0.5
stereo = np.column_stack([left, right]).astype(np.float32)
sf.write('test_tonos.wav', stereo, sr)
print('Creado test_tonos.wav')
"
```

Procesa con HRTF (oído izquierdo funcional, default):
```
python src/test_offline.py test_tonos.wav test_mono.wav
```

Si eres sordo del oído **izquierdo** (como el amigo del usuario):
```
python src/test_offline.py test_tonos.wav test_mono.wav --ear right
```

Escucha el resultado:
```
python -c "import sounddevice as sd, soundfile as sf; d,s=sf.read('test_mono.wav'); sd.play(d,s); sd.wait()"
```

> Original: tono grave (440Hz) en un canal, agudo (880Hz) en el otro.
> Procesado: mezclado a mono, pero cada tono suena de direcciones opuestas.

### Flags de test_offline.py

| Flag | Default | Descripción |
|------|---------|-------------|
| input_path | (requerido) | WAV estéreo de entrada |
| output_path | (requerido) | WAV mono de salida |
| --sample-rate | 48000 | Frecuencia de muestreo |
| --ear | left | Oído funcional: left o right |

---

## Nivel 2 — Tiempo real

Lista dispositivos:
```
python src/realtime_processor.py --list-devices
```

Probar con micrófono:
```
python src/realtime_processor.py --input-device ID --output-device ID
```

### Gaming con VB-CABLE
1. Instalar https://vb-audio.com/Cable/
2. Juego → CABLE Input
3. MonoSpatial: --input-device CABLE_Output --output-device auricular

### Flags de realtime_processor.py

| Flag | Default | Descripción |
|------|---------|-------------|
| --input-device | automático | ID del dispositivo de entrada |
| --output-device | automático | ID del dispositivo de salida |
| --sample-rate | 48000 | Frecuencia de muestreo |
| --block-size | 512 | Tamaño de bloque (~10.6ms) |
| --ear | left | Oído funcional: left o right |

---

## Nivel 3 — Calibración

```
python src/calibration_ui.py
```

---

## Tests

```
python -m pytest tests/ -v
```
