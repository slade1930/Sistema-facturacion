"""Validación de los bloques de catálogo antes de escribir en la base.

Se reutilizan los esquemas Pydantic del catálogo y se añaden las reglas propias
de la carga por semillas. La función pública devuelve errores en lugar de
lanzarlos, para que la CLI pueda mostrarlos todos de una vez.
"""

from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, ValidationError

from app.models.catalogo import SectorEmpresa
from app.schemas.catalogo import CategoriaCreate, Dinero, ProductoCreate

SECTORES = ("supermercado", "turismo", "tecnologia")
LIMITE_PRODUCTOS = 20

_OBJETIVOS: dict[str, dict[str, int]] = {
    "supermercado": {
        "NIDIA": 4,
        "JOSHUA": 4,
        "JAVIER": 4,
        "ZEUS": 4,
        "HUGO": 4,
    },
    "turismo": {
        "JESUS": 4,
        "CRISTHIAN": 4,
        "ERICK": 4,
        "LUIS_CASTILLO": 4,
        "JOSE_RIVERA": 4,
    },
    "tecnologia": {
        "MOISES": 4,
        "ELIAN": 4,
        "IRVING": 3,
        "ANTONY": 3,
        "MANUEL_VARGAS": 3,
        "ANDRES": 3,
    },
}

_CAMPOS_TEXTO = ("descripcion_corta", "marca", "presentacion")
_PRECIOS = ("precio_unidad", "precio_caja")


class _Stock(BaseModel):
    """Envuelve ``Dinero`` para validar el stock inicial con el tipo del proyecto."""

    valor: Dinero = Decimal("0.00")


def objetivos(sector: str) -> dict[str, int]:
    """Devuelve la meta de productos por bloque para un sector."""
    try:
        clave = SectorEmpresa(sector).value
    except (TypeError, ValueError):
        raise ValueError(
            f"Sector desconocido: {sector!r}. Usa uno de: {', '.join(SECTORES)}."
        ) from None
    return dict(_OBJETIVOS[clave])


def _decimal_valor(valor: Any, ruta: str, errores: list[str]) -> Decimal | None:
    try:
        resultado = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        errores.append(f"{ruta}: debe ser un número decimal válido.")
        return None
    if not resultado.is_finite():
        errores.append(f"{ruta}: debe ser un número finito.")
        return None
    return resultado


def _dos_decimales(valor: Decimal) -> bool:
    try:
        return valor == valor.quantize(Decimal("0.01"))
    except InvalidOperation:
        return False


def _texto(valor: Any, ruta: str, errores: list[str], *, obligatorio: bool = False) -> None:
    if valor is None:
        if obligatorio:
            errores.append(f"{ruta}: es obligatorio.")
        return
    if not isinstance(valor, str):
        errores.append(f"{ruta}: debe ser texto.")
    elif valor.strip() != valor:
        errores.append(f"{ruta}: no debe tener espacios al inicio ni al final.")


def _errores_pydantic(exc: ValidationError, ruta: str, errores: list[str]) -> None:
    for detalle in exc.errors():
        campo = ".".join(str(parte) for parte in detalle.get("loc", ())) or "valor"
        errores.append(f"{ruta}.{campo}: {detalle.get('msg', 'valor no válido')}")


def validar_bloques(sector: str, bloques: dict) -> list[str]:
    """Devuelve todos los errores de los bloques de un sector (vacío si no hay).

    Las rutas de los errores usan ``bloque.campo`` o ``bloque.productos[i].campo``
    para que sea claro dónde corregir. Los archivos vacíos son válidos.
    """
    errores: list[str] = []
    try:
        clave = SectorEmpresa(sector).value
        sector_enum = SectorEmpresa(clave)
    except (TypeError, ValueError):
        return [
            f"sector: {sector!r} no es válido. Usa uno de: {', '.join(SECTORES)}."
        ]

    if not isinstance(bloques, dict):
        return ["bloques: debe ser un diccionario con un entrada por responsable."]

    nombres_categorias: set[str] = set()
    nombres_productos: dict[str, str] = {}
    total_productos = 0

    for bloque, contenido in bloques.items():
        if not isinstance(contenido, dict):
            errores.append(f"{bloque}: debe ser un diccionario con 'categorias' y 'productos'.")
            continue

        categorias = contenido.get("categorias", [])
        productos = contenido.get("productos", [])
        if not isinstance(categorias, list):
            errores.append(f"{bloque}.categorias: debe ser una lista.")
            categorias = []
        if not isinstance(productos, list):
            errores.append(f"{bloque}.productos: debe ser una lista.")
            productos = []

        for indice, categoria in enumerate(categorias):
            ruta = f"{bloque}.categorias[{indice}]"
            if not isinstance(categoria, dict):
                errores.append(f"{ruta}: debe ser un diccionario con 'nombre' y 'descripcion'.")
                continue
            nombre = categoria.get("nombre")
            _texto(nombre, f"{ruta}.nombre", errores, obligatorio=True)
            _texto(categoria.get("descripcion"), f"{ruta}.descripcion", errores)
            if isinstance(nombre, str) and nombre.strip():
                nombres_categorias.add(nombre)
                try:
                    CategoriaCreate(nombre=nombre, sector=sector_enum)
                except ValidationError as exc:
                    _errores_pydantic(exc, f"{ruta}.nombre", errores)

        for indice, producto in enumerate(productos):
            total_productos += 1
            ruta = f"{bloque}.productos[{indice}]"
            if not isinstance(producto, dict):
                errores.append(f"{ruta}: debe ser un diccionario.")
                continue

            nombre = producto.get("nombre")
            _texto(nombre, f"{ruta}.nombre", errores, obligatorio=True)
            if isinstance(nombre, str) and nombre.strip():
                if nombre in nombres_productos:
                    errores.append(
                        f"{ruta}.nombre: '{nombre}' ya está declarado en "
                        f"{nombres_productos[nombre]} (los nombres no se repiten en el sector)."
                    )
                else:
                    nombres_productos[nombre] = bloque

            categoria = producto.get("categoria")
            _texto(categoria, f"{ruta}.categoria", errores, obligatorio=True)
            if (
                isinstance(categoria, str)
                and categoria.strip()
                and categoria not in nombres_categorias
            ):
                errores.append(
                    f"{ruta}.categoria: '{categoria}' no está declarada en este archivo."
                )

            for campo in _CAMPOS_TEXTO:
                _texto(producto.get(campo), f"{ruta}.{campo}", errores)

            if "aplica_itbms" not in producto:
                errores.append(
                    f"{ruta}.aplica_itbms: debe estar definido explícitamente (true o false)."
                )
            elif not isinstance(producto["aplica_itbms"], bool):
                errores.append(f"{ruta}.aplica_itbms: debe ser true o false.")

            imagen = producto.get("imagen")
            if imagen is not None:
                if isinstance(imagen, str):
                    _texto(imagen, f"{ruta}.imagen", errores)
                if not isinstance(imagen, str):
                    errores.append(f"{ruta}.imagen: debe ser texto, None o una ruta 'media/...'.")
                else:
                    limpia = imagen.strip()
                    if limpia.lower().startswith(("http://", "https://")):
                        errores.append(
                            f"{ruta}.imagen: no se permiten imágenes de internet."
                        )
                    elif limpia and not limpia.startswith("media/"):
                        errores.append(
                            f"{ruta}.imagen: usa None o una ruta que empiece con 'media/'."
                        )

            if "stock_inicial" not in producto:
                errores.append(f"{ruta}.stock_inicial: es obligatorio.")
            else:
                try:
                    _Stock(valor=producto["stock_inicial"])
                except ValidationError:
                    errores.append(
                        f"{ruta}.stock_inicial: debe ser mayor o igual a cero con máximo 2 decimales."
                    )

            valores: dict[str, Decimal] = {}
            for campo in (*_PRECIOS, "precio_media_caja", "descuento_pct"):
                valor = producto.get(campo)
                if valor is None:
                    continue
                decimal = _decimal_valor(valor, f"{ruta}.{campo}", errores)
                if decimal is None:
                    continue
                if not _dos_decimales(decimal):
                    errores.append(f"{ruta}.{campo}: máximo 2 decimales.")
                    continue
                valores[campo] = decimal
                if campo in _PRECIOS and decimal <= 0:
                    errores.append(f"{ruta}.{campo}: debe ser mayor que cero.")
                elif campo == "descuento_pct" and not (Decimal("0") <= decimal <= Decimal("90")):
                    errores.append(f"{ruta}.descuento_pct: debe estar entre 0 y 90.")

            permite_media = producto.get("permite_media_caja", False)
            if not isinstance(permite_media, bool):
                errores.append(f"{ruta}.permite_media_caja: debe ser true o false.")
            media = producto.get("precio_media_caja")
            if permite_media is True and media is None:
                errores.append(
                    f"{ruta}.precio_media_caja: es obligatorio si permite_media_caja es true."
                )
            elif permite_media is not True and media is not None:
                errores.append(
                    f"{ruta}.precio_media_caja: solo se permite si permite_media_caja es true."
                )
            elif (
                permite_media is True
                and media is not None
                and "precio_media_caja" in valores
                and "precio_caja" in valores
                and valores["precio_media_caja"] >= valores["precio_caja"]
            ):
                errores.append(
                    f"{ruta}.precio_media_caja: debe ser menor que precio_caja."
                )

            # ProductoCreate ya exige >= 0, hasta 2 decimales y el rango de
            # descuento; acá solo se añaden las reglas específicas de semillas.
            campos_pydantic = {
                clave: valor
                for clave, valor in producto.items()
                if clave not in {"categoria", "stock_inicial", "sku"}
            }
            try:
                ProductoCreate(categoria_id=1, sku="VALIDACION", **campos_pydantic)
            except ValidationError as exc:
                _errores_pydantic(exc, ruta, errores)

    if total_productos > LIMITE_PRODUCTOS:
        errores.append(
            f"{clave}: hay {total_productos} productos en el archivo; el máximo es "
            f"{LIMITE_PRODUCTOS}."
        )

    return errores
