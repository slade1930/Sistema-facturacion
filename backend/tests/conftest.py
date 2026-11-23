import sys
from pathlib import Path

# Gente, esto es solo para que `pytest` encuentre `app` dentro del contenedor.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def pytest_configure(config):
    # Gente, registramos el mark para que pytest no largue el warning.
    config.addinivalue_line(
        "markers", "integration: prueba que necesita DATABASE_URL"
    )
