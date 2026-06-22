"""
Script d'évaluation principal.
Usage :
  python eval/run_evaluation.py --mode toy
  python eval/run_evaluation.py --mode full --data-dir data/sample_images
"""

import argparse
import csv
import json
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.guardrails import validate_and_apply
from src.metrics import compute_metrics, print_metrics, save_metrics_csv
from src.database import log_prediction, init_db


def load_labels(label_file: Path) -> dict:
    """
    Charge les labels vérité terrain depuis un CSV.
    Format attendu : image_name, ground_truth
    """
    labels = {}
    if not label_file.exists():
        return labels
    with open(label_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            labels[row["image_name"]] = row["ground_truth"]
    return labels


def run_toy_mode(out_dir: Path, db_path: Path):
    """
    Mode jouet : génère 20 cas synthétiques sans GPU ni modèle.
    Utilisé pour vérifier que la chaîne complète fonctionne.
    """
    from src.inference import run_inference_toy

    print("\n[MODE TOY] Évaluation sur 20 cas synthétiques")
    init_db(db_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Labels synthétiques (pour simuler la vérité terrain)
    toy_labels = (
        ["normal"] * 7
        + ["suspected_opacity"] * 7
        + ["uncertain"] * 6
    )

    results = []
    output_rows = []

    for i, ground_truth in enumerate(toy_labels):
        image_name = f"CXR_SYN_{i+1:03d}_{ground_truth}.png"
        raw_result, latency_ms = run_inference_toy(image_name)

        try:
            result = validate_and_apply(raw_result)
            json_valid = 1
        except ValueError as e:
            print(f"  ⚠ Garde-fou rejeté pour {image_name} : {e}")
            result = raw_result
            json_valid = 0

        log_prediction(
            image_name=image_name,
            prompt_version="toy_baseline_v1",
            model_name="toy_model",
            result=result,
            latency_ms=latency_ms,
            db_path=db_path,
        )

        record = {
            "image_name": image_name,
            "ground_truth": ground_truth,
            "predicted_class": result.get("predicted_class"),
            "confidence": result.get("confidence"),
            "json_valid": json_valid,
            "latency_ms": latency_ms,
            "hallucination": 0,
        }
        results.append(record)
        output_rows.append({**record, "output_json": json.dumps(result, ensure_ascii=False)})

        status = "✓" if result.get("predicted_class") == ground_truth else "✗"
        print(f"  {status} {image_name} → prédit: {result.get('predicted_class')} | conf: {result.get('confidence')} | {latency_ms}ms")

    # Sauvegarde CSV des résultats bruts
    results_path = out_dir / "results_toy.csv"
    with open(results_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_rows[0].keys())
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"\nRésultats sauvegardés : {results_path}")

    # Calcul et affichage des métriques
    metrics = compute_metrics(results)
    print_metrics(metrics)

    metrics_path = out_dir / "metrics_toy.csv"
    save_metrics_csv(metrics, metrics_path)

    return metrics


def run_full_mode(data_dir: Path, out_dir: Path, db_path: Path, prompt_path: Path):
    """
    Mode complet : inférence réelle sur les images du dossier data_dir.
    Nécessite MedGemma chargé et un fichier labels.csv dans data_dir.
    """
    from src.inference import run_inference
    from PIL import Image

    print(f"\n[MODE FULL] Évaluation sur : {data_dir}")
    init_db(db_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    image_files = sorted(list(data_dir.glob("*.png")) + list(data_dir.glob("*.jpg")))
    if not image_files:
        print(f"Aucune image trouvée dans {data_dir}")
        return {}

    labels = load_labels(data_dir / "labels.csv")
    results = []
    output_rows = []

    for img_path in image_files:
        image = Image.open(img_path).convert("RGB")
        raw_result, latency_ms = run_inference(image, prompt_path=prompt_path)

        try:
            result = validate_and_apply(raw_result)
            json_valid = 1
        except ValueError as e:
            print(f"  ⚠ Garde-fou rejeté pour {img_path.name} : {e}")
            json_valid = 0
            result = {"predicted_class": "uncertain", "confidence": 0.0,
                      "warning": "JSON invalide — garde-fou activé"}

        ground_truth = labels.get(img_path.name, "unknown")

        log_prediction(
            image_name=img_path.name,
            prompt_version=prompt_path.stem,
            model_name="medgemma-4b",
            result=result,
            latency_ms=latency_ms,
            db_path=db_path,
        )

        record = {
            "image_name": img_path.name,
            "ground_truth": ground_truth,
            "predicted_class": result.get("predicted_class"),
            "confidence": result.get("confidence"),
            "json_valid": json_valid,
            "latency_ms": latency_ms,
            "hallucination": 0,
        }
        results.append(record)
        output_rows.append({**record, "output_json": json.dumps(result, ensure_ascii=False)})

        status = "✓" if result.get("predicted_class") == ground_truth else "✗"
        print(f"  {status} {img_path.name} → prédit: {result.get('predicted_class')} | conf: {result.get('confidence'):.2f} | {latency_ms}ms")

    results_path = out_dir / "results_full.csv"
    with open(results_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_rows[0].keys())
        writer.writeheader()
        writer.writerows(output_rows)

    metrics = compute_metrics([r for r in results if r["ground_truth"] != "unknown"])
    print_metrics(metrics)
    save_metrics_csv(metrics, out_dir / "metrics_full.csv")

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Évaluation de l'assistant radiologue")
    parser.add_argument("--mode", choices=["toy", "full"], default="toy")
    parser.add_argument("--data-dir", type=Path, default=Path("data/sample_images"))
    parser.add_argument("--out-dir", type=Path, default=Path("eval/outputs"))
    parser.add_argument("--db-path", type=Path, default=Path("data/evidence.sqlite"))
    parser.add_argument("--prompt", type=Path, default=Path("prompts/prompt_baseline.txt"))
    args = parser.parse_args()

    if args.mode == "toy":
        run_toy_mode(out_dir=args.out_dir, db_path=args.db_path)
    else:
        run_full_mode(
            data_dir=args.data_dir,
            out_dir=args.out_dir,
            db_path=args.db_path,
            prompt_path=args.prompt,
        )
