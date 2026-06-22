"""
Garde-fous appliqués sur la sortie JSON de MedGemma.
Règle principale : confidence < 0.60 → predicted_class = "uncertain"
"""

import json
from typing import Union

REQUIRED_FIELDS = [
    "image_quality",
    "predicted_class",
    "confidence",
    "visual_evidence",
    "justification",
    "limitations",
    "warning",
]

ALLOWED_CLASSES = {"normal", "suspected_opacity", "uncertain"}
ALLOWED_QUALITY = {"good", "limited", "poor"}
CONFIDENCE_THRESHOLD = 0.60
WARNING_TEXT = (
    "Prototype pédagogique uniquement. Résultat expérimental non validé cliniquement. "
    "Ne pas utiliser pour diagnostiquer, trier ou orienter un patient."
)


def validate_and_apply(raw_output: Union[str, dict]) -> dict:
    """
    Valide et corrige la sortie du modèle.
    Retourne le JSON corrigé ou lève une ValueError si le format est irrécupérable.
    """
    if isinstance(raw_output, str):
        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON invalide : {e}")
    else:
        data = raw_output

    # Vérification des champs obligatoires
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise ValueError(f"Champs manquants : {missing}")

    # Règle garde-fou : confiance faible → uncertain
    confidence = float(data["confidence"])
    if confidence < CONFIDENCE_THRESHOLD:
        data["predicted_class"] = "uncertain"

    # Validation de la classe prédite
    if data["predicted_class"] not in ALLOWED_CLASSES:
        data["predicted_class"] = "uncertain"

    # Validation de la qualité image
    if data["image_quality"] not in ALLOWED_QUALITY:
        data["image_quality"] = "limited"

    # Warning toujours présent
    if not data.get("warning"):
        data["warning"] = WARNING_TEXT

    # visual_evidence et limitations doivent être des listes
    if isinstance(data["visual_evidence"], str):
        data["visual_evidence"] = [data["visual_evidence"]]
    if isinstance(data["limitations"], str):
        data["limitations"] = [data["limitations"]]

    data["confidence"] = round(confidence, 4)

    return data
