"""Verifica el avance de los bloques de catálogo por sector y persona.

Uso:
    python -m app.cli.verificar_catalogo [--sector tecnologia]
"""

import argparse
import importlib
from decimal import Decimal
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.semillas.esquema import (
    LIMITE_PRODUCTOS,
    SECTORES,
    objetivos,
    validar_bloques,
)
from app.db.session import get_session_local
from app.models.catalogo import Categoria, Producto, SectorEmpresa


def _pares_declarados(bloques: dict) -> dict[tuple[str, str], str]:
    """Relaciona (categoría, nombre) con el bloque que lo declaró."""
    pares: dict[tuple[str, str], str] = {}
    for bloque, datos in bloques.items():
        if not isinstance(datos, dict):
            continue
        for producto in datos.get("productos", []):
            if not isinstance(producto, dict):
                continue
            categoria = producto.get("categoria")
            nombre = producto.get("nombre")
            if isinstance(categoria, str) and isinstance(nombre, str):
                pares[(categoria, nombre)] = bloque
    return pares


def verificar_sector(db: Session, sector: str, bloques: dict) -> list[str]:
    """Devuelve las líneas del informe de un sector."""
    errores = validar_bloques(sector, bloques)
    metas = objetivos(sector)
    conteos: dict[str, dict[str, int]] = {
        bloque: {"cargados": 0, "oferta": 0, "media": 0} for bloque in bloques
    }

    pares = _pares_declarados(bloques)
    if pares:
        nombres = [nombre for _, nombre in pares]
        consulta = (
            select(
                Categoria.nombre,
                Producto.nombre,
                Producto.descuento_pct,
                Producto.permite_media_caja,
            )
            .join(Categoria, Producto.categoria_id == Categoria.id)
            .where(
                Categoria.sector == SectorEmpresa(sector),
                Producto.nombre.in_(nombres),
            )
        )
        for categoria, nombre, descuento, permite_media in db.execute(consulta).all():
            bloque = pares.get((categoria, nombre))
            if bloque is None:
                continue
            conteos[bloque]["cargados"] += 1
            if descuento is not None and Decimal(str(descuento)) > 0:
                conteos[bloque]["oferta"] += 1
            if permite_media:
                conteos[bloque]["media"] += 1

    lineas = [
        f"Sector: {sector} (máximo {LIMITE_PRODUCTOS} productos)",
        (
            f"{'Bloque':<16} {'Categorías':>10} {'Cargados/meta':>14} "
            f"{'Oferta':>7} {'Media caja':>11} {'Reglas':>7}"
        ),
    ]
    total_cargados = 0
    for bloque, datos in bloques.items():
        categorias = datos.get("categorias", []) if isinstance(datos, dict) else []
        declaradas = len(categorias) if isinstance(categorias, list) else 0
        valores = conteos.get(bloque, {"cargados": 0, "oferta": 0, "media": 0})
        reglas = sum(1 for error in errores if error.startswith(f"{bloque}."))
        total_cargados += valores["cargados"]
        meta = metas.get(bloque, 0)
        avance = f"{valores['cargados']}/{meta}"
        lineas.append(
            f"{bloque:<16} {declaradas:>10} {avance:>14} "
            f"{valores['oferta']:>7} {valores['media']:>11} {reglas:>7}"
        )

    lineas.append(
        f"Total del sector: {total_cargados}/{LIMITE_PRODUCTOS} productos"
    )
    for error in errores:
        lineas.append(f"  ! {error}")
    return lineas


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description="Verifica categorías, productos cargados y reglas por bloque."
    )
    analizador.add_argument(
        "--sector", choices=SECTORES, default=None, help="Sector a verificar (todos por defecto)."
    )
    argumentos = analizador.parse_args(argv)

    sectores = [argumentos.sector] if argumentos.sector else list(SECTORES)
    db = get_session_local()()
    try:
        for sector in sectores:
            modulo = importlib.import_module(f"app.db.semillas.{sector}")
            for linea in verificar_sector(db, sector, modulo.BLOQUES):
                print(linea)
            print()
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
