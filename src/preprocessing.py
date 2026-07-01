from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}
DICOM_SUFFIXES = {".dcm", ".dicom"}


def _dicom_to_image(path: Path) -> Image.Image:
    """Décode un DICOM (ex: RSNA) en image RGB 8 bits.

    Gère la VOI LUT (fenêtrage radiologique) et l'inversion MONOCHROME1,
    sans quoi les radios RSNA ressortiraient en négatif / mal contrastées.
    """
    import pydicom

    try:
        from pydicom.pixels import apply_voi_lut
    except ImportError:  # pydicom < 3.0
        from pydicom.pixel_data_handlers.util import apply_voi_lut

    ds = pydicom.dcmread(str(path))
    pixels = ds.pixel_array

    try:
        pixels = apply_voi_lut(pixels, ds)
    except Exception:
        pass

    if str(getattr(ds, "PhotometricInterpretation", "")) == "MONOCHROME1":
        pixels = pixels.max() - pixels

    arr = pixels.astype(np.float32)
    lo, hi = float(arr.min()), float(arr.max())
    if hi <= lo:
        img8 = np.zeros_like(arr, dtype=np.uint8)
    else:
        img8 = ((arr - lo) / (hi - lo) * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(img8).convert("RGB")


def load_image(path: str | Path, size: tuple[int, int] = (512, 512)) -> Image.Image:
    """Load an image safely for the educational prototype.

    Supporte les images bitmap classiques (PNG/JPG/BMP) ainsi que le DICOM
    (ex: RSNA Pneumonia Detection Challenge), avec fenêtrage VOI LUT.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in DICOM_SUFFIXES:
        img = _dicom_to_image(path)
    elif suffix in ALLOWED_SUFFIXES:
        img = Image.open(path).convert("RGB")
    else:
        raise ValueError(f"Unsupported image format: {path.suffix}")
    return img.resize(size)


def basic_quality_flag(path: str | Path) -> str:
    """Toy quality flag based on filename metadata.

    Replace this with real image-quality checks in a serious implementation.
    """
    name = Path(path).name.lower()
    if "uncertain" in name or "limited" in name:
        return "limited"
    return "good"
