"""Traduction de la sortie riche du service IA vers les 3 classes métier.

MedGemma renvoie une anomalie + une gravité 0-10 (pas une probabilité calibrée).
La plateforme, elle, raisonne en 3 classes pédagogiques alignées sur le contrat
du projet (`normal` / `suspected_opacity` / `uncertain`), exposées côté UI en
français : Sain / Malade / Incertain.

Règle de dérivation (heuristique assumée, documentée pour la soutenance) :
- pas d'anomalie (gravité 0)        -> Sain      (normal)
- anomalie de faible gravité (1-3)  -> Incertain (garde-fou : doute, à vérifier)
- anomalie de gravité >= 4          -> Malade    (suspected_opacity)

La « confiance » affichée est dérivée de la gravité, faute de probabilité
calibrée fournie par le VLM.
"""
from __future__ import annotations

DIAG_SAIN = "Sain"
DIAG_MALADE = "Malade"
DIAG_INCERTAIN = "Incertain"

DIAGNOSES = (DIAG_SAIN, DIAG_MALADE, DIAG_INCERTAIN)


def clamp_severity(value) -> int:
    """Ramène une gravité potentiellement invalide dans l'entier [0, 10].

    Le service IA n'est pas garanti de renvoyer un entier propre (le VLM peut
    renvoyer une chaîne, un flottant ou rien). On sécurise donc la conversion
    au lieu de laisser un `int()` brut faire planter la vue.
    """
    try:
        severity = int(float(value)) if value not in (None, "") else 0
    except (TypeError, ValueError):
        severity = 0
    return max(0, min(10, severity))


def derive_diagnosis(analysis: dict) -> tuple[str, float]:
    """(diagnostic 3-classes, confiance 0-1) à partir de l'analyse IA brute."""
    anomaly = bool(analysis.get("anomaly_present"))
    severity = clamp_severity(analysis.get("severity"))

    if not anomaly or severity == 0:
        # Confiance = à quel point on est sûr que c'est sain.
        return DIAG_SAIN, round(1 - severity / 10, 2)
    if severity <= 3:
        return DIAG_INCERTAIN, round(severity / 10, 2)
    return DIAG_MALADE, round(severity / 10, 2)


def doctor_to_category(doctor_diagnosis: str | None) -> str | None:
    """Ramène l'avis médecin libre à une catégorie binaire Sain/Malade."""
    if not doctor_diagnosis:
        return None
    return DIAG_SAIN if doctor_diagnosis == DIAG_SAIN else DIAG_MALADE


def concordance(ia_diagnosis: str, doctor_diagnosis: str | None) -> tuple[str | None, int | None]:
    """Compare le diagnostic IA à l'avis médecin -> (statut, % similitude)."""
    category = doctor_to_category(doctor_diagnosis)
    if category is None:
        return None, None
    if ia_diagnosis == DIAG_INCERTAIN:
        return "Non comparable (IA incertaine)", 50
    if ia_diagnosis == category:
        return "Concordant", 100
    return "Discordant", 0
