"""
Tests du contrat de sortie JSON.
Vérifie que chaque champ respecte les valeurs autorisées.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.guardrails import validate_and_apply, ALLOWED_CLASSES, ALLOWED_QUALITY

VALID_SAMPLE = {
    "image_quality": "good",
    "predicted_class": "normal",
    "confidence": 0.85,
    "visual_evidence": ["Champs pulmonaires clairs"],
    "justification": "Pas d'opacité détectée.",
    "limitations": ["Prototype synthétique"],
    "warning": "Prototype pédagogique uniquement.",
}


def test_classes_autorisees():
    for cls in ALLOWED_CLASSES:
        data = VALID_SAMPLE.copy()
        data["predicted_class"] = cls
        data["confidence"] = 0.80 if cls != "uncertain" else 0.50
        result = validate_and_apply(data)
        assert result["predicted_class"] in ALLOWED_CLASSES


def test_qualite_image_autorisee():
    for q in ALLOWED_QUALITY:
        data = VALID_SAMPLE.copy()
        data["image_quality"] = q
        result = validate_and_apply(data)
        assert result["image_quality"] in ALLOWED_QUALITY


def test_confidence_arrondie():
    data = VALID_SAMPLE.copy()
    data["confidence"] = 0.123456789
    result = validate_and_apply(data)
    assert result["confidence"] == round(0.123456789, 4)


def test_classe_inconnue_devient_uncertain():
    data = VALID_SAMPLE.copy()
    data["predicted_class"] = "pneumonia"  # non autorisé
    result = validate_and_apply(data)
    assert result["predicted_class"] == "uncertain"


def test_qualite_inconnue_devient_limited():
    data = VALID_SAMPLE.copy()
    data["image_quality"] = "excellent"  # non autorisé
    result = validate_and_apply(data)
    assert result["image_quality"] == "limited"
