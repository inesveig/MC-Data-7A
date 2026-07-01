"""Pilote la boucle d'éval réelle case par case, un sous-process par image.

Chaque cas est traité par un `python eval/run_one_case.py` séparé (voir ce
fichier) : le process charge MedGemma, infère, écrit son résultat, puis
quitte. La mémoire est donc intégralement libérée entre deux images — on
évite ainsi l'accumulation qui a fait grimper le swap et bloqué la machine
lors d'une boucle unique longue durée dans un seul process.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--mode", choices=["baseline", "improved"], default="baseline")
    parser.add_argument("--db-path", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="fichier .jsonl de sortie")
    args = parser.parse_args()

    cases = list(csv.DictReader(args.cases.open(newline="", encoding="utf-8")))
    args.out.parent.mkdir(parents=True, exist_ok=True)

    with args.out.open("a", encoding="utf-8") as out_f:
        for i, case in enumerate(cases, 1):
            t0 = time.perf_counter()
            result = subprocess.run(
                [
                    sys.executable, str(ROOT / "eval" / "run_one_case.py"),
                    "--case-id", case["case_id"],
                    "--image-path", case["image_path"],
                    "--label", case["label"],
                    "--mode", args.mode,
                    "--db-path", str(args.db_path),
                ],
                capture_output=True, text=True, cwd=ROOT,
            )
            dt = time.perf_counter() - t0
            if result.returncode != 0:
                print(f"[{i}/{len(cases)}] ERREUR case={case['case_id']} ({dt:.0f}s)", flush=True)
                print(result.stderr[-2000:], flush=True)
                continue
            line = result.stdout.strip().splitlines()[-1]
            out_f.write(line + "\n")
            out_f.flush()
            row = json.loads(line)
            print(
                f"[{i}/{len(cases)}] {case['case_id']} label={row['label']} "
                f"pred={row['predicted_class']} ({dt:.0f}s)",
                flush=True,
            )


if __name__ == "__main__":
    main()
