"""Tests de la conversion DICOM/image -> PIL utilisée avant l'inférence."""
import io

import numpy as np
import pytest
from PIL import Image

from dicom_utils import (
    _to_uint8,
    dicom_to_image,
    file_to_image,
    image_to_png_bytes,
)


def test_to_uint8_image_constante_donne_zeros():
    arr = np.full((4, 4), 42.0)
    out = _to_uint8(arr)
    assert out.dtype == np.uint8
    assert out.max() == 0  # hi <= lo -> tout à 0, pas de division par zéro


def test_to_uint8_gradient_couvre_toute_la_plage():
    arr = np.arange(256, dtype=np.float32).reshape(16, 16)
    out = _to_uint8(arr)
    assert out.min() == 0
    assert out.max() == 255


def test_file_to_image_png_donne_rgb():
    buf = io.BytesIO()
    Image.new("L", (10, 12), color=128).save(buf, format="PNG")
    img = file_to_image(buf.getvalue(), "radio.png")
    assert img.mode == "RGB"
    assert img.size == (10, 12)


def test_image_to_png_bytes_est_relisible():
    img = Image.new("RGB", (8, 8), color=(10, 20, 30))
    data = image_to_png_bytes(img)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"  # signature PNG
    assert Image.open(io.BytesIO(data)).size == (8, 8)


def _synthetic_dicom_bytes(photometric="MONOCHROME2"):
    pydicom = pytest.importorskip("pydicom")
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid

    ds = Dataset()
    ds.file_meta = FileMetaDataset()
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta.MediaStorageSOPClassUID = generate_uid()
    ds.file_meta.MediaStorageSOPInstanceUID = generate_uid()
    ds.Rows, ds.Columns = 8, 8
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = photometric
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    arr = np.arange(64, dtype=np.uint16).reshape(8, 8)
    ds.PixelData = arr.tobytes()

    buf = io.BytesIO()
    # Le Transfer Syntax UID (ExplicitVRLittleEndian) suffit à définir l'encodage.
    ds.save_as(buf, enforce_file_format=True)
    return buf.getvalue()


def test_dicom_to_image_monochrome2():
    img = dicom_to_image(_synthetic_dicom_bytes("MONOCHROME2"))
    assert img.mode == "RGB"
    assert img.size == (8, 8)


def test_dicom_monochrome1_est_inverse():
    """MONOCHROME1 = échelle inversée : le pixel de valeur brute max doit
    devenir sombre après conversion (et inversement)."""
    m2 = np.asarray(dicom_to_image(_synthetic_dicom_bytes("MONOCHROME2")))
    m1 = np.asarray(dicom_to_image(_synthetic_dicom_bytes("MONOCHROME1")))
    # Le coin le plus lumineux de l'un doit être le plus sombre de l'autre.
    assert m2[-1, -1].mean() > m2[0, 0].mean()
    assert m1[-1, -1].mean() < m1[0, 0].mean()


def test_file_to_image_png_illisible_leve_une_exception():
    with pytest.raises(Exception):
        file_to_image(b"pas une image", "radio.png")
