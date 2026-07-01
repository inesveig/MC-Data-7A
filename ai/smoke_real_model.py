"""Fumée du VRAI MedGemma (non-mock) sur une image d'exemple.

Usage : AI_MOCK=0 python smoke_real_model.py [chemin_image]
Charge les poids en cache (~8 Go), lance une inférence, imprime l'analyse.
"""
import os
import sys
import time

os.environ["AI_MOCK"] = "0"  # on veut explicitement le vrai modèle

from dicom_utils import file_to_image  # noqa: E402
from medgemma import analyze_image, model_name  # noqa: E402

img_path = sys.argv[1] if len(sys.argv) > 1 else (
    "../data/sample_images/CXR_SYN_002_suspected_opacity.png"
)

print(f"Modèle : {model_name()}")
print(f"Image  : {img_path}")

with open(img_path, "rb") as fh:
    img = file_to_image(fh.read(), img_path)
print(f"Image chargée : {img.size} {img.mode}")

t0 = time.perf_counter()
analysis = analyze_image(img)
dt = time.perf_counter() - t0

print(f"\n--- Inférence en {dt:.1f}s ---")
print(analysis.model_dump_json(indent=2))
