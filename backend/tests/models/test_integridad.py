from sqlalchemy import CheckConstraint, UniqueConstraint

from app.db.base import Base
from app.models import facturacion  # noqa: F401


def test_factura_no_tiene_fk_a_configuracion_negocio():
    tabla = Base.metadata.tables["factura"]
    destinos = {fk.target_fullname for fk in tabla.foreign_keys}
    assert "configuracion_negocio.id" not in destinos
    assert destinos == set(), destinos


def test_factura_generada_id_sin_unique():
    tabla = Base.metadata.tables["factura"]
    columnas_unicas = set()
    for restriccion in tabla.constraints:
        if isinstance(restriccion, UniqueConstraint):
            columnas_unicas.update(columna.name for columna in restriccion.columns)
    assert "factura_generada_id" not in columnas_unicas
    assert tabla.c.factura_generada_id.unique is not True


def test_codigo_verificacion_unico():
    tabla = Base.metadata.tables["factura"]
    assert tabla.c.codigo_verificacion.unique is True


def test_check_de_itbms_exento():
    tabla = Base.metadata.tables["linea_factura"]
    checks = [c for c in tabla.constraints if isinstance(c, CheckConstraint)]
    assert any(
        "tasa_itbms" in str(c.sqltext) and "impuesto" in str(c.sqltext)
        for c in checks
    )


def test_tablas_del_pr1():
    esperadas = {
        "configuracion_negocio",
        "contador_serie",
        "contador_orden_compra",
        "factura",
        "linea_factura",
    }
    assert esperadas <= set(Base.metadata.tables)
    assert len(Base.metadata.tables) == 5