"""Conversion DICOM / images brutes -> PIL.Image affichable (RGB 8 bits)."""
from __future__ import annotations

import io

import numpy as np
from PIL import Image


def _to_uint8(arr: np.ndarray) -> np.ndarray:
    """Normalise un tableau en 8 bits sur la plage min/max effective."""
    arr = arr.astype(np.float32)
    lo, hi = float(arr.min()), float(arr.max())
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.uint8)
    arr = (arr - lo) / (hi - lo)
    return (arr * 255.0).clip(0, 255).astype(np.uint8)


def dicom_to_image(data: bytes) -> Image.Image:
    """Lit un DICOM (bytes) et renvoie une image RGB normalisée.

    Gère la VOI LUT (fenêtrage), l'inversion MONOCHROME1 et la mise à
    l'échelle 8 bits pour que l'image soit lisible par un humain / le modèle.
    """
    import pydicom

    # `apply_voi_lut` a migré vers `pydicom.pixels` en pydicom 3.x ; on garde un
    # repli vers l'ancien chemin pour rester compatible avec pydicom 2.x.
    try:
        from pydicom.pixels import apply_voi_lut
    except ImportError:  # pydicom < 3.0
        from pydicom.pixel_data_handlers.util import apply_voi_lut

    ds = pydicom.dcmread(io.BytesIO(data))
    pixels = ds.pixel_array

    # Applique le fenêtrage radiologique si présent
    try:
        pixels = apply_voi_lut(pixels, ds)
    except Exception:
        pass

    # MONOCHROME1 = échelle inversée (le blanc est le minimum)
    if str(getattr(ds, "PhotometricInterpretation", "")) == "MONOCHROME1":
        pixels = pixels.max() - pixels

    img8 = _to_uint8(pixels)
    return Image.fromarray(img8).convert("RGB")


def file_to_image(data: bytes, filename: str) -> Image.Image:
    """Route vers le bon décodeur selon l'extension du fichier."""
    name = (filename or "").lower()
    if name.endswith(".dcm") or name.endswith(".dicom"):
        return dicom_to_image(data)
    return Image.open(io.BytesIO(data)).convert("RGB")


def image_to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
