"""Valida la estructura e integridad de feature_list.json."""

import json
import re
import sys

GREEN = "\033[32m"
RED = "\033[31m"
NC = "\033[0m"

CANONICAL_STATUSES = {"pending", "in_progress", "testing", "done", "blocked"}
ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


def _check(cond, msg):
    if cond:
        print(f"{GREEN}[OK]{NC}    {msg}")
        return True
    print(f"{RED}[FAIL]  {msg}{NC}")
    return False


def run():
    try:
        with open("feature_list.json") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"{RED}[FAIL]  feature_list.json no encontrado{NC}")
        return False
    except json.JSONDecodeError as e:
        print(f"{RED}[FAIL]  feature_list.json inválido: {e}{NC}")
        return False

    # ── validar valid_status ──────────────────────────────────────────
    file_statuses = set(data.get("rules", {}).get("valid_status", []))
    if file_statuses != CANONICAL_STATUSES:
        extra = file_statuses - CANONICAL_STATUSES
        missing = CANONICAL_STATUSES - file_statuses
        parts = []
        if extra:
            parts.append(f"sobran: {sorted(extra)}")
        if missing:
            parts.append(f"faltan: {sorted(missing)}")
        print(
            f"{RED}[FAIL]  valid_status no coincide con el set canónico ({', '.join(parts)}){NC}"
        )
        return False
    _check(True, "valid_status coincide con el set canónico")

    # ── validar features ──────────────────────────────────────────────
    features = data.get("features", [])
    in_progress = [f for f in features if f["status"] == "in_progress"]

    if len(in_progress) > 1:
        ids = [f["id"] for f in in_progress]
        print(f"{RED}[FAIL]  Hay {len(in_progress)} features en in_progress (máximo 1): {ids}{NC}")
        return False

    all_ok = True
    for feat in features:
        fid = feat.get("id")

        # status válido
        sid = feat.get("status")
        if sid not in CANONICAL_STATUSES:
            print(f"{RED}[FAIL]  Estado inválido en feature {fid}: {sid}{NC}")
            all_ok = False

        # created_at presente y con formato ISO
        cat = feat.get("created_at")
        if not cat or not ISO_RE.match(cat):
            print(f"{RED}[FAIL]  feature {fid}: created_at ausente o con formato inválido: {cat}{NC}")
            all_ok = False

        # transitions es un array
        trans = feat.get("transitions")
        if not isinstance(trans, list):
            print(f"{RED}[FAIL]  feature {fid}: transitions debe ser un array{NC}")
            all_ok = False
        else:
            # cada transición tiene from / to / at válidos
            for i, t in enumerate(trans):
                if not isinstance(t, dict):
                    print(f"{RED}[FAIL]  feature {fid}: transitions[{i}] no es un objeto{NC}")
                    all_ok = False
                    continue
                tf = t.get("from")
                tt = t.get("to")
                ta = t.get("at")
                if tf not in CANONICAL_STATUSES:
                    print(f"{RED}[FAIL]  feature {fid}: transitions[{i}].from inválido: {tf}{NC}")
                    all_ok = False
                if tt not in CANONICAL_STATUSES:
                    print(f"{RED}[FAIL]  feature {fid}: transitions[{i}].to inválido: {tt}{NC}")
                    all_ok = False
                if not ta or not ISO_RE.match(ta):
                    print(f"{RED}[FAIL]  feature {fid}: transitions[{i}].at ausente o inválido: {ta}{NC}")
                    all_ok = False

            # si hay transiciones, la última debe coincidir con status actual
            if trans and all_ok:
                last_to = trans[-1]["to"]
                if last_to != sid:
                    print(
                        f"{RED}[FAIL]  feature {fid}: última transición to={last_to} "
                        f"no coincide con status actual={sid}{NC}"
                    )
                    all_ok = False

    if all_ok:
        print(f"{GREEN}[OK]{NC}    feature_list.json válido ({len(features)} features)")

    return all_ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
