"""Calibration UI for MonoSpatial — PyQt6 app for HRTF parameter adjustment
and front/back discrimination testing.

Provides:
  - CalibrationWindow: PyQt6 QMainWindow with ear selection, HRTF intensity
    and rear reverb sliders, and an interactive front/back discrimination test.
  - parse_args: CLI argument parsing.
  - main: Entry point.

Dependencies:
  - PyQt6
  - numpy
  - sounddevice
  - hrtf_engine (MonauralSpatialEncoder, HRTFDatabase)

Example:
  Run directly::

      python src/calibration_ui.py
"""

from __future__ import annotations

import argparse
import random
import sys

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

try:
    from src.hrtf_engine import HRTFDatabase, MonauralSpatialEncoder
except ImportError:
    from hrtf_engine import HRTFDatabase, MonauralSpatialEncoder


class CalibrationWindow(QMainWindow):
    """PyQt6 main window for HRTF calibration.

    Provides sliders for HRTF intensity and rear reverb, an ear selector,
    and an interactive front/back discrimination test with immediate feedback.

    Attributes:
        SAMPLE_RATE: Audio sample rate in Hz (48 000).
        TEST_DURATION: Duration of test sounds in seconds (0.5).
    """

    SAMPLE_RATE: int = 48000
    TEST_DURATION: float = 0.5

    def __init__(self) -> None:
        """Initialize the calibration window with all UI components."""
        super().__init__()

        self.setWindowTitle("MonoSpatial — Calibración HRTF")
        self.setFixedSize(500, 400)

        # ── HRTF engine (synthetic mode, no .sofa file required) ───────
        self._hrtf_db: HRTFDatabase = HRTFDatabase("dummy.sofa", ear="left")
        self._encoder: MonauralSpatialEncoder = MonauralSpatialEncoder(
            self._hrtf_db,
            sample_rate=self.SAMPLE_RATE,
        )

        # ── calibration state ──────────────────────────────────────────
        self._current_azimuth: float = 0.0
        self._current_answer: str = ""
        self._score_correct: int = 0
        self._score_total: int = 0

        # ── build UI ───────────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)

        # Section 1 — Ear selection
        ear_label = QLabel("Oído funcional:")
        self._ear_combo = QComboBox()
        self._ear_combo.addItem("Oído izquierdo funcional")
        self._ear_combo.addItem("Oído derecho funcional")
        ear_layout = QHBoxLayout()
        ear_layout.addWidget(ear_label)
        ear_layout.addWidget(self._ear_combo)
        ear_layout.addStretch()
        layout.addLayout(ear_layout)

        # Section 2 — Sliders
        # Intensity slider
        intensity_layout = QHBoxLayout()
        intensity_label = QLabel("Intensidad HRTF:")
        self._intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self._intensity_slider.setRange(0, 100)
        self._intensity_slider.setValue(80)
        self._intensity_value_label = QLabel("80")
        self._intensity_slider.valueChanged.connect(
            lambda v: self._intensity_value_label.setText(str(v)),
        )
        intensity_layout.addWidget(intensity_label)
        intensity_layout.addWidget(self._intensity_slider)
        intensity_layout.addWidget(self._intensity_value_label)
        layout.addLayout(intensity_layout)

        # Reverb slider
        reverb_layout = QHBoxLayout()
        reverb_label = QLabel("Reverb trasero:")
        self._reverb_slider = QSlider(Qt.Orientation.Horizontal)
        self._reverb_slider.setRange(0, 100)
        self._reverb_slider.setValue(50)
        self._reverb_value_label = QLabel("50")
        self._reverb_slider.valueChanged.connect(
            lambda v: self._reverb_value_label.setText(str(v)),
        )
        reverb_layout.addWidget(reverb_label)
        reverb_layout.addWidget(self._reverb_slider)
        reverb_layout.addWidget(self._reverb_value_label)
        layout.addLayout(reverb_layout)

        # Section 3 — Test controls
        layout.addSpacing(8)
        test_label = QLabel("Test de discriminación front/back:")
        layout.addWidget(test_label)

        self._play_button = QPushButton("▶ Reproducir sonido de prueba")
        self._play_button.clicked.connect(self.play_test_sound)
        layout.addWidget(self._play_button)

        # Answer buttons
        answer_layout = QHBoxLayout()
        self._front_button = QPushButton("Adelante")
        self._front_button.clicked.connect(lambda: self.check_answer("front"))
        self._back_button = QPushButton("Atrás")
        self._back_button.clicked.connect(lambda: self.check_answer("back"))
        answer_layout.addWidget(self._front_button)
        answer_layout.addWidget(self._back_button)
        layout.addLayout(answer_layout)

        # Feedback label
        self._feedback_label = QLabel("")
        self._feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._feedback_label)

        # Score label
        self._score_label = QLabel("Aciertos: 0 / 0")
        self._score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._score_label)

        layout.addStretch()

    # ── Public methods ──────────────────────────────────────────────────

    def play_test_sound(self) -> None:
        """Generate, spatialize and play a test sound at a random angle.

        Creates 0.5 s of white noise at 48 kHz, encodes it with the
        :class:`MonauralSpatialEncoder` at either 0° (front) or 180° (back),
        applies the current slider values, and plays the result through the
        default audio output.
        """
        n_samples = int(self.TEST_DURATION * self.SAMPLE_RATE)
        noise = np.random.randn(n_samples).astype(np.float32)

        self._current_azimuth = random.choice([0.0, 180.0])

        # Full spatial encoding via HRTF engine
        out = self._encoder.encode_source(
            noise,
            azimuth=self._current_azimuth,
            elevation=0.0,
        )

        # Apply intensity gain (post-gain)
        intensity = self._intensity_slider.value() / 100.0
        out = out * max(0.01, intensity)

        # Apply rear reverb (additional cue for behind sounds)
        reverb_level = self._reverb_slider.value() / 100.0
        if reverb_level > 0.0 and abs(self._current_azimuth) > 90.0:
            delay_samples = int(0.012 * self.SAMPLE_RATE)
            reverb = np.zeros_like(out)
            reverb[delay_samples:] = out[:-delay_samples] * 0.25 * reverb_level
            out = out + reverb
            # Normalise to prevent clipping
            peak = float(np.max(np.abs(out)))
            if peak > 0.95 and peak > 0.0:
                out = out * (0.95 / peak)

        self._current_answer = "front" if self._current_azimuth == 0.0 else "back"

        sd.play(out, samplerate=self.SAMPLE_RATE)

    def check_answer(self, answer: str) -> None:
        """Check the user's answer against the correct direction.

        Args:
            answer: User's answer — ``"front"`` (adelante) or
                ``"back"`` (atrás).
        """
        if not self._current_answer:
            return  # No test sound has been played yet

        self._score_total += 1

        if answer == self._current_answer:
            self._score_correct += 1
            self._feedback_label.setText("✅ ¡Correcto!")
            self._feedback_label.setStyleSheet(
                "color: green; font-weight: bold; font-size: 14px;",
            )
        else:
            self._feedback_label.setText("❌ Incorrecto")
            self._feedback_label.setStyleSheet(
                "color: red; font-weight: bold; font-size: 14px;",
            )

        self._score_label.setText(
            f"Aciertos: {self._score_correct} / {self._score_total}",
        )

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def score_correct(self) -> int:
        """Number of correct answers."""
        return self._score_correct

    @property
    def score_total(self) -> int:
        """Total number of answers submitted."""
        return self._score_total


# =========================================================================
# CLI
# =========================================================================


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the calibration UI.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Parsed ``argparse.Namespace``.
    """
    parser = argparse.ArgumentParser(
        description="MonoSpatial — Calibración HRTF",
    )
    parser.add_argument(
        "--ear",
        type=str,
        default="left",
        choices=["left", "right"],
        help="Functional ear (default: left)",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Entry point for the calibration UI.

    Creates the PyQt6 application, shows the calibration window,
    and enters the event loop.
    """
    app = QApplication(sys.argv)
    window = CalibrationWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
