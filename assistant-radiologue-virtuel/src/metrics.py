"""
Calcul des métriques d'évaluation.
accuracy, macro-F1, sensibilité, spécificité, taux JSON valide, latence, taux incertitude.
"""

import json
import csv
from pathlib import Path
from typing import Optional


CLASSES = ["normal", "suspected_opacity", "uncertain"]


def compute_metrics(results: list[dict]) -> dict:
    """
    Calcule toutes les métriques à partir d'une liste de résultats.
    Chaque entrée doit contenir : predicted_class, ground_truth, confidence,
    json_valid, latency_ms.
    """
    total = len(results)
    if total == 0:
        return {}

    correct = 0
    json_valid_count = 0
    latencies = []
    uncertain_count = 0
    hallucination_count = 0

    # Matrice de confusion (3 classes)
    matrix = {c: {c2: 0 for c2 in CLASSES} for c in CLASSES}

    for r in results:
        pred = r.get("predicted_class", "uncertain")
        truth = r.get("ground_truth", "uncertain")
        json_valid = r.get("json_valid", 0)
        latency = r.get("latency_ms", 0)
        hallucination = r.get("hallucination", 0)

        if json_valid:
            json_valid_count += 1
        if pred == truth:
            correct += 1
        if pred == "uncertain":
            uncertain_count += 1
        if hallucination:
            hallucination_count += 1

        latencies.append(latency)

        # Remplissage matrice (lignes = vérité terrain, colonnes = prédit)
        if truth in CLASSES and pred in CLASSES:
            matrix[truth][pred] += 1

    accuracy = round(correct / total, 4)
    json_valid_rate = round(json_valid_count / total, 4)
    uncertainty_rate = round(uncertain_count / total, 4)
    hallucination_rate = round(hallucination_count / total, 4)
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0

    # Macro-F1, sensibilité (rappel), spécificité par classe
    f1_scores = []
    sensitivity_scores = []
    specificity_scores = []

    for c in CLASSES:
        tp = matrix[c][c]
        fp = sum(matrix[other][c] for other in CLASSES if other != c)
        fn = sum(matrix[c][other] for other in CLASSES if other != c)
        tn = total - tp - fp - fn

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0  # sensibilité
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

        f1_scores.append(f1)
        sensitivity_scores.append(recall)
        specificity_scores.append(specificity)

    macro_f1 = round(sum(f1_scores) / len(f1_scores), 4)
    avg_sensitivity = round(sum(sensitivity_scores) / len(sensitivity_scores), 4)
    avg_specificity = round(sum(specificity_scores) / len(specificity_scores), 4)

    return {
        "total_cases": total,
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "sensitivity": avg_sensitivity,
        "specificity": avg_specificity,
        "json_valid_rate": json_valid_rate,
        "uncertainty_rate": uncertainty_rate,
        "hallucination_rate": hallucination_rate,
        "avg_latency_ms": avg_latency,
        "confusion_matrix": matrix,
    }


def print_metrics(metrics: dict):
    """Affiche les métriques de façon lisible dans le terminal."""
    print("\n" + "="*50)
    print("MÉTRIQUES D'ÉVALUATION")
    print("="*50)
    print(f"  Cas total          : {metrics.get('total_cases')}")
    print(f"  Accuracy           : {metrics.get('accuracy', 0):.1%}")
    print(f"  Macro-F1           : {metrics.get('macro_f1', 0):.1%}")
    print(f"  Sensibilité        : {metrics.get('sensitivity', 0):.1%}")
    print(f"  Spécificité        : {metrics.get('specificity', 0):.1%}")
    print(f"  JSON valide        : {metrics.get('json_valid_rate', 0):.1%}")
    print(f"  Taux incertitude   : {metrics.get('uncertainty_rate', 0):.1%}")
    print(f"  Taux hallucination : {metrics.get('hallucination_rate', 0):.1%}")
    print(f"  Latence moyenne    : {metrics.get('avg_latency_ms')} ms")
    print("="*50)


def save_metrics_csv(metrics: dict, out_path: Path):
    """Sauvegarde les métriques dans un CSV."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    flat = {k: v for k, v in metrics.items() if k != "confusion_matrix"}
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=flat.keys())
        writer.writeheader()
        writer.writerow(flat)
    print(f"Métriques sauvegardées : {out_path}")
