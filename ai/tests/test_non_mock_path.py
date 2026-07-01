"""Teste le *chemin non-mock* de `analyze_image` sans télécharger les poids.

On injecte un faux modèle + faux processeur à la place de MedGemma : tout le
câblage réel est exercé (construction des messages system/user + image, appel à
`generate`, décodage, extraction JSON, normalisation en `Analysis`, repli si la
sortie n'est pas du JSON). Seuls les 8 Go de poids sont remplacés.

Le vrai modèle est testé séparément (voir README / script de fumée réel).
"""
import pytest
from PIL import Image

torch = pytest.importorskip("torch")  # le chemin non-mock importe torch

import medgemma


class _FakeBatch(dict):
    """Imite la sortie de `processor.apply_chat_template(...)` : un mapping
    (dépliable via **inputs) qui répond à `.to(device)`."""

    def to(self, device):
        return self


class _FakeProcessor:
    def __init__(self, decoded_text):
        self._decoded = decoded_text
        self.seen_messages = None

    def apply_chat_template(self, messages, **kwargs):
        self.seen_messages = messages
        batch = _FakeBatch()
        batch["input_ids"] = torch.zeros((1, 4), dtype=torch.long)
        return batch

    def decode(self, sequence, skip_special_tokens=True):
        return self._decoded


class _FakeModel:
    def __init__(self):
        self.generate_called_with = None

    def generate(self, **kwargs):
        self.generate_called_with = kwargs
        return torch.zeros((1, 12), dtype=torch.long)


@pytest.fixture
def force_real_path(monkeypatch):
    """Bascule `analyze_image` sur la branche non-mock."""
    monkeypatch.setattr(medgemma, "MOCK", False)

    def _install(decoded_text):
        model = _FakeModel()
        processor = _FakeProcessor(decoded_text)
        monkeypatch.setattr(medgemma, "_load_model", lambda: (model, processor, "cpu"))
        return model, processor

    return _install


def test_non_mock_parse_le_json_du_modele(force_real_path):
    model, processor = force_real_path(
        '{"anomaly_present": true, "findings": ["Opacité"], '
        '"region": "lobe supérieur gauche", "severity": 6, '
        '"explanation": "test", "recommendation": "avis"}'
    )
    analysis = medgemma.analyze_image(Image.new("RGB", (16, 16)))

    assert analysis.anomaly_present is True
    assert analysis.severity == 6
    assert analysis.severity_label == "moderate"  # déduit de la gravité
    assert analysis.region == "lobe supérieur gauche"
    # generate a bien été appelé avec les tokens du processeur.
    assert model.generate_called_with is not None
    assert "max_new_tokens" in model.generate_called_with


def test_non_mock_transmet_bien_image_et_system_prompt(force_real_path):
    _, processor = force_real_path('{"anomaly_present": false, "severity": 0}')
    medgemma.analyze_image(Image.new("RGB", (16, 16)))

    msgs = processor.seen_messages
    roles = [m["role"] for m in msgs]
    assert roles == ["system", "user"]
    # Le message user contient bien un bloc image + un bloc texte.
    user_types = [block["type"] for block in msgs[1]["content"]]
    assert "image" in user_types and "text" in user_types


def test_non_mock_findings_en_string_devient_liste_dun_element(force_real_path):
    # Observé en usage réel : MedGemma renvoie parfois `findings` comme une
    # phrase brute au lieu d'une liste. Sans garde-fou, itérer la str la
    # découpe caractère par caractère (voir ai/medgemma.py::_to_analysis).
    force_real_path(
        '{"anomaly_present": true, "findings": "Opacité du lobe droit.", '
        '"severity": 3}'
    )
    analysis = medgemma.analyze_image(Image.new("RGB", (16, 16)))
    assert analysis.findings == ["Opacité du lobe droit."]


def test_non_mock_json_dans_fence_markdown(force_real_path):
    force_real_path('Voici:\n```json\n{"anomaly_present": true, "severity": 9}\n```')
    analysis = medgemma.analyze_image(Image.new("RGB", (16, 16)))
    assert analysis.severity == 9
    assert analysis.severity_label == "critical"


def test_non_mock_sortie_non_json_bascule_sur_repli(force_real_path):
    force_real_path("Le modèle a divagué sans produire de JSON.")
    analysis = medgemma.analyze_image(Image.new("RGB", (16, 16)))
    # Repli sûr : pas d'anomalie inventée, message de relance.
    assert analysis.anomaly_present is False
    assert analysis.severity == 0
    assert "non structurée" in analysis.recommendation.lower()
