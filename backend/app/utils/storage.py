
from pathlib import Path
from uuid import uuid4


# Carpeta backend/media
CARPETA_MEDIA = Path(__file__).resolve().parents[2] / "media"

TAMANO_MAXIMO = 5 * 1024 * 1024

FORMATOS_PERMITIDOS = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}


def guardar_logo(
    contenido: bytes,
    nombre_archivo: str,
    tipo_contenido: str,
) -> str:
    """
    Guarda un logo y devuelve su ruta relativa.
    Acepta PNG, JPG y WEBP de hasta 5 MB.
    """

    if not contenido:
        raise ValueError("El archivo está vacío.")

    if len(contenido) > TAMANO_MAXIMO:
        raise ValueError("El logo no puede superar los 5 MB.")

    extension = Path(nombre_archivo).suffix.lower().lstrip(".")

    if extension not in FORMATOS_PERMITIDOS:
        raise ValueError("Formato no permitido. Use PNG, JPG o WEBP.")

    if tipo_contenido != FORMATOS_PERMITIDOS[extension]:
        raise ValueError("El tipo de archivo no coincide con su extensión.")

    # Comprobar la firma real del archivo.
    if extension == "png":
        valido = contenido.startswith(b"\x89PNG\r\n\x1a\n")
    elif extension in ("jpg", "jpeg"):
        valido = contenido.startswith(b"\xff\xd8\xff")
    else:
        valido = (
            len(contenido) >= 12
            and contenido.startswith(b"RIFF")
            and contenido[8:12] == b"WEBP"
        )

    if not valido:
        raise ValueError("El contenido no corresponde a una imagen válida.")

    CARPETA_MEDIA.mkdir(parents=True, exist_ok=True)

    nombre_nuevo = f"{uuid4().hex}.{extension}"
    ruta = CARPETA_MEDIA / nombre_nuevo

    ruta.write_bytes(contenido)

    return f"media/{nombre_nuevo}"
