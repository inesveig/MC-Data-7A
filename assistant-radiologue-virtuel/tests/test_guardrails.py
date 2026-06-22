"""
Tests du module garde-fous.
"""
import pytest
import sys
sys.path.insert(0, ".")
from src.guardrails import validate_and_apply

VALID_BASE = {
    "image_quality": "good",
    "predicted_class": "normal",
    "confidence": 0.80,
    "visual_evidence": ["Champs clairs"],
    "justification": "Pas d'opacité détectée.",
    "limitations": ["Dataset synthétique"],
    "warning": "Prototype pédagogique uniquement.",
}

def test_valid_output():
    result = validate_and_apply(VALID_BASE.copy())
    assert result["predicted_class"] == "normal"
    assert result["confidence"] == 0.80

def test_low_confidence_becomes_uncertain():
    data = VALID_BASE.copy()
    data["confidence"] = 0.45
    result = validate_and_apply(data)
    assert result["predicted_class"] == "uncertain"

def test_warning_always_present():
    data = VALID_BASE.copy()
    data["warning"] = ""
    result = validate_and_apply(data)
    assert len(result["warning"]) > 0

def test_missing_field_raises():
    data = VALID_BASE.copy()
    del data["confidence"]
    with pytest.raises(ValueError):
        validate_and_apply(data)

def test_string_evidence_converted_to_list():
    data = VALID_BASE.copy()
    data["visual_evidence"] = "Opacité basale droite"
    result = validate_and_apply(data)
    assert isinstance(result["visual_evidence"], list)
