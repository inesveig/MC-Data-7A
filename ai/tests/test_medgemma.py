"""Tests de la logique d'analyse (parsing JSON, normalisation) en mode mock."""
import pytest
from PIL import Image

from medgemma import (
    MOCK,
    _extract_json,
    _severity_label,
    _to_analysis,
    analyze_image,
    model_name,
)


def test_mode_mock_actif_dans_les_tests():
    assert MOCK is True
    assert model_name() == "mock"


def test_extract_json_texte_pur():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_dans_barriere_markdown():
    text = "Voici le résultat:\n```json\n{\"severity\": 5}\n```\nfin"
    assert _extract_json(text) == {"severity": 5}


def test_extract_json_entoure_de_bruit():
    assert _extract_json('bla bla {"ok": true} merci') == {"ok": True}


def test_extract_json_sans_json_leve_valueerror():
    with pytest.raises(ValueError):
        _extract_json("aucun objet ici")


@pytest.mark.parametrize(
    "score,label",
    [(0, "none"), (2, "low"), (5, "moderate"), (8, "high"), (10, "critical")],
)
def test_severity_label(score, label):
    assert _severity_label(score) == label


def test_to_analysis_borne_la_severite():
    a = _to_analysis({"anomaly_present": True, "severity": 99})
    assert a.severity == 10


def test_to_analysis_cercle_invalide_ignore():
    a = _to_analysis(
        {"anomaly_present": True, "severity": 4, "circle": {"cx": 1.8, "cy": 0.5, "r": 0.1}}
    )
    # cx hors [0,1] -> Circle rejeté par le schéma -> circle=None (pas de crash)
    assert a.circle is None


def test_to_analysis_cercle_valide_conserve():
    a = _to_analysis(
        {"anomaly_present": True, "severity": 4, "circle": {"cx": 0.5, "cy": 0.5, "r": 0.1}}
    )
    assert a.circle is not None
    assert a.circle.cx == 0.5


def test_to_analysis_deduit_severity_label_si_absent():
    a = _to_analysis({"anomaly_present": True, "severity": 7})
    assert a.severity_label == "high"


def test_analyze_image_mock_renvoie_une_analyse():
    a = analyze_image(Image.new("RGB", (16, 16)))
    assert a.anomaly_present is True
    assert a.severity == 7
    assert "MOCK" in a.explanation
