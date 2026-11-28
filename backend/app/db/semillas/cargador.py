"""Carga de los bloques de catálogo: planificar, simular y escribir.

El cargador nunca hace commit: la CLI decide si confirma la transacción. Sí
hace flush cuando necesita identificadores (categorías y productos nuevos).
"""

from dataclasses import dataclass, field, replace
from decimal import Decimal
import hashlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.semillas.esquema import validar_bloques
from app.models.catalogo import Categoria, Producto, SectorEmpresa
from app.models.inventario import TipoMovimiento
from app.repositories.catalogo import (
    CategoriaRepository,
    IntegridadError,
    ProductoRepository,
)
from app.repositories.inventario import InventarioRepository
from app.schemas.catalogo import CategoriaCreate, ProductoCreate, ProductoUpdate
from app.services.inventario import ajustar

_CAMPOS_PRODUCTO = (
    "nombre",
    "descripcion_corta",
    "marca",
    "presentacion",
    "imagen",
    "precio_caja",
    "precio_media_caja",
    "permite_media_caja",
    "precio_unidad",
    "precio_consumidor",
    "unidades_por_caja",
    "descuento_pct",
    "aplica_itbms",
    "estado_activo",
)


@dataclass(frozen=True)
class Cambio:
    """Acción calculada para un producto del archivo."""

    bloque: str
    nombre: str
    categoria: str
    datos: dict[str, Any]
    accion: str  # crear | actualizar | omitir
    sku: str | None = None
    categoria_id: int | None = None
    producto_id: int | None = None


@dataclass
class PlanCarga:
    cambios: list[Cambio] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    omitidos: int = 0


@dataclass
class ResumenCarga:
    sector: str
    simulacion: bool = False
    creados: int = 0
    actualizados: int = 0
    omitidos: int = 0
    errores: list[str] = field(default_factory=list)
    detalles: list[str] = field(default_factory=list)

    def lineas(self) -> list[str]:
        """Texto listo para imprimir en la consola."""
        modo = "simulación (sin escribir)" if self.simulacion else "carga"
        lineas = [
            f"Sector: {self.sector}",
            f"Modo: {modo}",
            f"Creados: {self.creados}",
            f"Actualizados: {self.actualizados}",
            f"Omitidos: {self.omitidos}",
            f"Errores: {len(self.errores)}",
        ]
        lineas.extend(f"  - {detalle}" for detalle in self.detalles)
        return lineas


def generar_sku(sector: str, categoria: str, nombre: str) -> str:
    """SKU determinista: prefijo del sector y hash corto de categoría + nombre.

    Ejemplo: ``SUP-3F2A9C1D77``. No se guarda el SKU que escriba la persona:
    siempre se genera acá para evitar duplicados y cumplir con NOT NULL UNIQUE.
    """
    prefijo = sector[:3].upper()
    semilla = f"{sector}|{categoria}|{nombre}".encode("utf-8")
    return f"{prefijo}-{hashlib.sha256(semilla).hexdigest()[:10].upper()}"


def _campos_producto(datos: dict[str, Any]) -> dict[str, Any]:
    campos = {campo: datos[campo] for campo in _CAMPOS_PRODUCTO if campo in datos}
    # Si se desactiva la media caja, se limpia el precio viejo aunque la persona
    # no haya escrito el campo.
    if datos.get("permite_media_caja") is False and "precio_media_caja" not in campos:
        campos["precio_media_caja"] = None
    return campos


def _nombrar(cambio: Cambio) -> str:
    return f"{cambio.bloque} / {cambio.categoria} / {cambio.nombre}"


def preparar(
    db: Session, sector: str, bloques: dict, solo_bloque: str | None = None
) -> PlanCarga:
    """Valida y calcula qué se crearía, actualizaría u omitiría, sin escribir."""
    sector = getattr(sector, "value", sector)
    plan = PlanCarga()
    plan.errores = validar_bloques(sector, bloques)
    if plan.errores:
        return plan

    try:
        sector_enum = SectorEmpresa(sector)
    except (TypeError, ValueError):
        plan.errores.append(f"sector: {sector!r} no es válido.")
        return plan

    contenido_bloques = {
        nombre: datos for nombre, datos in bloques.items() if isinstance(datos, dict)
    }
    if solo_bloque is not None:
        bloque_elegido = (
            solo_bloque.strip().upper()
            if isinstance(solo_bloque, str)
            else solo_bloque
        )
        if bloque_elegido not in contenido_bloques:
            plan.errores.append(
                f"bloque: '{bloque_elegido}' no existe en el archivo de {sector}."
            )
            return plan
        plan.omitidos = sum(
            len(datos.get("productos", []))
            for nombre, datos in contenido_bloques.items()
            if nombre != bloque_elegido
        )
        contenido_bloques = {bloque_elegido: contenido_bloques[bloque_elegido]}

    repositorio_categorias = CategoriaRepository(db)
    categorias: dict[str, Categoria | None] = {}
    # Se consultan las categorías de TODO el archivo: con --bloque, un producto
    # puede usar una categoría declarada por otra persona y ya existir en la base.
    for datos in bloques.values():
        if not isinstance(datos, dict):
            continue
        for categoria in datos.get("categorias", []):
            nombre = categoria["nombre"]
            if nombre in categorias:
                continue
            existente = repositorio_categorias.get_by_nombre(nombre)
            if existente is not None and existente.sector != sector_enum:
                plan.errores.append(
                    f"{nombre}: la categoría ya existe en el sector "
                    f"'{getattr(existente.sector, 'value', existente.sector)}'."
                )
            categorias[nombre] = existente

    if plan.errores:
        return plan

    nombres = [
        producto["nombre"]
        for datos in contenido_bloques.values()
        for producto in datos.get("productos", [])
    ]
    ids_categorias = [cat.id for cat in categorias.values() if cat is not None]
    existentes: dict[tuple[int, str], Producto] = {}
    if ids_categorias and nombres:
        consulta = select(Producto).where(
            Producto.categoria_id.in_(ids_categorias),
            Producto.nombre.in_(nombres),
        )
        existentes = {
            (producto.categoria_id, producto.nombre): producto
            for producto in db.scalars(consulta).all()
        }

    repositorio_productos = ProductoRepository(db)
    skus_vistos: set[str] = set()
    for bloque, datos in contenido_bloques.items():
        for producto in datos.get("productos", []):
            nombre = producto["nombre"]
            categoria = producto["categoria"]
            categoria_obj = categorias.get(categoria)
            sku = generar_sku(sector, categoria, nombre)
            cambio = Cambio(
                bloque=bloque,
                nombre=nombre,
                categoria=categoria,
                datos=producto,
                accion="crear",
                sku=sku,
                categoria_id=categoria_obj.id if categoria_obj is not None else None,
                producto_id=None,
            )

            if categoria_obj is not None:
                anterior = existentes.get((categoria_obj.id, nombre))
                if anterior is not None:
                    campos = ProductoUpdate(**_campos_producto(producto)).model_dump(
                        exclude_unset=True
                    )
                    sin_cambios = all(
                        getattr(anterior, campo) == valor
                        for campo, valor in campos.items()
                    )
                    accion = "omitir" if sin_cambios else "actualizar"
                    plan.cambios.append(
                        replace(
                            cambio,
                            accion=accion,
                            sku=anterior.sku,
                            producto_id=anterior.id,
                        )
                    )
                    continue

            if sku is not None and sku not in skus_vistos:
                skus_vistos.add(sku)
                otro = repositorio_productos.get_by_sku(sku)
                if otro is not None:
                    plan.errores.append(
                        f"{bloque}.productos: el sku generado '{sku}' ya pertenece a "
                        f"'{otro.nombre}'."
                    )
            plan.cambios.append(cambio)

    return plan


def cargar(
    db: Session,
    sector: str,
    bloques: dict,
    solo_bloque: str | None = None,
    *,
    simular: bool = False,
) -> ResumenCarga:
    """Aplica el plan calculado por ``preparar``. Sin commit; con ``simular``, sin escritura."""
    sector = getattr(sector, "value", sector)
    plan = preparar(db, sector, bloques, solo_bloque)
    resumen = ResumenCarga(sector=sector, simulacion=simular, omitidos=plan.omitidos)
    if plan.errores:
        resumen.errores.extend(plan.errores)
        return resumen

    try:
        sector_enum = SectorEmpresa(sector)
    except (TypeError, ValueError):
        resumen.errores.append(f"sector: {sector!r} no es válido.")
        return resumen

    categorias_creadas: dict[str, Categoria] = {}
    productos_repo = ProductoRepository(db)

    for cambio in plan.cambios:
        if cambio.accion == "omitir":
            resumen.omitidos += 1
            resumen.detalles.append(f"omitir (sin cambios): {_nombrar(cambio)}")
            continue
        if simular:
            if cambio.accion == "crear":
                resumen.creados += 1
            else:
                resumen.actualizados += 1
            resumen.detalles.append(f"simular {cambio.accion}: {_nombrar(cambio)}")
            continue

        try:
            if cambio.accion == "crear":
                categoria_id = cambio.categoria_id
                if categoria_id is None:
                    categoria = categorias_creadas.get(cambio.categoria)
                    if categoria is None:
                        categoria = CategoriaRepository(db).crear(
                            CategoriaCreate(
                                nombre=cambio.categoria, sector=sector_enum
                            ),
                            commit=False,
                        )
                        categorias_creadas[cambio.categoria] = categoria
                    categoria_id = categoria.id
                producto = productos_repo.crear(
                    ProductoCreate(
                        categoria_id=categoria_id,
                        sku=cambio.sku,
                        **_campos_producto(cambio.datos),
                    ),
                    commit=False,
                )
                inventario = InventarioRepository(db).obtener_o_crear(producto.id)
                movimiento = ajustar(
                    db,
                    inventario,
                    existencias=Decimal(str(cambio.datos["stock_inicial"])),
                    stock_minimo=Decimal("0.00"),
                    cuenta_id=None,
                    motivo="carga inicial",
                )
                if movimiento is not None:
                    movimiento.tipo = TipoMovimiento.ENTRADA
                resumen.creados += 1
                resumen.detalles.append(f"creado: {_nombrar(cambio)} ({producto.sku})")
            else:
                producto = db.get(Producto, cambio.producto_id)
                if producto is None:
                    resumen.errores.append(
                        f"{cambio.bloque}.productos: no se encontró "
                        f"'{cambio.nombre}' para actualizar."
                    )
                    continue
                productos_repo.actualizar(
                    producto,
                    ProductoUpdate(**_campos_producto(cambio.datos)),
                    commit=False,
                )
                resumen.actualizados += 1
                resumen.detalles.append(f"actualizado: {_nombrar(cambio)}")
        except IntegridadError as exc:
            resumen.errores.append(
                f"{cambio.bloque}.productos: no se pudo guardar "
                f"'{cambio.nombre}' ({exc})."
            )
            break

    return resumen
