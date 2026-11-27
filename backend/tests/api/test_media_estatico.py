"""Pruebas del servidor de archivos `media/` (issue #45)."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import montar_media

PNG = b"\x89PNG\r\n\x1a\ncontenido de prueba"


def test_media_se_sirve_sin_api_key(tmp_path):
    directorio = tmp_path / "media"
    directorio.mkdir()
    (directorio / "logo.png").write_bytes(PNG)

    app = FastAPI()
    montar_media(app, directorio)

    with TestClient(app) as client:
        respuesta = client.get("/media/logo.png")

    assert respuesta.status_code == 200
    assert respuesta.content == PNG
    assert respuesta.headers["content-type"].startswith("image/png")


def test_archivo_inexistente_da_404(tmp_path):
    app = FastAPI()
    montar_media(app, tmp_path / "media")

    with TestClient(app) as client:
        respuesta = client.get("/media/no-existe.png")

    assert respuesta.status_code == 404


def test_app_principal_monta_media():
    from app.main import app

    assert any(getattr(ruta, "path", None) == "/media" for ruta in app.routes)
