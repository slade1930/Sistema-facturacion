from sqlalchemy import UniqueConstraint

from app.db.base import Base
from app.models import facturacion  # noqa: F401

TABLAS_ESPERADAS = {
    "configuracion_negocio",
    "contador_serie",
    "contador_orden_compra",
    "factura",
    "linea_factura",
    "categoria",
    "producto",
    "cliente_b2b",
    "pedido_b2b",
    "linea_pedido_b2b",
}


def test_tablas_del_pr1():
    assert TABLAS_ESPERADAS == set(Base.metadata.tables)
    assert len(Base.metadata.tables) == 10


def test_factura_no_tiene_fk_a_configuracion_negocio():
    tabla = Base.metadata.tables["factura"]
    destinos = {fk.target_fullname for fk in tabla.foreign_keys}
    assert "configuracion_negocio.id" not in destinos
    assert destinos == set(), destinos


def test_factura_no_tiene_factura_generada_id():
    assert "factura_generada_id" not in Base.metadata.tables["factura"].c


def test_codigo_verificacion_unico_de_12_caracteres():
    tabla = Base.metadata.tables["factura"]
    columna = tabla.c.codigo_verificacion
    assert columna.unique is True
    assert columna.type.length == 12


def test_factura_generada_id_en_pedido_sin_fk_ni_unique():
    tabla = Base.metadata.tables["pedido_b2b"]
    columna = tabla.c.factura_generada_id
    assert columna.unique is not True
    assert not any(fk.parent is columna for fk in tabla.foreign_keys)
    columnas_unicas = set()
    for restriccion in tabla.constraints:
        if isinstance(restriccion, UniqueConstraint):
            columnas_unicas.update(c.name for c in restriccion.columns)
    assert "factura_generada_id" not in columnas_unicas


def test_linea_factura_tiene_gravada_y_monto():
    tabla = Base.metadata.tables["linea_factura"]
    assert "gravada" in tabla.c
    assert "monto" in tabla.c
    assert "tasa_itbms" not in tabla.c


def test_todas_las_relaciones_del_drawio():
    relaciones = {
        "linea_factura": {"factura.id", "producto.id"},
        "producto": {"categoria.id"},
        "pedido_b2b": {"cliente_b2b.id"},
        "linea_pedido_b2b": {"pedido_b2b.id", "producto.id"},
    }
    for nombre, esperados in relaciones.items():
        tabla = Base.metadata.tables[nombre]
        destinos = {fk.target_fullname for fk in tabla.foreign_keys}
        assert esperados <= destinos, (nombre, destinos)