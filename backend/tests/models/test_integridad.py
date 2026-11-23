from sqlalchemy import CheckConstraint, Enum as SAEnum, UniqueConstraint

from app.db.base import Base
from app.models import facturacion  # noqa: F401
from app.models.facturacion import (
    CobrarPor,
    CondicionPago,
    EstadoFactura,
    EstadoPedido,
    TipoEmpaque,
)

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


def _fk(tabla, columna):
    foreign_keys = list(Base.metadata.tables[tabla].c[columna].foreign_keys)
    assert len(foreign_keys) == 1, (tabla, columna, foreign_keys)
    return foreign_keys[0]


def _checks(tabla):
    return {
        restriccion.name: str(restriccion.sqltext)
        for restriccion in Base.metadata.tables[tabla].constraints
        if isinstance(restriccion, CheckConstraint)
    }


def _columnas_unicas(tabla):
    columnas = set()
    for restriccion in Base.metadata.tables[tabla].constraints:
        if isinstance(restriccion, UniqueConstraint):
            columnas.update(columna.name for columna in restriccion.columns)
    for nombre, columna in Base.metadata.tables[tabla].c.items():
        if columna.unique:
            columnas.add(nombre)
    return columnas


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


def test_codigo_verificacion_de_12_caracteres_sin_unique():
    columna = Base.metadata.tables["factura"].c.codigo_verificacion
    assert columna.type.length == 12
    # Gente, el original no le puso UNIQUE, lo habíamos inventado nosotros.
    assert columna.unique is not True
    assert "codigo_verificacion" not in _columnas_unicas("factura")


def test_empresa_ruc_sin_unique():
    assert Base.metadata.tables["configuracion_negocio"].c.empresa_ruc.unique is not True
    assert "empresa_ruc" not in _columnas_unicas("configuracion_negocio")


def test_factura_generada_id_con_fk_y_sin_unique():
    tabla = Base.metadata.tables["pedido_b2b"]
    columna = tabla.c.factura_generada_id
    assert columna.unique is not True
    assert "factura_generada_id" not in _columnas_unicas("pedido_b2b")
    # Ahora sí hay FK real, pero sin UNIQUE (0..1 -> N pedidos).
    assert _fk("pedido_b2b", "factura_generada_id").target_fullname == "factura.id"
    assert _fk("pedido_b2b", "factura_generada_id").ondelete == "SET NULL"


def test_linea_factura_tiene_gravada_y_monto():
    tabla = Base.metadata.tables["linea_factura"]
    assert "gravada" in tabla.c
    assert "monto" in tabla.c
    assert "tasa_itbms" not in tabla.c


def test_todas_las_relaciones_del_drawio():
    relaciones = {
        "linea_factura": {"factura.id", "producto.id"},
        "producto": {"categoria.id"},
        "pedido_b2b": {"cliente_b2b.id", "factura.id"},
        "linea_pedido_b2b": {"pedido_b2b.id", "producto.id"},
    }
    for nombre, esperados in relaciones.items():
        tabla = Base.metadata.tables[nombre]
        destinos = {fk.target_fullname for fk in tabla.foreign_keys}
        assert esperados <= destinos, (nombre, destinos)


def test_enums_reales_con_valores_del_original():
    casos = [
        ("factura", "condicion_pago", CondicionPago, "condicion_pago"),
        ("factura", "estado", EstadoFactura, "estado_factura"),
        ("linea_factura", "cobrar_por", CobrarPor, "cobrar_por"),
        ("pedido_b2b", "estado", EstadoPedido, "estado_pedido_b2b"),
        ("linea_pedido_b2b", "tipo_empaque", TipoEmpaque, "tipo_empaque_b2b"),
    ]
    for tabla, columna, enum_cls, nombre_tipo in casos:
        tipo = Base.metadata.tables[tabla].c[columna].type
        assert isinstance(tipo, SAEnum), (tabla, columna)
        assert tipo.name == nombre_tipo
        assert [miembro.value for miembro in enum_cls] == list(tipo.enums)


def test_enum_values_estan_en_minuscula():
    assert [m.value for m in CondicionPago] == ["contado", "credito"]
    assert [m.value for m in EstadoFactura] == ["emitida", "anulada"]
    assert [m.value for m in CobrarPor] == ["unidad", "caja"]
    assert [m.value for m in EstadoPedido] == [
        "pendiente",
        "procesando",
        "facturado",
        "cancelado",
    ]
    assert [m.value for m in TipoEmpaque] == ["caja", "media_caja", "unidad"]


def test_defaults_del_original():
    columnas = Base.metadata.tables
    assert columnas["linea_factura"].c.gravada.default.arg is True
    assert columnas["factura"].c.mostrar_ruc.default.arg is True
    assert columnas["configuracion_negocio"].c.mostrar_ruc.default.arg is True
    assert columnas["factura"].c.condicion_pago.default.arg is CondicionPago.CONTADO
    assert columnas["factura"].c.estado.default.arg is EstadoFactura.EMITIDA
    assert columnas["linea_factura"].c.cobrar_por.default.arg is CobrarPor.UNIDAD
    assert columnas["pedido_b2b"].c.estado.default.arg is EstadoPedido.PENDIENTE
    assert columnas["linea_pedido_b2b"].c.tipo_empaque.default.arg is TipoEmpaque.CAJA
    assert (
        columnas["configuracion_negocio"].c.color_principal.default.arg == "#3A0088"
    )
    assert (
        columnas["configuracion_negocio"].c.color_barra_factura.default.arg
        == "#5B3A9E"
    )
    assert columnas["configuracion_negocio"].c.color_tabla.default.arg == "#3A0088"


def test_ondelete_y_nullabilidad_de_todas_las_fk():
    esperados = [
        ("linea_factura", "factura_id", "CASCADE", False),
        ("linea_factura", "producto_id", "SET NULL", True),
        ("producto", "categoria_id", "RESTRICT", False),
        ("pedido_b2b", "cliente_id", "RESTRICT", False),
        ("pedido_b2b", "factura_generada_id", "SET NULL", True),
        ("linea_pedido_b2b", "pedido_id", "CASCADE", False),
        ("linea_pedido_b2b", "producto_id", "RESTRICT", False),
    ]
    for tabla, columna, ondelete, nullable in esperados:
        column = Base.metadata.tables[tabla].c[columna]
        assert _fk(tabla, columna).ondelete == ondelete, (tabla, columna)
        assert column.nullable is nullable, (tabla, columna)


def test_precio_unidad_not_null():
    assert Base.metadata.tables["producto"].c.precio_unidad.nullable is False


def test_email_contacto_not_null():
    assert Base.metadata.tables["cliente_b2b"].c.email_contacto.nullable is False


def test_checks_del_original():
    for tabla in ("contador_serie", "contador_orden_compra"):
        checks = _checks(tabla)
        assert checks[f"ck_{tabla}_anio"] == "anio >= 0"
    assert "anio BETWEEN 1900 AND 9999" not in str(
        list(Base.metadata.tables["contador_serie"].constraints)
    )
    checks = _checks("linea_factura")
    assert "cantidad >= 0.01" in checks["ck_linea_factura_cantidad"]
    assert "unidades_por_caja >= 1" in checks["ck_linea_factura_unidades"]
    assert "unidades_por_caja >= 1" in _checks("producto")["ck_producto_unidades"]
    # El check de anulación no contradice al original: se anula con fecha.
    assert "anulada" in _checks("factura")["ck_factura_anulacion"]


def test_mixin_de_fechas_realmente_usado():
    for tabla in ("producto", "pedido_b2b"):
        columnas = Base.metadata.tables[tabla].c
        assert "fecha_creacion" in columnas
        assert "fecha_actualizacion" in columnas
        assert "created_at" not in columnas
        assert "updated_at" not in columnas
    for tabla in Base.metadata.tables.values():
        assert "created_at" not in tabla.c
        assert "updated_at" not in tabla.c
