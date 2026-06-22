"""
Inférence MedGemma 4B par prompting.
Aucun entraînement — on envoie l'image + le prompt, le modèle répond en JSON.
"""

import json
import time
import re
import random
from pathlib import Path
from PIL import Image

from src.preprocessing import preprocess_image, assess_image_quality

PROMPT_BASELINE = Path("prompts/prompt_baseline.txt")
PROMPT_AMELIORE = Path("prompts/prompt_ameliore.txt")
MODEL_ID = "google/medgemma-4b-it"

_model = None
_processor = None


def _load_model():
    """Charge MedGemma une seule fois en mémoire (lazy loading)."""
    global _model, _processor
    if _model is not None:
        return

    try:
        import torch
        from transformers import AutoProcessor, AutoModelForImageTextToText
    except ImportError:
        raise RuntimeError(
            "Dépendances manquantes. Lance : pip install transformers torch accelerate"
        )

    print(f"[Modèle] Chargement de {MODEL_ID}…")
    _processor = AutoProcessor.from_pretrained(MODEL_ID)
    _model = AutoModelForImageTextToText.from_pretrained(
        MODEL_ID,
        torch_dtype="auto",
        device_map="auto",
    )
    print("[Modèle] Prêt.")


def _load_prompt(prompt_path: Path) -> str:
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _extract_json(raw_text: str) -> dict:
    """
    Extrait le JSON de la réponse brute.
    MedGemma peut ajouter du texte avant/après — on isole le bloc JSON.
    """
    # Essai direct
    try:
        return json.loads(raw_text.strip())
    except json.JSONDecodeError:
        pass

    # Extraction entre la première { et la dernière }
    match = re.search(r"\{[\s\S]*\}", raw_text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Nettoyage balises markdown ```json ... ```
    cleaned = re.sub(r"```(?:json)?", "", raw_text).strip().rstrip("`")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        raise ValueError(
            f"Impossible d'extraire un JSON valide. Réponse brute : {raw_text[:300]}"
        )


def run_inference(
    image: Image.Image,
    prompt_path: Path = PROMPT_BASELINE,
    max_new_tokens: int = 512,
) -> tuple[dict, float]:
    """
    Envoie une image prétraitée à MedGemma avec le prompt donné.
    Retourne (résultat_dict, latence_ms).
    """
    _load_model()
    import torch

    # Prétraitement
    image = preprocess_image(image)
    quality_hint = assess_image_quality(image)
    prompt_text = _load_prompt(prompt_path)

    # Message multimodal
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt_text},
            ],
        }
    ]

    inputs = _processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(_model.device)

    start = time.time()
    with torch.inference_mode():
        output_ids = _model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )
    latency_ms = round((time.time() - start) * 1000, 2)

    # Décodage — tokens générés uniquement (pas le prompt)
    input_len = inputs["input_ids"].shape[-1]
    generated = output_ids[0][input_len:]
    raw_text = _processor.decode(generated, skip_special_tokens=True)

    result = _extract_json(raw_text)

    # Injecte la qualité image pré-calculée si le modèle ne l'a pas renseignée
    if not result.get("image_quality"):
        result["image_quality"] = quality_hint

    return result, latency_ms


def run_inference_toy(image_path: str = None) -> tuple[dict, float]:
    """
    Sortie jouet pour smoke test — aucun modèle requis.
    Simule les 3 classes avec des confidences variées.
    """
    time.sleep(0.05)
    confidence = round(random.uniform(0.38, 0.95), 2)
    predicted = (
        "uncertain"
        if confidence < 0.60
        else random.choice(["normal", "suspected_opacity"])
    )
    quality = random.choice(["good", "good", "limited"])

    return {
        "image_quality": quality,
        "predicted_class": predicted,
        "confidence": confidence,
        "visual_evidence": [
            "Sortie synthétique — smoke test uniquement",
            "Aucune image réelle analysée",
        ],
        "justification": (
            "Résultat généré automatiquement pour vérification de la chaîne complète. "
            "Aucune analyse médicale réelle effectuée."
        ),
        "limitations": [
            "Modèle non chargé",
            "Données synthétiques",
            "Résultat non représentatif",
        ],
        "warning": (
            "Prototype pédagogique uniquement. Résultat expérimental non validé cliniquement. "
            "Ne pas utiliser pour diagnostiquer, trier ou orienter un patient."
        ),
    }, round(random.uniform(60, 350), 2)
