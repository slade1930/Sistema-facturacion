import os
import sys
from pathlib import Path

# Gente, esto es solo para que `pytest` encuentre `app` dentro del contenedor.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Gente, claves fijas de prueba: la app ya no trae ninguna por defecto.
CLAVE_API_PRUEBA = "api-key-de-prueba"
CLAVE_HMAC_PRUEBA = "clave-hmac-de-prueba"


def pytest_configure(config):
    # Gente, registramos el mark para que pytest no largue el warning.
    config.addinivalue_line(
        "markers", "integration: prueba que necesita DATABASE_URL"
    )
    os.environ.setdefault("API_KEY", CLAVE_API_PRUEBA)
    os.environ.setdefault("FACTURA_HMAC_KEY", CLAVE_HMAC_PRUEBA)
