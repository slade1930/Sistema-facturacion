import sys
from pathlib import Path

# Gente, esto es solo para que `pytest` encuentre `app` dentro del contenedor.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
