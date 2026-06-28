"""Construit un registre d'erreurs (brouillon) à partir d'un CSV de prédictions.

Livrable SHOULD de l'appel d'offre : « Registre d'erreurs sur 20 à 30 cas
commentés ». Le script applique la taxonomie du protocole d'évaluation
(docs/evaluation_protocol.md) :

    FN  faux négatif        : anomalie présente prédite normale
    FP  faux positif        : image normale prédite suspecte
    UA  incertitude acceptable : signes faibles / image limitée → uncertain
    JF  JSON format error   : sortie non exploitable
    HT  hallucination texte  : mention d'un signe non visible (revue manuelle)

Les codes FN/FP/UA/JF sont déduits automatiquement ; HT doit être complété à la
main après lecture des justifications. Le `comment` reste à compléter par
l'étudiant : c'est le cœur de l'analyse d'erreurs défendue à l'oral.

Usage :
    python eval/build_error_register.py \
        --predictions /tmp/eval/baseline_predictions.csv \
        --out /tmp/eval/baseline_error_register.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

FIELDS = [
    "case_id",
    "ground_truth",
    "prediction",
    "confidence",
    "error_type",
    "severity",
    "comment",
    "corrective_action",
]


def classify(label: str, pred: str, json_valid: bool) -> tuple[str, str, str]:
    """Retourne (error_type, severity, corrective_action)."""
    if not json_valid:
        return "JF", "high", "fix output schema / parsing"
    if label == pred:
        return "OK", "none", "keep"
    # Incertitude : garde-fou plutôt qu'erreur dure.
    if pred == "uncertain":
        return "UA", "low", "keep uncertainty rule"
    if label == "suspected_opacity" and pred == "normal":
        return "FN", "high", "review threshold and prompt (missed opacity)"
    if label == "normal" and pred == "suspected_opacity":
        return "FP", "medium", "improve specificity (overcall)"
    if label == "uncertain" and pred != "uncertain":
        # Le modèle a tranché là où l'attendu était 'uncertain'.
        return "FP" if pred == "suspected_opacity" else "FN", "medium", \
            "should have abstained on limited evidence"
    return "MISC", "medium", "manual review"


def build(predictions: Path, out: Path) -> dict[str, int]:
    with predictions.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    counts: dict[str, int] = {}
    out_rows = []
    for r in rows:
        label = r["label"]
        pred = r["predicted_class"]
        json_valid = str(r.get("json_valid", "True")).lower() in {"true", "1"}
        etype, severity, action = classify(label, pred, json_valid)
        counts[etype] = counts.get(etype, 0) + 1
        out_rows.append(
            {
                "case_id": r["case_id"],
                "ground_truth": label,
                "prediction": pred,
                "confidence": r.get("confidence", ""),
                "error_type": etype,
                "severity": severity,
                "comment": "" if etype != "OK" else "correct",
                "corrective_action": action,
            }
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out_rows)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    counts = build(args.predictions, args.out)
    total = sum(counts.values())
    print(f"Registre écrit : {args.out}  ({total} cas)")
    for k in sorted(counts):
        print(f"  {k}: {counts[k]}")
    print("\nÀ compléter à la main : colonne 'comment' et codes HT (hallucinations).")


if __name__ == "__main__":
    main()
