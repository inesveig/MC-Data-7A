"""Chargement de MedGemma et analyse d'une radio en sortie structurée.

MedGemma est un modèle vision-langage : il décrit l'image et donne une zone
APPROXIMATIVE + une gravité. Ce n'est pas un dispositif de diagnostic certifié.
"""
from __future__ import annotations

import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

from PIL import Image

from schemas import Analysis, Circle

# Rend le code MedGemma déjà écrit par l'équipe (src/) importable quand on lance
# le service depuis ai/ : on réutilise son chargement de modèle au lieu de le
# dupliquer.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MODEL_ID = os.getenv("MEDGEMMA_MODEL", "google/medgemma-4b-it")
MOCK = os.getenv("AI_MOCK", "0") == "1"

# On force le modèle à répondre en JSON pur, exploitable directement par le front.
SYSTEM_PROMPT = (
    "Tu es un radiologue expert spécialisé en imagerie thoracique. "
    "Tu analyses une radiographie pulmonaire. Réponds UNIQUEMENT avec un objet "
    "JSON valide, sans texte autour, sans balises markdown. Schéma exact :\n"
    "{\n"
    '  "anomaly_present": bool,\n'
    '  "findings": [string],            // anomalies observées (vide si normal)\n'
    '  "region": string|null,           // localisation anatomique en clair, ex: "lobe inférieur droit"\n'
    '  "circle": {"cx": float, "cy": float, "r": float}|null,  // centre+rayon de l\'anomalie principale,\n'
    "                                   // en FRACTIONS de l'image entre 0 et 1 (0,0 = haut-gauche). null si normal.\n"
    '  "severity": int,                 // 0 (rien) à 10 (critique vital)\n'
    '  "severity_label": string,        // "none" | "low" | "moderate" | "high" | "critical"\n'
    '  "explanation": string,           // pourquoi c\'est grave ou rassurant, en français\n'
    '  "recommendation": string         // conduite à tenir suggérée, en français\n'
    "}\n"
    "Sois prudent : en cas de doute, signale-le dans explanation."
)

USER_PROMPT = (
    "Analyse cette radiographie thoracique. Détecte toute opacité, "
    "consolidation, épanchement ou autre anomalie. Donne la localisation et "
    "la gravité. Réponds en JSON selon le schéma imposé."
)


def _severity_label(score: int) -> str:
    if score <= 0:
        return "none"
    if score <= 3:
        return "low"
    if score <= 6:
        return "moderate"
    if score <= 8:
        return "high"
    return "critical"


def _extract_json(text: str) -> dict:
    """Extrait le premier objet JSON d'une sortie de modèle, tolérant au bruit."""
    text = text.strip()
    # Retire d'éventuelles barrières markdown ```json ... ```
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Pas de JSON trouvé dans la sortie du modèle: {text[:200]!r}")
    return json.loads(text[start : end + 1])


def _to_analysis(raw: dict) -> Analysis:
    circle = None
    c = raw.get("circle")
    if isinstance(c, dict) and all(k in c for k in ("cx", "cy", "r")):
        try:
            circle = Circle(cx=float(c["cx"]), cy=float(c["cy"]), r=float(c["r"]))
        except Exception:
            circle = None

    severity = int(raw.get("severity", 0) or 0)
    severity = max(0, min(10, severity))
    label = raw.get("severity_label") or _severity_label(severity)

    findings = raw.get("findings") or []
    if isinstance(findings, str):
        # Le modèle répond parfois par une phrase brute au lieu d'une liste :
        # sans ce garde-fou, itérer sur une str la découpe caractère par caractère.
        findings = [findings]

    return Analysis(
        anomaly_present=bool(raw.get("anomaly_present", circle is not None)),
        findings=[str(f) for f in findings],
        region=raw.get("region"),
        circle=circle,
        severity=severity,
        severity_label=str(label),
        explanation=str(raw.get("explanation", "")),
        recommendation=str(raw.get("recommendation", "")),
    )


# --------------------------------------------------------------------------- #
# Mode MOCK : permet de développer front + back sans télécharger le modèle.
# --------------------------------------------------------------------------- #
def _mock_analysis() -> Analysis:
    return _to_analysis(
        {
            "anomaly_present": True,
            "findings": ["Opacité alvéolaire suspecte", "Bronchogramme aérique"],
            "region": "lobe inférieur droit",
            "circle": {"cx": 0.66, "cy": 0.62, "r": 0.12},
            "severity": 7,
            "severity_label": "high",
            "explanation": (
                "[MOCK] Opacité compatible avec une pneumonie du lobe inférieur "
                "droit. Étendue et densité élevées : risque d'insuffisance "
                "respiratoire si non traitée."
            ),
            "recommendation": "[MOCK] Corréler à la clinique, envisager antibiothérapie et avis médical rapide.",
        }
    )


# --------------------------------------------------------------------------- #
# Chargement paresseux du modèle (une seule fois).
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _load_model():
    """Réutilise le loader de `src/medgemma_baseline.py` (équipe/prof).

    Le modèle MedGemma n'est ainsi chargé qu'une seule fois en mémoire et
    partagé entre la classification baseline et l'analyse de localisation.
    """
    from src.medgemma_baseline import _load_model as _shared_load_model

    return _shared_load_model(MODEL_ID)


def model_name() -> str:
    return "mock" if MOCK else MODEL_ID


def analyze_image(img: Image.Image) -> Analysis:
    if MOCK:
        return _mock_analysis()

    import torch

    model, processor, device = _load_model()
    messages = [
        {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
        {
            "role": "user",
            "content": [
                {"type": "image", "image": img},
                {"type": "text", "text": USER_PROMPT},
            ],
        },
    ]
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(device)

    input_len = inputs["input_ids"].shape[-1]
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=700, do_sample=False)
    text = processor.decode(out[0][input_len:], skip_special_tokens=True)

    try:
        return _to_analysis(_extract_json(text))
    except Exception:
        # Repli : on n'a pas pu parser de JSON, on renvoie la sortie brute.
        return Analysis(
            anomaly_present=False,
            findings=[],
            region=None,
            circle=None,
            severity=0,
            severity_label="none",
            explanation=text.strip()[:1000],
            recommendation="Sortie non structurée du modèle ; relancer l'analyse.",
        )
