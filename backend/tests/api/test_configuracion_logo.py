"""Pruebas de la subida del logo de la configuración."""

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.utils import storage

# PNG de 1x1 generado en memoria, sin archivos en el repo.
# Gente, antes tenía el CRC del IDAT mal y Pillow lo rechazaba: lo corrijo.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

CONFIGURACION = {
    "empresa_nombre": "Negocio Logo API",
    "empresa_ruc": "RUC-LOGO-API",
    "color_principal": "#123456",
}


@pytest.fixture
def media_temporal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Media temporal para no ensuciar backend/media ni el repo."""
    carpeta = tmp_path / "media"
    monkeypatch.setattr(storage, "CARPETA_MEDIA", carpeta)
    return carpeta


def _crear_configuracion(client: TestClient) -> None:
    respuesta = client.put("/api/v1/configuracion", json=CONFIGURACION)
    assert respuesta.status_code == 200, respuesta.text


def _archivos(nombre: str = "logo.png", contenido: bytes = PNG, tipo: str = "image/png"):
    return {"archivo": (nombre, contenido, tipo)}


def test_subir_logo_valido(client: TestClient, media_temporal: Path) -> None:
    _crear_configuracion(client)

    respuesta = client.post(
        "/api/v1/configuracion/logo", files=_archivos()
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    ruta = datos["logo"]

    assert ruta.startswith("media/")
    assert ruta.endswith(".png")
    assert (media_temporal / Path(ruta).name).is_file()
    assert client.get("/api/v1/configuracion").json()["logo"] == ruta


def test_reemplazar_logo_borra_el_anterior(
    client: TestClient, media_temporal: Path
) -> None:
    _crear_configuracion(client)

    primera = client.post("/api/v1/configuracion/logo", files=_archivos())
    assert primera.status_code == 200, primera.text
    ruta_vieja = media_temporal / Path(primera.json()["logo"]).name
    assert ruta_vieja.is_file()

    segunda = client.post(
        "/api/v1/configuracion/logo", files=_archivos(nombre="otro.png")
    )
    assert segunda.status_code == 200, segunda.text
    ruta_nueva = media_temporal / Path(segunda.json()["logo"]).name

    assert ruta_nueva.is_file()
    assert not ruta_vieja.exists()
    assert segunda.json()["logo"] != primera.json()["logo"]


def test_tipo_no_permitido(client: TestClient, media_temporal: Path) -> None:
    _crear_configuracion(client)

    respuesta = client.post(
        "/api/v1/configuracion/logo",
        files=_archivos(nombre="logo.txt", contenido=PNG, tipo="image/png"),
    )

    assert respuesta.status_code == 422
    assert "Formato no permitido" in respuesta.json()["detail"]
    assert not media_temporal.exists() or not any(media_temporal.iterdir())


def test_archivo_demasiado_grande(client: TestClient, media_temporal: Path) -> None:
    _crear_configuracion(client)

    contenido = b"\x89PNG\r\n\x1a\n" + b"0" * storage.TAMANO_MAXIMO
    respuesta = client.post(
        "/api/v1/configuracion/logo", files=_archivos(contenido=contenido)
    )

    assert respuesta.status_code == 422
    assert "5 MB" in respuesta.json()["detail"]
    assert not media_temporal.exists() or not any(media_temporal.iterdir())


def test_nombre_malicioso_no_sale_de_media(
    client: TestClient, media_temporal: Path, tmp_path: Path
) -> None:
    _crear_configuracion(client)

    respuesta = client.post(
        "/api/v1/configuracion/logo",
        files=_archivos(nombre="../../x.png"),
    )

    assert respuesta.status_code == 422
    assert not (tmp_path / "x.png").exists()
    assert not media_temporal.exists() or not any(media_temporal.iterdir())


def test_sin_archivo(client: TestClient, media_temporal: Path) -> None:
    _crear_configuracion(client)

    respuesta = client.post("/api/v1/configuracion/logo")

    assert respuesta.status_code == 422


def test_sin_api_key_se_rechaza(
    client: TestClient, media_temporal: Path
) -> None:
    _crear_configuracion(client)

    respuesta = client.post(
        "/api/v1/configuracion/logo",
        files=_archivos(),
        headers={"X-API-Key": ""},
    )

    assert respuesta.status_code == 401
    assert not media_temporal.exists() or not any(media_temporal.iterdir())
