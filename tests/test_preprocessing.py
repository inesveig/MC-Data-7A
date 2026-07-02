"""Tests du chargement d'image (PNG/JPG classiques + DICOM, ex: RSNA)."""
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from src.preprocessing import load_image


def test_load_image_png_donne_rgb_redimensionne():
    img = load_image(
        Path(__file__).resolve().parents[1] / "data" / "sample_images" / "CXR_SYN_001_normal.png",
        size=(64, 64),
    )
    assert img.mode == "RGB"
    assert img.size == (64, 64)


def test_load_image_extension_non_supportee_leve_valueerror(tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("hello")
    with pytest.raises(ValueError):
        load_image(bad)


def _write_synthetic_dicom(path: Path, photometric: str = "MONOCHROME2") -> None:
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
    ds.save_as(str(path), enforce_file_format=True)


def test_load_image_dicom_monochrome2(tmp_path):
    dcm_path = tmp_path / "radio.dcm"
    _write_synthetic_dicom(dcm_path, "MONOCHROME2")
    img = load_image(dcm_path, size=(32, 32))
    assert img.mode == "RGB"
    assert img.size == (32, 32)


def test_load_image_dicom_monochrome1_est_inverse(tmp_path):
    """MONOCHROME1 = échelle inversée : le coin le plus lumineux d'un mode
    doit devenir le plus sombre de l'autre (voir ai/dicom_utils.py, même règle)."""
    m2_path, m1_path = tmp_path / "m2.dcm", tmp_path / "m1.dcm"
    _write_synthetic_dicom(m2_path, "MONOCHROME2")
    _write_synthetic_dicom(m1_path, "MONOCHROME1")

    m2 = np.asarray(load_image(m2_path, size=(8, 8)))
    m1 = np.asarray(load_image(m1_path, size=(8, 8)))
    assert m2[-1, -1].mean() > m2[0, 0].mean()
    assert m1[-1, -1].mean() < m1[0, 0].mean()
