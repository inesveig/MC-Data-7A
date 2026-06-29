import random

UNCERTAINTY_THRESHOLD = 0.65

def _predict_raw(image_path: str):
    """
    Call le model IA
    """

    # pour les tests
    diagnosis = random.choice(["Sain", "Malade"])
    confidence = round(random.uniform(0.45, 0.99), 2)
    return diagnosis, confidence


def predict_diagnosis(image_path: str):

    diagnosis, confidence = _predict_raw(image_path)

    if confidence < UNCERTAINTY_THRESHOLD:
        return "Incertain", confidence

    return diagnosis, confidence


def generate_heatmap(image_path: str, model_obj=None):
    """
    call la heatmap
    """
    return None