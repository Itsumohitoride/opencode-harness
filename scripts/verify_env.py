"""Verifica el entorno para MonoSpatial: Python, numpy, scipy, deps de audio."""

import importlib
import os
import shutil
import subprocess
import sys

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
NC = "\033[0m"

REQUIRED_PYTHON = (3, 11)
REQUIRED_PACKAGES = [
    "numpy",
    "scipy",
    "soundfile",
    "sounddevice",
    "PyQt6",
]

OPTIONAL_PACKAGES = [
    "libmysofa",  # para carga .sofa real (test offline usa IR sintética)
]


def check_python_version() -> bool:
    if sys.version_info < REQUIRED_PYTHON:
        ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        print(f"{RED}[FAIL]  Python >= 3.11 required (actual: {ver}){NC}")
        return False
    ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"{GREEN}[OK]{NC}    Python {ver}")
    return True


def check_package(name: str, optional: bool = False) -> bool:
    try:
        mod = importlib.import_module(name)
        ver = getattr(mod, "__version__", "unknown")
        tag = f"{YELLOW}[WARN]{NC}" if optional else f"{GREEN}[OK]{NC}"
        status = f"({ver})" if ver != "unknown" else ""
        print(f"{tag}    {name} {status}")
        return True
    except ImportError:
        tag = f"{YELLOW}[WARN]{NC}" if optional else f"{RED}[FAIL]{NC}"
        msg = "opcional" if optional else "obligatorio"
        print(f"{tag}  {name} no instalado ({msg})")
        return optional  # solo fail si es obligatorio


def check_audio_devices() -> bool:
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        if len(devices) == 0:
            print(f"{YELLOW}[WARN]{NC}  No se detectaron dispositivos de audio")
            return True
        print(f"{GREEN}[OK]{NC}    {len(devices)} dispositivos de audio detectados")
        return True
    except Exception:
        print(f"{YELLOW}[WARN]{NC}  No se pudo consultar dispositivos de audio")
        return True


def run() -> bool:
    print(f"{'='*50}")
    print(f"  MonoSpatial — Verificación de Entorno")
    print(f"{'='*50}\n")

    checks = [
        ("Python version", check_python_version()),
    ]

    print(f"\n--- Paquetes obligatorios ---")
    for pkg in REQUIRED_PACKAGES:
        checks.append((pkg, check_package(pkg)))

    print(f"\n--- Paquetes opcionales ---")
    for pkg in OPTIONAL_PACKAGES:
        check_package(pkg, optional=True)

    print(f"\n--- Audio ---")
    checks.append(("Audio devices", check_audio_devices()))

    all_ok = all(result for _, result in checks)

    print(f"\n{'='*50}")
    if all_ok:
        print(f"{GREEN}RESULTADO: Entorno listo para MonoSpatial{NC}")
    else:
        print(f"{RED}RESULTADO: Hay problemas que resolver{NC}")
    print(f"{'='*50}")

    return all_ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)