# MonoSpatial — Plan de Implementación en Código
### Guía completa de desarrollo Python para audio 3D monoaural

---

## Stack de Dependencias

```bash
pip install numpy scipy soundfile sounddevice pysofaconventions libmysofa-python PyQt6
```

**Base de datos HRTF (gratis):**
- SADIE II: https://www.york.ac.uk/sadie-project/database.html
- Formato `.sofa` — directamente compatible con libmysofa

---

## Etapa 1 — HRTF Engine (hrtf_engine.py)

Núcleo del sistema. Carga la base de datos HRTF, aplica filtros monoaurales y combina todos los cues espaciales.

```python
# hrtf_engine.py
import numpy as np
from scipy.signal import fftconvolve
import soundfile as sf
import libmysofa

class HRTFDatabase:
    def __init__(self, sofa_path: str, ear: str = "left"):
        self.hrtf = libmysofa.load(sofa_path)
        self.ear_index = 0 if ear == "left" else 1
        self._cache = {}

    def get_filter(self, azimuth: float, elevation: float) -> np.ndarray:
        key = (round(azimuth, 1), round(elevation, 1))
        if key in self._cache:
            return self._cache[key]

        filter_left, filter_right, delay = self.hrtf.interpolate(
            azimuth, elevation, 0.0
        )
        ir = filter_left if self.ear_index == 0 else filter_right
        self._cache[key] = ir
        return ir


class MonauralSpatialEncoder:
    def __init__(self, hrtf_db: HRTFDatabase, sample_rate: int = 48000):
        self.hrtf_db = hrtf_db
        self.sample_rate = sample_rate

    def apply_spectral_elevation_cue(
        self, signal: np.ndarray, elevation: float
    ) -> np.ndarray:
        from scipy.signal import butter, sosfilt
        output = signal.copy()
        if elevation > 20:
            sos = butter(2, [7500, 10500], btype='bandpass',
                        fs=self.sample_rate, output='sos')
            output = signal + sosfilt(sos, signal) * 0.4
        elif elevation < -20:
            sos = butter(2, [3500, 6500], btype='bandpass',
                        fs=self.sample_rate, output='sos')
            output = signal - sosfilt(sos, signal) * 0.3
        return output

    def apply_front_back_cue(
        self, signal: np.ndarray, azimuth: float
    ) -> np.ndarray:
        from scipy.signal import butter, sosfilt
        if abs(azimuth) > 90:
            sos = butter(2, [7500, 8500], btype='bandstop',
                        fs=self.sample_rate, output='sos')
            signal = sosfilt(sos, signal)
            delay_samples = int(0.012 * self.sample_rate)
            reverb = np.zeros_like(signal)
            reverb[delay_samples:] = signal[:-delay_samples] * 0.25
            signal = signal + reverb
        return signal

    def encode_source(
        self,
        signal: np.ndarray,
        azimuth: float,
        elevation: float,
        distance: float = 1.0
    ) -> np.ndarray:
        hrtf_filter = self.hrtf_db.get_filter(azimuth, elevation)
        output = fftconvolve(signal, hrtf_filter, mode='same')
        output = self.apply_spectral_elevation_cue(output, elevation)
        output = self.apply_front_back_cue(output, azimuth)
        gain = 1.0 / max(1.0, distance ** 2)
        return output * gain

    def mix_sources(self, sources: list) -> np.ndarray:
        if not sources:
            return np.zeros(1)
        max_len = max(len(s[0]) for s in sources)
        output = np.zeros(max_len)
        for signal, azimuth, elevation, distance in sources:
            encoded = self.encode_source(signal, azimuth, elevation, distance)
            output[:len(encoded)] += encoded
        peak = np.max(np.abs(output))
        if peak > 0.95:
            output = output * (0.95 / peak)
        return output
```

---

## Etapa 2 — Test Offline (test_offline.py)

Valida el engine con archivos de audio antes de pasar a tiempo real.

```python
# test_offline.py
import numpy as np
import soundfile as sf
from hrtf_engine import HRTFDatabase, MonauralSpatialEncoder

def test_with_file(input_stereo: str, output_path: str):
    audio, sr = sf.read(input_stereo)
    left = audio[:, 0]
    right = audio[:, 1]

    db = HRTFDatabase("path/to/SADIE_subject_001.sofa", ear="left")
    encoder = MonauralSpatialEncoder(db, sample_rate=sr)

    sources = [
        (left,  -30.0, 0.0, 1.0),
        (right, +30.0, 0.0, 1.0),
    ]

    mono_spatial = encoder.mix_sources(sources)
    sf.write(output_path, mono_spatial, sr)
    print(f"Guardado en {output_path} — escuchalo con UN solo auricular")

test_with_file("game_stereo_sample.wav", "output_mono_spatial.wav")
```

---

## Etapa 3 — Procesamiento en Tiempo Real (realtime_processor.py)

Intercepta el audio del juego en vivo con latencia menor a 11ms.

```python
# realtime_processor.py
import numpy as np
import sounddevice as sd
from hrtf_engine import HRTFDatabase, MonauralSpatialEncoder

SAMPLE_RATE = 48000
BLOCK_SIZE = 512  # ~10.6ms de latencia

db = HRTFDatabase("SADIE_subject_001.sofa", ear="left")
encoder = MonauralSpatialEncoder(db, sample_rate=SAMPLE_RATE)

def process_block(indata, outdata, frames, time, status):
    if status:
        print(f"Stream status: {status}")
    left  = indata[:, 0]
    right = indata[:, 1]
    sources = [
        (left,  -30.0, 0.0, 1.0),
        (right, +30.0, 0.0, 1.0),
    ]
    mono_out = encoder.mix_sources(sources)
    outdata[:, 0] = mono_out[:frames]

def list_devices():
    print(sd.query_devices())

def start_processing(input_device: int, output_device: int):
    with sd.Stream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        dtype='float32',
        channels=(2, 1),
        device=(input_device, output_device),
        callback=process_block
    ):
        print("Procesando audio espacial monoaural... (Ctrl+C para detener)")
        while True:
            sd.sleep(1000)

if __name__ == "__main__":
    list_devices()
    start_processing(input_device=3, output_device=1)
```

---

## Etapa 4 — Convolución Optimizada (optimized_convolver.py)

Overlap-save para minimizar latencia en producción.

```python
# optimized_convolver.py
import numpy as np

class OverlapSaveConvolver:
    def __init__(self, ir: np.ndarray, block_size: int):
        self.block_size = block_size
        self.ir_len = len(ir)
        self.fft_size = block_size + self.ir_len - 1
        self.fft_size = 2 ** int(np.ceil(np.log2(self.fft_size)))
        # Pre-computar FFT del filtro — solo una vez por angulo
        self.IR_F = np.fft.rfft(ir, n=self.fft_size)
        self.overlap = np.zeros(self.ir_len - 1)

    def process(self, block: np.ndarray) -> np.ndarray:
        x = np.concatenate([block, np.zeros(self.fft_size - len(block))])
        X_F = np.fft.rfft(x)
        Y_F = X_F * self.IR_F
        y = np.fft.irfft(Y_F)[:self.fft_size]
        out_len = len(block)
        y[:self.ir_len - 1] += self.overlap
        self.overlap = y[out_len:out_len + self.ir_len - 1]
        return y[:out_len].astype(np.float32)
```

---

## Etapa 5 — App de Calibración (calibration_ui.py)

Interfaz gráfica para ajuste personalizado de parámetros HRTF.

```python
# calibration_ui.py
from PyQt6.QtWidgets import (QApplication, QMainWindow, QSlider,
                              QLabel, QPushButton, QVBoxLayout, QWidget)
from PyQt6.QtCore import Qt
import sys, numpy as np, sounddevice as sd

class CalibrationApp(QMainWindow):
    def __init__(self, encoder):
        super().__init__()
        self.encoder = encoder
        self.setWindowTitle("MonoSpatial — Calibracion")
        self.setMinimumWidth(400)
        self._current_test_angle = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Intensidad HRTF"))
        self.hrtf_slider = QSlider(Qt.Orientation.Horizontal)
        self.hrtf_slider.setRange(0, 100)
        self.hrtf_slider.setValue(75)
        layout.addWidget(self.hrtf_slider)

        layout.addWidget(QLabel("Reverb trasero (front-back cue)"))
        self.reverb_slider = QSlider(Qt.Orientation.Horizontal)
        self.reverb_slider.setRange(0, 100)
        self.reverb_slider.setValue(30)
        layout.addWidget(self.reverb_slider)

        self.test_btn = QPushButton("Reproducir sonido de prueba")
        self.test_btn.clicked.connect(self.play_test_sound)
        layout.addWidget(self.test_btn)

        self.result_label = QLabel("El sonido viene de adelante o de atras?")
        layout.addWidget(self.result_label)

        btn_front = QPushButton("Adelante")
        btn_rear  = QPushButton("Atras")
        btn_front.clicked.connect(lambda: self.record_answer("front"))
        btn_rear.clicked.connect(lambda: self.record_answer("rear"))
        layout.addWidget(btn_front)
        layout.addWidget(btn_rear)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def play_test_sound(self):
        import random
        angles = [0.0, 180.0]
        self._current_test_angle = random.choice(angles)
        sr = 48000
        noise = np.random.randn(sr // 2).astype(np.float32) * 0.3
        encoded = self.encoder.encode_source(
            noise, azimuth=self._current_test_angle, elevation=0.0
        )
        sd.play(encoded, sr)

    def record_answer(self, answer: str):
        if self._current_test_angle is None:
            return
        correct = "front" if abs(self._current_test_angle) < 90 else "rear"
        if answer == correct:
            self.result_label.setText("Correcto!")
        else:
            self.result_label.setText("Incorrecto — ajusta los sliders y proba de nuevo")

def launch_ui(encoder):
    app = QApplication(sys.argv)
    window = CalibrationApp(encoder)
    window.show()
    sys.exit(app.exec())
```

---

## Orden de Implementación

```
Paso 1: pip install + descargar SADIE II .sofa
Paso 2: Correr test_offline.py con cualquier WAV estereo
Paso 3: Escuchar con UN solo auricular y validar la diferencia
Paso 4: Configurar Virtual Cable y correr realtime_processor.py
Paso 5: Abrir el juego y probar en vivo
Paso 6: Calibrar con calibration_ui.py
```

---

## Notas de Latencia

| Block Size | Latencia aprox | Uso recomendado        |
|------------|---------------|------------------------|
| 256        | ~5.3ms        | Produccion C++/JUCE    |
| 512        | ~10.6ms       | Python (aceptable)     |
| 1024       | ~21ms         | Prototipo / debug      |

El objetivo para gaming es mantenerse por debajo de **10ms** de latencia de procesamiento.
