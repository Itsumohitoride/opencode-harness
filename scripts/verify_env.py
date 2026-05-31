"""Verifica el entorno: uv, .venv, Python version y dependencias."""

import os
import shutil
import subprocess
import sys

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
NC = "\033[0m"


def run():
    all_ok = True

    # uv instalado
    uv_path = shutil.which("uv")
    if uv_path:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        ver = result.stdout.strip()
        print(f"{GREEN}[OK]{NC}    uv -> {ver}")
    else:
        print(f"{RED}[FAIL]  uv no está instalado. Instala: curl -LsSf https://astral.sh/uv/install.sh | sh{NC}")
        all_ok = False

    # .venv existe
    venv_python = os.path.join(".venv", "bin", "python3")
    if not os.path.exists(venv_python):
        print(f"{RED}[FAIL]  .venv no encontrado. Crea: uv venv{NC}")
        return False
    print(f"{GREEN}[OK]{NC}    .venv encontrado")

    # Python version
    if sys.version_info < (3, 9):
        ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        print(f"{RED}[FAIL]  Se requiere Python >= 3.9 (actual: {ver}){NC}")
        all_ok = False
    else:
        ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        print(f"{GREEN}[OK]{NC}    Python {ver}")

    # Dependencias sincronizadas
    if not all_ok:
        return False

    has_pyproject = os.path.exists("pyproject.toml")
    has_requirements = os.path.exists("requirements.txt")

    if has_pyproject or has_requirements:
        if uv_path:
            sync_file = "pyproject.toml" if has_pyproject else "requirements.txt"
            result = subprocess.run(
                ["uv", "sync", "--frozen"],
                capture_output=True, text=True, cwd=os.getcwd()
            )
            if result.returncode != 0:
                print(f"{RED}[FAIL]  Dependencias no sincronizadas. Corre: uv sync{NC}")
                all_ok = False
            else:
                print(f"{GREEN}[OK]{NC}    Dependencias sincronizadas ({sync_file})")
        else:
            warn("uv no disponible — no se puede verificar sincronización de dependencias")
    else:
        print(f"{YELLOW}[WARN]{NC}  No hay pyproject.toml ni requirements.txt")

    return all_ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
