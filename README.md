# MonoSpatial

Audio 3D monoaural para gaming y accesibilidad. Permite a personas con audición de un solo lado percibir dirección espacial en videojuegos mediante filtros HRTF.

## Requisitos

- Python 3.12+
- Windows (compatible con WASAPI/CABLE)

### Dependencias

`ash
pip install numpy scipy soundfile sounddevice PyQt6
`

Opcional: libmysofa para cargar bases de datos .sofa reales.

## Pipeline completo

`
src/
  hrtf_engine.py              # HRTFDatabase + MonauralSpatialEncoder
  optimized_convolver.py      # OverlapSaveConvolver (FFT overlap-save)
  test_offline.py             # Prueba offline con archivos WAV
  realtime_processor.py       # Procesamiento en vivo (sounddevice)
  calibration_ui.py           # App de calibración (PyQt6)
`

---

## ?? Nivel 1 — Test offline (sin juego, sin dispositivos)

Genera un WAV estéreo de prueba:

`powershell
python -c ^
  "import numpy as np, soundfile as sf; ^
  sr=48000; t=np.arange(sr*3)/sr; ^
  left=np.sin(2*np.pi*440*t)*0.5; ^
  right=np.sin(2*np.pi*880*t)*0.5; ^
  sf.write('test_tonos.wav', np.column_stack([left,right]).astype(np.float32), sr); ^
  print('Creado test_tonos.wav')"
`

Procesa con HRTF:

`powershell
python src/test_offline.py test_tonos.wav test_mono.wav
`

Reproduce el original (estéreo) y el procesado (mono HRTF):

`powershell
python -c "import sounddevice as sd, soundfile as sf; d,s=sf.read('test_tonos.wav'); sd.play(d,s); sd.wait()"
python -c "import sounddevice as sd, soundfile as sf; d,s=sf.read('test_mono.wav'); sd.play(d,s); sd.wait()"
`

> **¿Qué notar?** Original: agudo (880Hz) en un canal, grave (440Hz) en el otro.
> Procesado: mezclado a mono, pero cada tono suena como si viniera de direcciones
> opuestas aunque sea un solo auricular.

---

## ?? Nivel 2 — Tiempo real con audio del sistema

Lista dispositivos disponibles:

`powershell
python src/realtime_processor.py --list-devices
`

Para probar con micrófono (prueba rápida):

`powershell
python src/realtime_processor.py --input-device <id_mic> --output-device <id_auricular>
`

### Para gaming — Virtual Audio Cable

1. Instala **VB-CABLE** (gratuito): https://vb-audio.com/Cable/
2. Configura:
   - **Juego** ? salida de audio ? **CABLE Input**
   - **MonoSpatial** captura desde **CABLE Output**
   - **MonoSpatial** envía procesado a tu **auricular**
3. Ejecuta:

`powershell
python src/realtime_processor.py --input-device <CABLE_Output_id> --output-device <auricular_id>
`

### Stereo Mix (alternativa)

En Windows: Panel de control ? Sonido ? Grabación ? Activar **Stereo Mix".
Luego úsalo como --input-device.

---

## ??? Nivel 3 — Calibración

Ajusta parámetros antes de jugar:

`powershell
python src/calibration_ui.py
`

- **Intensidad HRTF**: qué tan fuerte es el filtro direccional
- **Reverb trasero**: ayuda a distinguir sonidos detrás
- **Test front/back**: genera ruido a 0° o 180°, tú respondes si fue adelante o atrás

---

## ?? Parámetros del procesador en vivo

| Flag | Default | Descripción |
|------|---------|-------------|
| --input-device | automático | ID del dispositivo de entrada |
| --output-device | automático | ID del dispositivo de salida |
| --sample-rate | 48000 | Frecuencia de muestreo |
| --block-size | 512 | Tamaño de bloque (~10.6ms) |
| --ear | left | Oído funcional (left/right) |

---

## ?? Arquitectura

`
Audio del juego (Stereo)
        ¦
        ?
+-----------------------+
¦  Captura (sounddevice) ¦  ? RealtimeProcessor
+-----------------------+
        ¦
        ?
+-----------------------+
¦  Monaural HRTF Encoder ¦  ? MonauralSpatialEncoder
¦  + OverlapSave FFT    ¦  ? OverlapSaveConvolver
+-----------------------+
        ¦
        ?
+-----------------------+
¦  Salida ? Auricular   ¦
¦  (mono procesado)     ¦
+-----------------------+
`

Latencia objetivo: **< 11ms** (block_size=512 a 48kHz).

---

## ?? Tests

`powershell
python -m pytest tests/ -v
`

158 tests cubriendo: HRTF database, convolución optimizada, procesado offline, tiempo real y UI de calibración.
