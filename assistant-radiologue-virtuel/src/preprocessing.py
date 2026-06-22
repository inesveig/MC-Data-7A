"""
Prétraitement des images avant envoi à MedGemma.
Normalisation, redimensionnement, vérification du format.
"""

from PIL import Image, ImageOps
from pathlib import Path

TARGET_SIZE = (512, 512)
ALLOWED_FORMATS = {".png", ".jpg", ".jpeg"}


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Prépare une radiographie pour MedGemma :
    - Conversion en RGB (les DICOM ou PNG en niveaux de gris doivent être convertis)
    - Redimensionnement à 512x512 en conservant les proportions
    - Normalisation de l'histogramme pour améliorer le contraste
    """
    # Conversion RGB (MedGemma attend du RGB)
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Amélioration du contraste (utile pour les radios sous-exposées)
    image = ImageOps.autocontrast(image, cutoff=1)

    # Redimensionnement avec ratio conservé, puis padding pour atteindre 512x512
    image.thumbnail(TARGET_SIZE, Image.LANCZOS)
    padded = Image.new("RGB", TARGET_SIZE, (0, 0, 0))
    offset = (
        (TARGET_SIZE[0] - image.width) // 2,
        (TARGET_SIZE[1] - image.height) // 2,
    )
    padded.paste(image, offset)

    return padded


def load_and_preprocess(image_path: Path) -> Image.Image:
    """
    Charge une image depuis un chemin fichier et la prétraite.
    """
    if image_path.suffix.lower() not in ALLOWED_FORMATS:
        raise ValueError(f"Format non supporté : {image_path.suffix}. Formats acceptés : {ALLOWED_FORMATS}")

    image = Image.open(image_path)
    return preprocess_image(image)


def assess_image_quality(image: Image.Image) -> str:
    """
    Évalue grossièrement la qualité de l'image avant analyse.
    Retourne 'good', 'limited' ou 'poor'.
    """
    import numpy as np

    img_array = np.array(image.convert("L"))  # niveaux de gris

    # Contraste : écart-type des pixels
    std = img_array.std()
    # Luminosité moyenne
    mean = img_array.mean()

    if std < 20 or mean < 10 or mean > 245:
        return "poor"
    elif std < 40 or mean < 30 or mean > 220:
        return "limited"
    else:
        return "good"
