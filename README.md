# Rafear

Audio 3D monoaural para gaming con sordera unilateral.

Procesa audio estéreo en tiempo real y lo mezcla a mono aplicando claves espaciales (L/R, F/B, U/D) para que una persona con sordera de un oído pueda percibir dirección y profundidad. Todo el procesamiento está optimizado para <1% CPU en block-size 512.

## Arquitectura

Pipeline completo (orden de procesamiento):

`
Estéreo → Head Shadow (L/R) → Presencia (clarity) → Brillo (brillo)
       → Suma mono → Front/Back cues → Elevation cues
       → Low-cut filter → Soft compressor → Anti-clip → Mono
`

| Etapa | Flag | Propósito |
|-------|------|-----------|
| Head shadow | \--lr-intensity\ | Atenuación canal contralateral + paneo |
| Presence boost | \--clarity\ | Boost 3-5kHz para claridad de voces |
| High-shelf | \--brillo\ | Boost >2kHz para brillo/aire |
| Front/Back | \--fb-intensity\ | Notch 8kHz + delay para discriminar frente/atrás |
| Elevation | \--ud-intensity\ | Boost/cut selectivo para discriminar arriba/abajo |
| Low-cut | \--low-cut\ | Highpass 80Hz anti-rumble |
| Compressor | \--compress\ | Soft-knee crest factor reduction |

## Requisitos

- Python 3.12+
- Windows 10/11 (WASAPI)
- Auriculares estéreo

### Instalación

`powershell
pip install numpy scipy sounddevice soundfile PyQt6
`

## Comandos

### Listar dispositivos de audio

`powershell
python src/realtime_processor.py --list-devices
`

### Uso básico en tiempo real

`powershell
python src/realtime_processor.py --input-device ID --output-device ID --ear right
`

### Prueba recomendada (sordera oído izquierdo, block-size 512)

`powershell
python src/realtime_processor.py --input-device 25 --output-device 24 --ear right --block-size 512 --clarity 0.4 --brillo 0.3 --low-cut 0.3 --compress 0.3
`

### Routing con VB-CABLE

1. Instalar [VB-CABLE](https://vb-audio.com/Cable/)
2. Configurar juego/app → CABLE Input
3. Ejecutar Rafear → \--input-device CABLE_Output\ → \--output-device auricular
## Flags de realtime_processor.py

| Flag | Rango | Default | Descripción |
|------|-------|---------|-------------|
| \--input-device\ | ID int | default | Dispositivo de entrada |
| \--output-device\ | ID int | default | Dispositivo de salida |
| \--sample-rate\ | int | 48000 | Frecuencia de muestreo (Hz) |
| \--block-size\ | 64,128,... | 512 | Bloques de procesamiento (samples) |
| \--ear\ | left/right | left | Oído funcional |
| \--lr-intensity\ | 0.0-1.0 | 1.0 | Head shadow L/R (1.0=máximo) |
| \--fb-intensity\ | 0.0-1.0 | 0.3 | Front/Back cue (0.0=off) |
| \--ud-intensity\ | 0.0-1.0 | 0.3 | Elevación arriba/abajo (0.0=off) |
| \--clarity\ | 0.0-1.0 | 0.0 | Presence boost 3-5kHz (0.0=off) |
| \--brillo\ | 0.0-1.0 | 0.0 | High-shelf >2kHz (0.0=off) |
| \--low-cut\ | 0.0-1.0 | 0.0 | Highpass 80Hz anti-rumble (0.0=off) |
| \--compress\ | 0.0-1.0 | 0.0 | Soft compressor (0.0=off) |

### Nota sobre latencia

| Block-size | Latencia base | Uso |
|------------|---------------|-----|
| 256 | ~5.3ms | Mínima latencia, más CPU |
| 512 | ~10.6ms | Sweet spot (balance) |
| 1024 | ~21.3ms | Estable, algo de latencia |
| 2048 | ~42.7ms | Máxima estabilidad |

### Ejemplos de flags

**Sordera oído izquierdo, claridad de voces:**
`powershell
--ear right --clarity 0.5
`

**Con todos los filtros de calidad:**
`powershell
--clarity 0.4 --brillo 0.3 --low-cut 0.3 --compress 0.3
`

**Solo head shadow + low-cut + compressor (sin spatial cues):**
`powershell
--fb-intensity 0.0 --ud-intensity 0.0 --low-cut 0.4 --compress 0.5
`

## Tests

`powershell
python -m pytest tests/ -v
`

138 tests, 0 failing.

## Licencia

MIT
