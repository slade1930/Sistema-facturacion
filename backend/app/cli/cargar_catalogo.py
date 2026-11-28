"""Carga el catálogo de un sector desde los bloques de semillas.

Uso:
    python -m app.cli.cargar_catalogo --sector tecnologia [--bloque MOISES] [--simular]
"""

import argparse
import importlib
import sys

from app.db.semillas.cargador import cargar
from app.db.semillas.esquema import SECTORES, validar_bloques
from app.db.session import get_session_local


def _leer_bloques(sector: str) -> dict:
    modulo = importlib.import_module(f"app.db.semillas.{sector}")
    return modulo.BLOQUES


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description="Carga los bloques de catálogo de un sector."
    )
    analizador.add_argument(
        "--sector", required=True, choices=SECTORES, help="Sector a cargar."
    )
    analizador.add_argument(
        "--bloque", default=None, help="Carga solo este bloque (por ejemplo MOISES)."
    )
    analizador.add_argument(
        "--simular", action="store_true", help="Valida y muestra el plan sin escribir."
    )
    argumentos = analizador.parse_args(argv)

    sector = argumentos.sector
    bloques = _leer_bloques(sector)
    errores = validar_bloques(sector, bloques)
    bloque = None
    if argumentos.bloque is not None:
        bloque = argumentos.bloque.strip().upper()
        if bloque not in bloques:
            errores.append(
                f"bloque: '{argumentos.bloque}' no existe en el archivo de {sector}."
            )

    if errores:
        for error in errores:
            print(f"Error: {error}", file=sys.stderr)
        return 1

    db = get_session_local()()
    try:
        resumen = cargar(
            db,
            sector,
            bloques,
            solo_bloque=bloque,
            simular=argumentos.simular,
        )
        if resumen.errores:
            db.rollback()
            for error in resumen.errores:
                print(f"Error: {error}", file=sys.stderr)
            return 2
        if not argumentos.simular:
            db.commit()
    except Exception as exc:
        db.rollback()
        print(f"No se pudo cargar el catálogo de {sector}: {exc}", file=sys.stderr)
        return 3
    finally:
        db.close()

    for linea in resumen.lineas():
        print(linea)
    return 0


if __name__ == "__main__":
    sys.exit(main())
