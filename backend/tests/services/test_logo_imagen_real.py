"""Gente: el logo tiene que ser una imagen de verdad antes de tocar disco."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.utils import storage


def _png_valido() -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (16, 16), (58, 0, 136, 255)).save(buffer, "PNG")
    return buffer.getvalue()


def test_logo_corrupto_da_error_y_no_guarda_nada(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "CARPETA_MEDIA", tmp_path / "media")
    roto = b"\x89PNG\r\n\x1a\n" + b"esto-no-es-un-png-completo"

    with pytest.raises(ValueError, match="imagen legible"):
        storage.guardar_logo(roto, "logo.png", "image/png")

    assert not (tmp_path / "media").exists() or list((tmp_path / "media").glob("*")) == []


def test_logo_valido_se_guarda(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "CARPETA_MEDIA", tmp_path / "media")
    png = _png_valido()

    ruta = storage.guardar_logo(png, "logo.png", "image/png")

    assert ruta.startswith("media/")
    archivo = tmp_path / "media" / Path(ruta).name
    assert archivo.read_bytes() == png
