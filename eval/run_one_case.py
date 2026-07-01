"""Évalue UN SEUL cas avec le vrai MedGemma, dans un process isolé.

Sert de brique à un pilote bash qui boucle case par case : chaque appel charge
le modèle, infère, écrit son résultat en JSON puis quitte — la mémoire est
donc intégralement libérée entre deux images (contrairement à une boucle dans
un seul process long, qui a fait grimper le swap et bloqué la machine).

Usage :
    python eval/run_one_case.py --case-id ID --image-path PATH --label LABEL \
        --mode baseline --db-path /tmp/evidence.sqlite >> results.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.database import insert_run
from src.guardrails import apply_safety_guardrails, validate_prediction
from src.medgemma_baseline import medgemma_predict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--image-path", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--mode", choices=["baseline", "improved"], default="baseline")
    parser.add_argument("--db-path", type=Path, required=True)
    args = parser.parse_args()

    pred = apply_safety_guardrails(medgemma_predict(args.image_path, mode=args.mode))
    valid, errors = validate_prediction(pred)
    insert_run(args.db_path, args.case_id, args.image_path, pred)

    row = {
        "case_id": args.case_id,
        "label": args.label,
        "predicted_class": pred["predicted_class"],
        "confidence": pred["confidence"],
        "json_valid": valid,
        "warning": pred.get("warning", ""),
        "latency_ms": pred.get("latency_ms", 0),
        "guardrail_errors": ";".join(errors),
    }
    print(json.dumps(row))


if __name__ == "__main__":
    main()
