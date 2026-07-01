"""Tests des endpoints HTTP du service IA (via TestClient, mode mock)."""
import io

from fastapi.testclient import TestClient
from PIL import Image

from main import app

client = TestClient(app)


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(120, 120, 120)).save(buf, format="PNG")
    return buf.getvalue()


def test_health_signale_le_mode_mock():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["mock"] is True


def test_analyze_png_renvoie_analyse_structuree():
    resp = client.post(
        "/analyze", files={"file": ("radio.png", _png_bytes(), "image/png")}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(("analysis", "image_png_base64", "image_width", "image_height")) <= body.keys()
    assert body["analysis"]["severity"] == 7
    assert body["image_width"] == 32
    assert body["mock"] is True


def test_analyze_fichier_vide_renvoie_400():
    resp = client.post("/analyze", files={"file": ("vide.png", b"", "image/png")})
    assert resp.status_code == 400


def test_analyze_image_illisible_renvoie_422():
    resp = client.post(
        "/analyze", files={"file": ("radio.png", b"pas une image", "image/png")}
    )
    assert resp.status_code == 422
