import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

RAIZ = Path(__file__).resolve().parents[1]
VOCES = (
    "Intentá", "intentá", "Revisá", "revisá", "Elegí", "Ingresá", "Volvé",
    "completá", "completás", "Probá", "emití", "Emití", "confirmá",
    "comprobá", "Agregá", "agregá", "sumá", "Tomá", "usá",
)


def test_orq_interfaz_no_usa_voseo():
    encontrados = []
    for ruta in RAIZ.rglob("*.py"):
        if "__pycache__" in ruta.parts or ruta.name == Path(__file__).name:
            continue
        texto = ruta.read_text()
        for numero, linea in enumerate(texto.splitlines(), start=1):
            for voz in VOCES:
                if re.search(rf"\b{re.escape(voz)}\b", linea):
                    encontrados.append(f"{ruta.relative_to(RAIZ)}:{numero}: {voz}")

    assert encontrados == [], "Se encontró voseo en: " + ", ".join(encontrados)
