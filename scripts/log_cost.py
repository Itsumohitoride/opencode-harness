#!/usr/bin/env python3
"""CLI para registrar costos de sesión en progress/cost_log.json.

Uso:
    python3 scripts/log_cost.py \\
        --feature-id 1 \\
        --feature-name "setup_project" \\
        --model "claude-sonnet-4" \\
        --tokens-in 50000 \\
        --tokens-out 12000 \\
        --cost-usd 2.15 \\
        --duration "2h 30m" \\
        --agents "leader,implementer,reviewer"

Ejecutar sin args muestra esta ayuda.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone


COST_LOG_PATH = "progress/cost_log.json"


def _load_log():
    if os.path.exists(COST_LOG_PATH):
        with open(COST_LOG_PATH) as f:
            return json.load(f)
    return {"entries": []}


def _save_log(data):
    os.makedirs(os.path.dirname(COST_LOG_PATH), exist_ok=True)
    with open(COST_LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Registra el costo de una sesión en progress/cost_log.json"
    )
    parser.add_argument("--feature-id", type=int, required=True)
    parser.add_argument("--feature-name", type=str, required=True)
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--tokens-in", type=int, required=True)
    parser.add_argument("--tokens-out", type=int, required=True)
    parser.add_argument("--cost-usd", type=float, required=True)
    parser.add_argument("--duration", type=str, required=True,
                        help="Duración de la sesión, ej. '2h 30m'")
    parser.add_argument("--agents", type=str, required=True,
                        help="Agentes participantes separados por coma, ej. 'leader,implementer,reviewer'")

    args = parser.parse_args()

    entry = {
        "date": datetime.now(timezone.utc).isoformat(),
        "feature_id": args.feature_id,
        "feature_name": args.feature_name,
        "model": args.model,
        "tokens_in": args.tokens_in,
        "tokens_out": args.tokens_out,
        "cost_usd": args.cost_usd,
        "duration": args.duration,
        "agents": [a.strip() for a in args.agents.split(",")],
    }

    data = _load_log()
    data["entries"].append(entry)
    _save_log(data)

    feature_ref = f"#{args.feature_id} ({args.feature_name})"
    print(f"[OK] Costo registrado para feature {feature_ref}: "
          f"${args.cost_usd:.2f} ({args.model})")


if __name__ == "__main__":
    main()
