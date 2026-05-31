"""Descubre y ejecuta los tests del proyecto."""

import os
import subprocess
import sys

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
NC = "\033[0m"

# Intenta unittest primero, luego pytest, etc.
TEST_RUNNERS = [
    (["-m", "unittest", "discover", "-s", "tests", "-v"], "unittest"),
    (["-m", "pytest", "tests", "-v"], "pytest"),
]


def run():
    if not os.path.isdir("tests"):
        print(f"{YELLOW}[WARN]{NC}  tests/ no existe todavía")
        return True

    for args, name in TEST_RUNNERS:
        try:
            result = subprocess.run(
                [sys.executable] + args,
                capture_output=True, text=True
            )
            combined = (result.stdout + result.stderr).strip()
            if combined:
                print(combined)

            if "Ran 0 tests" in combined:
                print(f"{YELLOW}[WARN]{NC}  No se encontraron tests ({name})")
                return True

            if result.returncode == 0:
                print(f"{GREEN}[OK]{NC}    Todos los tests pasan ({name})")
                return True

            print(f"{RED}[FAIL]  Hay tests rotos ({name}){NC}")
            return False
        except FileNotFoundError:
            continue

    print(f"{RED}[FAIL]  No se encontró un runner de tests disponible{NC}")
    return False


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
