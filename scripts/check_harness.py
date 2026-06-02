#!/usr/bin/env python3
"""Orquestador maestro: verifica entorno, archivos, features y tests."""

import os
import sys
import platform

VENV_DIR = ".venv"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
NC = "\033[0m"


def _ensure_venv():
    """Re-ejecutar con el Python del .venv si no estamos ya dentro."""
    is_windows = platform.system() == "Windows"
    if is_windows:
        venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(VENV_DIR, "bin", "python3")

    abs_exec = os.path.abspath(sys.executable)
    abs_venv = os.path.abspath(VENV_DIR)
    if not abs_exec.startswith(abs_venv):
        if not os.path.exists(venv_python):
            print(f"{RED}[FAIL]  .venv no encontrado. Crea: uv venv{NC}")
            print(f"{YELLOW}[HINT]  Buscaba: {os.path.abspath(venv_python)}{NC}")
            sys.exit(1)
        os.execv(venv_python, [venv_python] + sys.argv)


def ok(msg):
    print(f"{GREEN}[OK]{NC}    {msg}")


def fail(msg):
    print(f"{RED}[FAIL]  {msg}{NC}")


def warn(msg):
    print(f"{YELLOW}[WARN]{NC}  {msg}")


def _run_section(title, module_fn):
    print(f"\n-- {title} " + "-" * (60 - len(title)))
    return module_fn()


def main():
    _ensure_venv()

    _scripts_dir = os.path.dirname(os.path.abspath(__file__))
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)

    import verify_env
    import verify_files
    import verify_features
    import run_tests
    import verify_cost

    exit_code = 0

    if not _run_section("1. Verificando entorno", verify_env.run):
        exit_code = 1

    if exit_code == 0:
        if not _run_section("2. Verificando archivos base", verify_files.run):
            exit_code = 1

    if exit_code == 0:
        if not _run_section("3. Validando feature_list.json", verify_features.run):
            exit_code = 1

    if exit_code == 0:
        if not _run_section("4. Ejecutando tests", run_tests.run):
            exit_code = 1

    if exit_code == 0:
        if not _run_section("5. Verificando cost_log.json", verify_cost.run):
            exit_code = 1

    print("\n-- 6. Resumen " + "-" * 44)
    if exit_code == 0:
        ok("Entorno listo. Puedes empezar a trabajar.")
    else:
        fail("Entorno NO esta listo. Resuelve los errores antes de avanzar.")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()