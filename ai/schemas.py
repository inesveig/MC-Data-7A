"""Schémas Pydantic de la réponse d'analyse."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Circle(BaseModel):
    """Localisation approximative de l'anomalie, en fractions [0,1] de l'image."""
    cx: float = Field(..., ge=0, le=1, description="Centre X (fraction de la largeur)")
    cy: float = Field(..., ge=0, le=1, description="Centre Y (fraction de la hauteur)")
    r: float = Field(..., ge=0, le=1, description="Rayon (fraction de la largeur)")


class Analysis(BaseModel):
    anomaly_present: bool
    findings: List[str] = []
    region: Optional[str] = Field(None, description="Localisation anatomique en clair")
    circle: Optional[Circle] = None
    severity: int = Field(0, ge=0, le=10, description="Gravité de 0 (RAS) à 10 (critique)")
    severity_label: str = "none"  # none | low | moderate | high | critical
    explanation: str = ""
    recommendation: str = ""


class AnalyzeResponse(BaseModel):
    analysis: Analysis
    # Image convertie (PNG base64) que le front affiche et sur laquelle il
    # dessine le cercle.
    image_png_base64: str
    image_width: int
    image_height: int
    model: str
    mock: bool = False
