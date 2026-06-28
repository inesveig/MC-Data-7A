"""Micro-service IA : reçoit une radio, renvoie l'analyse MedGemma structurée."""
from __future__ import annotations

import base64
import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from dicom_utils import file_to_image, image_to_png_bytes  # noqa: E402
from medgemma import MOCK, analyze_image, model_name  # noqa: E402
from schemas import AnalyzeResponse  # noqa: E402

app = FastAPI(title="MedScan AI", version="0.1.0")

# Le backend Django (et le front en dev) appellent ce service.
origins = os.getenv("AI_ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "model": model_name(), "mock": MOCK}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    try:
        img = file_to_image(data, file.filename or "")
    except Exception as exc:  # décodage DICOM/image impossible
        raise HTTPException(status_code=422, detail=f"Image illisible : {exc}")

    analysis = analyze_image(img)
    png_b64 = base64.b64encode(image_to_png_bytes(img)).decode("ascii")

    return AnalyzeResponse(
        analysis=analysis,
        image_png_base64=png_b64,
        image_width=img.width,
        image_height=img.height,
        model=model_name(),
        mock=MOCK,
    )
