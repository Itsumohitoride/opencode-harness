"""Verifica que existen los archivos base del harness."""

import os
import sys

GREEN = "\033[32m"
RED = "\033[31m"
NC = "\033[0m"

HARNESS_FILES = [
    "AGENTS.md",
    "feature_list.json",
    "progress/current.md",
    "docs/architecture.md",
    "docs/conventions.md",
    "docs/deployment.md",
    "docs/configuration.md",
    "docs/verification.md",
    "CHECKPOINTS.md",
]


def run():
    all_ok = True
    for path in HARNESS_FILES:
        if os.path.exists(path):
            print(f"{GREEN}[OK]{NC}    Existe {path}")
        else:
            print(f"{RED}[FAIL]  Falta archivo base: {path}{NC}")
            all_ok = False
    return all_ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
