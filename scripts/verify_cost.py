"""Verifica que progress/cost_log.json existe y tiene estructura válida."""

import json
import os
import sys

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
NC = "\033[0m"

REQUIRED_FIELDS = [
    "date", "feature_id", "feature_name", "model",
    "tokens_in", "tokens_out", "cost_usd", "duration", "agents",
]


def run():
    path = "progress/cost_log.json"
    if not os.path.exists(path):
        print(f"{YELLOW}[WARN]{NC}  {path} no existe todavía (se creará al cerrar la primera sesión)")
        return True

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"{RED}[FAIL]  {path} tiene JSON inválido: {e}{NC}")
        return False

    if not isinstance(data, dict) or "entries" not in data:
        print(f"{RED}[FAIL]  {path} debe tener un objeto con campo 'entries' (array){NC}")
        return False

    entries = data["entries"]
    if not isinstance(entries, list):
        print(f"{RED}[FAIL]  'entries' debe ser un array{NC}")
        return False

    all_ok = True
    for i, entry in enumerate(entries):
        missing = [f for f in REQUIRED_FIELDS if f not in entry]
        if missing:
            print(f"{RED}[FAIL]  Entrada {i} falta campos: {missing}{NC}")
            all_ok = False

        extra_keys = set(entry.keys()) - set(REQUIRED_FIELDS)
        if extra_keys:
            print(f"{YELLOW}[WARN]{NC}  Entrada {i} tiene campos extra: {extra_keys}")

        if not isinstance(entry.get("tokens_in"), (int, float)):
            print(f"{RED}[FAIL]  Entrada {i}: 'tokens_in' debe ser numérico{NC}")
            all_ok = False

        if not isinstance(entry.get("tokens_out"), (int, float)):
            print(f"{RED}[FAIL]  Entrada {i}: 'tokens_out' debe ser numérico{NC}")
            all_ok = False

        if not isinstance(entry.get("cost_usd"), (int, float)):
            print(f"{RED}[FAIL]  Entrada {i}: 'cost_usd' debe ser numérico{NC}")
            all_ok = False

        agents = entry.get("agents", [])
        if not isinstance(agents, list) or len(agents) == 0:
            print(f"{RED}[FAIL]  Entrada {i}: 'agents' debe ser un array no vacío{NC}")
            all_ok = False

    if all_ok:
        print(f"{GREEN}[OK]{NC}    {path} válido ({len(entries)} entradas)")

    return all_ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
