"""
Smoke test : vérifie que la chaîne complète fonctionne sans modèle.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_structure_depot():
    """Vérifie que tous les dossiers obligatoires existent."""
    base = Path(__file__).parent.parent
    required = ["data", "prompts", "src", "api", "app", "eval", "tests", "docs"]
    for folder in required:
        assert (base / folder).is_dir(), f"Dossier manquant : {folder}"


def test_prompt_baseline_existe():
    base = Path(__file__).parent.parent
    p = base / "prompts" / "prompt_baseline.txt"
    assert p.exists(), "prompt_baseline.txt manquant"
    assert len(p.read_text()) > 100, "prompt_baseline.txt trop court"


def test_schema_json_valide():
    import json
    base = Path(__file__).parent.parent
    schema = json.loads((base / "prompts" / "schema_output.json").read_text())
    required_fields = [
        "image_quality", "predicted_class", "confidence",
        "visual_evidence", "justification", "limitations", "warning"
    ]
    for field in required_fields:
        assert field in schema, f"Champ manquant dans schema_output.json : {field}"


def test_gitignore_exclut_images():
    base = Path(__file__).parent.parent
    gitignore = (base / ".gitignore").read_text()
    assert "*.png" in gitignore or "sample_images" in gitignore, \
        ".gitignore ne protège pas les images"


def test_toy_inference():
    from src.inference import run_inference_toy
    result, latency = run_inference_toy()
    assert "predicted_class" in result
    assert "confidence" in result
    assert "warning" in result
    assert latency > 0


def test_guardrails_sur_sortie_toy():
    from src.inference import run_inference_toy
    from src.guardrails import validate_and_apply
    result, _ = run_inference_toy()
    validated = validate_and_apply(result)
    assert validated["predicted_class"] in {"normal", "suspected_opacity", "uncertain"}
    assert len(validated["warning"]) > 0


def test_evaluation_toy():
    """Lance l'évaluation jouet et vérifie les métriques de base."""
    from eval.run_evaluation import run_toy_mode
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        metrics = run_toy_mode(
            out_dir=Path(tmp) / "out",
            db_path=Path(tmp) / "test.sqlite",
        )
    assert "accuracy" in metrics
    assert "macro_f1" in metrics
    assert metrics["total_cases"] == 20
    assert metrics["json_valid_rate"] == 1.0
