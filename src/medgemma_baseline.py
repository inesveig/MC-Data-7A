"""Connecteur MedGemma pour la baseline 'par prompting' (v1).

Conforme à l'appel d'offre : la baseline est un Vision-Language Model que l'on
*prompte* sur une radiographie thoracique frontale, et qui doit renvoyer le JSON
du contrat (`normal` / `suspected_opacity` / `uncertain`). On utilise le modèle
pré-entraîné Google MedGemma-4b (réf. R4 de l'appel d'offre).

Le modèle est chargé une seule fois puis mis en cache pour traiter les 30 images
sans le recharger. La sortie texte du modèle est parsée en JSON de manière
robuste, puis ramenée au schéma du projet ; en cas d'échec de parsing, on laisse
les garde-fous (`src/guardrails.py`) basculer la sortie en `uncertain`.

Position non clinique : prototype pédagogique, pas un dispositif médical.
"""

from __future__ import annotations

import json
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from .guardrails import ALLOWED_CLASSES, WARNING_TEXT
from .preprocessing import load_image

# Variante 'it' (instruction-tuned) : adaptée au prompting/chat, contrairement à
# la variante 'pt' (pré-entraînée brute) citée dans l'appel d'offre.
DEFAULT_MODEL_ID = "google/medgemma-4b-it"

_PROMPT_FILES = {
    "baseline": "prompts/baseline_prompt.txt",
    "improved": "prompts/improved_prompt.txt",
}

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=2)
def load_prompt(mode: str) -> str:
    rel = _PROMPT_FILES.get(mode, _PROMPT_FILES["baseline"])
    return (ROOT / rel).read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def _load_model(model_id: str):
    """Charge le modèle + processeur une seule fois (cache mémoire).

    Importé paresseusement pour que le reste du dépôt reste utilisable sans
    torch/transformers installés ou sans accès au modèle gated.
    """
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    if torch.cuda.is_available():
        device, dtype = "cuda", torch.bfloat16
    elif torch.backends.mps.is_available():
        device, dtype = "mps", torch.bfloat16
    else:
        device, dtype = "cpu", torch.float32

    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForImageTextToText.from_pretrained(
        model_id, torch_dtype=dtype
    ).to(device)
    model.eval()
    return model, processor, device


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extrait le premier objet JSON équilibré d'une sortie texte de VLM."""
    # Retire d'éventuelles clôtures markdown ```json ... ```
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates = []
    if fenced:
        candidates.append(fenced.group(1))
    # Balayage par équilibrage d'accolades pour le cas sans fence.
    depth, start = 0, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(text[start : i + 1])
                start = None
    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    return None


def _normalize(parsed: dict[str, Any] | None, raw_text: str) -> dict[str, Any]:
    """Ramène la sortie modèle au schéma du projet (sans la corriger silencieusement)."""
    if parsed is None:
        # Laisse les garde-fous trancher vers 'uncertain'.
        return {
            "image_quality": "limited",
            "visual_evidence": [],
            "justification": "Le modèle n'a pas renvoyé de JSON exploitable.",
            "limitations": ["sortie modèle non parsable", "JSON manquant"],
            "raw_model_output": raw_text[:500],
        }

    out: dict[str, Any] = dict(parsed)

    cls = str(out.get("predicted_class", "")).strip().lower()
    out["predicted_class"] = cls if cls in ALLOWED_CLASSES else cls  # validé en aval

    try:
        conf = float(out.get("confidence", 0.5))
    except (TypeError, ValueError):
        conf = 0.5
    out["confidence"] = round(max(0.0, min(1.0, conf)), 3)

    if isinstance(out.get("visual_evidence"), str):
        out["visual_evidence"] = [out["visual_evidence"]]
    out.setdefault("visual_evidence", [])
    out.setdefault("limitations", [])
    out.setdefault("justification", "")
    out.setdefault("image_quality", "good")
    return out


def medgemma_predict(
    image_path: str | Path,
    mode: str = "baseline",
    model_id: str = DEFAULT_MODEL_ID,
    max_new_tokens: int = 512,
) -> dict[str, Any]:
    """Inférence baseline 'par prompting' avec MedGemma.

    Renvoie un dict au schéma du projet. À combiner avec
    `apply_safety_guardrails` côté appelant (comme `toy_predict`).
    """
    import torch

    prompt = load_prompt(mode)
    image = load_image(image_path)  # PIL.Image RGB
    model, processor, device = _load_model(model_id)

    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "You are a cautious educational radiology assistant. "
                    "You are not a clinician. Reply with valid JSON only.",
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image", "image": image},
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

    start = time.perf_counter()
    with torch.inference_mode():
        generation = model.generate(
            **inputs, max_new_tokens=max_new_tokens, do_sample=False
        )
    latency_ms = int((time.perf_counter() - start) * 1000)

    prompt_len = inputs["input_ids"].shape[-1]
    raw_text = processor.decode(
        generation[0][prompt_len:], skip_special_tokens=True
    ).strip()

    pred = _normalize(_extract_json(raw_text), raw_text)
    pred["warning"] = WARNING_TEXT
    pred["model_name"] = model_id
    pred["prompt_version"] = f"{mode}_v1"
    pred["latency_ms"] = latency_ms
    return pred
