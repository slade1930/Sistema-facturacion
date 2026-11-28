"""Pruebas de los bloques de semillas: validación y carga sin duplicados."""

import importlib.util
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registra tablas y relaciones)
from app.db.base import Base
from app.db.semillas import supermercado, tecnologia, turismo
from app.db.semillas.cargador import cargar, generar_sku, preparar
from app.db.semillas.esquema import SECTORES, objetivos, validar_bloques
from app.models.catalogo import Categoria, Producto, SectorEmpresa
from app.models.inventario import Inventario, MovimientoInventario, TipoMovimiento

MODULOS = {
    "supermercado": supermercado,
    "turismo": turismo,
    "tecnologia": tecnologia,
}


@pytest.fixture()
def db():
    """Base SQLite en memoria, nueva para cada prueba, sin base externa."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    sesion = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield sesion
    finally:
        sesion.close()
        engine.dispose()


def _producto(nombre="Producto de prueba", categoria="Bebidas", **extra):
    datos = dict(
        categoria=categoria,
        nombre=nombre,
        descripcion_corta="Descripción neutra de prueba.",
        marca="Marca de prueba",
        presentacion="botella de 1 L",
        precio_unidad=Decimal("2.00"),
        unidades_por_caja=12,
        permite_media_caja=True,
        precio_media_caja=Decimal("11.00"),
        precio_caja=Decimal("20.00"),
        descuento_pct=Decimal("5.00"),
        aplica_itbms=True,
        estado_activo=True,
        imagen=None,
        stock_inicial=Decimal("8.00"),
    )
    datos.update(extra)
    return datos


def _bloques(productos, categoria="Bebidas"):
    return {
        "PRUEBA": {
            "categorias": [
                {"nombre": categoria, "descripcion": "Categoría de prueba"}
            ],
            "productos": productos,
        }
    }


def _archivo_temporal(tmp_path, sector, bloques):
    """Escribe un módulo temporal con BLOQUES y lo importa como los reales."""
    ruta = tmp_path / f"{sector}.py"
    ruta.write_text(
        "from decimal import Decimal\n\nBLOQUES = " + repr(bloques) + "\n",
        encoding="utf-8",
    )
    especificacion = importlib.util.spec_from_file_location(
        f"semilla_temporal_{sector}", ruta
    )
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return sector, modulo.BLOQUES


# ---------------- Archivos versionados ----------------
@pytest.mark.parametrize("sector", SECTORES)
def test_archivos_versionados_estan_vacios_y_son_validos(sector):
    bloques = MODULOS[sector].BLOQUES

    assert set(bloques) == set(objetivos(sector))
    for datos in bloques.values():
        assert datos["categorias"] == []
        assert datos["productos"] == []
    assert validar_bloques(sector, bloques) == []


def test_objetivos_por_bloque():
    assert objetivos("supermercado") == {
        "NIDIA": 4,
        "JOSHUA": 4,
        "JAVIER": 4,
        "ZEUS": 4,
        "HUGO": 4,
    }
    assert objetivos("turismo") == {
        "JESUS": 4,
        "CRISTHIAN": 4,
        "ERICK": 4,
        "LUIS_CASTILLO": 4,
        "JOSE_RIVERA": 4,
    }
    assert objetivos("tecnologia") == {
        "MOISES": 4,
        "ELIAN": 4,
        "IRVING": 3,
        "ANTONY": 3,
        "MANUEL_VARGAS": 3,
        "ANDRES": 3,
    }


def test_sector_desconocido_en_objetivos():
    with pytest.raises(ValueError):
        objetivos("otro")


# ---------------- Validación ----------------
@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"precio_unidad": Decimal("0")}, "precio_unidad"),
        ({"precio_caja": Decimal("1.234")}, "precio_caja"),
        ({"unidades_por_caja": 0}, "unidades_por_caja"),
        ({"descuento_pct": Decimal("91")}, "descuento_pct"),
        ({"stock_inicial": Decimal("-1")}, "stock_inicial"),
        ({"precio_media_caja": None}, "precio_media_caja"),
        ({"precio_media_caja": Decimal("20.00")}, "precio_media_caja"),
        ({"imagen": "https://ejemplo.invalid/foto.png"}, "imagen"),
        ({"nombre": "  Producto con espacios"}, "nombre"),
        ({"marca": "Marca "}, "marca"),
    ],
)
def test_validacion_rechaza_valores_incorrectos(cambios, campo):
    errores = validar_bloques("tecnologia", _bloques([_producto(**cambios)]))
    assert any(campo in error for error in errores)


def test_validacion_exige_itbms_explicito():
    producto = _producto()
    del producto["aplica_itbms"]
    errores = validar_bloques("tecnologia", _bloques([producto]))
    assert any("aplica_itbms" in error for error in errores)


def test_validacion_rechaza_categoria_no_declarada():
    errores = validar_bloques(
        "tecnologia", _bloques([_producto(categoria="Otra categoria")])
    )
    assert any("no está declarada" in error for error in errores)


def test_validacion_rechaza_nombres_repetidos_entre_bloques():
    bloques = _bloques([_producto()])
    bloques["OTRO"] = {
        "categorias": [],
        "productos": [_producto()],
    }
    errores = validar_bloques("tecnologia", bloques)
    assert any("ya está declarado en PRUEBA" in error for error in errores)


def test_validacion_rechaza_mas_de_veinte_productos():
    productos = [
        _producto(nombre=f"Producto de prueba {indice}") for indice in range(21)
    ]
    errores = validar_bloques("tecnologia", _bloques(productos))
    assert any("máximo es 20" in error for error in errores)


def test_validacion_acepta_imagen_local_y_archivos_vacios():
    bloques = _bloques([_producto(imagen="media/producto.png")])
    assert validar_bloques("tecnologia", bloques) == []
    assert validar_bloques("tecnologia", {}) == []


# ---------------- Cargador ----------------
def test_simulacion_no_escribe(db):
    resumen = cargar(db, "supermercado", _bloques([_producto()]), simular=True)

    assert resumen.creados == 1
    assert resumen.actualizados == 0
    assert db.scalars(select(Producto)).all() == []
    assert db.scalars(select(Categoria)).all() == []


def test_carga_crea_actualiza_y_no_reinicia_stock(db):
    bloques_iniciales = _bloques([_producto()])

    primero = cargar(db, "supermercado", bloques_iniciales)
    db.commit()
    assert primero.creados == 1
    assert primero.actualizados == 0

    producto = db.scalars(select(Producto)).one()
    categoria = db.get(Categoria, producto.categoria_id)
    assert categoria.sector == SectorEmpresa.SUPERMERCADO
    assert producto.sku == generar_sku("supermercado", "Bebidas", "Producto de prueba")
    assert db.scalars(select(Producto)).all() == [producto]

    inventario = db.get(Inventario, producto.id)
    assert inventario.existencias == Decimal("8.00")
    assert inventario.stock_minimo == Decimal("0.00")
    movimientos = db.scalars(select(MovimientoInventario)).all()
    assert len(movimientos) == 1
    assert movimientos[0].tipo == TipoMovimiento.ENTRADA
    assert movimientos[0].motivo == "carga inicial"
    assert movimientos[0].cuenta_id is None

    # La segunda carga cambia campos, pero no vuelve a tocar el inventario.
    cambios = _bloques(
        [_producto(precio_unidad=Decimal("3.00"), stock_inicial=Decimal("999.00"))]
    )
    segundo = cargar(db, "supermercado", cambios)
    db.commit()
    assert segundo.creados == 0
    assert segundo.actualizados == 1
    db.refresh(producto)
    assert producto.precio_unidad == Decimal("3.00")
    assert db.get(Inventario, producto.id).existencias == Decimal("8.00")
    assert len(db.scalars(select(MovimientoInventario)).all()) == 1

    # Una tercera carga sin cambios no cuenta como actualización.
    tercero = cargar(db, "supermercado", cambios)
    db.commit()
    assert tercero.creados == 0
    assert tercero.actualizados == 0
    assert tercero.omitidos == 1
    assert len(db.scalars(select(Producto)).all()) == 1


def test_sector_se_toma_del_nombre_de_archivo(tmp_path, db):
    sector_turismo, bloques_turismo = _archivo_temporal(
        tmp_path,
        "turismo",
        _bloques(
            [_producto(nombre="Producto compartido", categoria="Paquetes")],
            categoria="Paquetes",
        ),
    )
    sector_tecnologia, bloques_tecnologia = _archivo_temporal(
        tmp_path,
        "tecnologia",
        _bloques(
            [_producto(nombre="Producto compartido", categoria="Accesorios")],
            categoria="Accesorios",
        ),
    )

    cargar(db, sector_turismo, bloques_turismo)
    cargar(db, sector_tecnologia, bloques_tecnologia)
    db.commit()

    productos = db.scalars(select(Producto).order_by(Producto.sku)).all()
    assert len(productos) == 2
    assert [producto.sku[:3] for producto in productos] == ["TEC", "TUR"]
    sectores = {
        producto.sku[:3]: db.get(Categoria, producto.categoria_id).sector
        for producto in productos
    }
    assert sectores == {
        "TEC": SectorEmpresa.TECNOLOGIA,
        "TUR": SectorEmpresa.TURISMO,
    }


def test_solo_bloque_omite_los_demas(db):
    bloques = {
        "PRIMERO": {
            "categorias": [{"nombre": "Bebidas", "descripcion": "Categoría de prueba"}],
            "productos": [_producto(nombre="Producto del primer bloque")],
        },
        "SEGUNDO": {
            "categorias": [{"nombre": "Bebidas", "descripcion": "Categoría de prueba"}],
            "productos": [_producto(nombre="Producto del segundo bloque")],
        },
    }

    resumen = cargar(db, "supermercado", bloques, solo_bloque="PRIMERO")
    db.commit()

    assert resumen.creados == 1
    assert resumen.omitidos == 1
    assert db.scalars(select(Producto)).all()[0].nombre == "Producto del primer bloque"


def test_solo_bloque_reutiliza_categoria_declarada_en_otro_bloque(db):
    bloques = {
        "PRIMERO": {
            "categorias": [
                {"nombre": "Bebidas", "descripcion": "Categoría de prueba"}
            ],
            "productos": [_producto(nombre="Producto del primer bloque")],
        },
        "SEGUNDO": {
            "categorias": [],
            "productos": [_producto(nombre="Producto del segundo bloque")],
        },
    }

    cargar(db, "supermercado", bloques, solo_bloque="PRIMERO")
    resumen = cargar(db, "supermercado", bloques, solo_bloque="SEGUNDO")
    db.commit()

    assert resumen.creados == 1
    assert len(db.scalars(select(Categoria)).all()) == 1
    assert len(db.scalars(select(Producto)).all()) == 2


def test_preparar_no_escribe_y_detecta_categoria_de_otro_sector(db):
    categoria_ajena = Categoria(nombre="Bebidas", sector=SectorEmpresa.TURISMO)
    db.add(categoria_ajena)
    db.flush()

    plan = preparar(db, "supermercado", _bloques([_producto()]))

    assert plan.cambios == []
    assert any("ya existe en el sector" in error for error in plan.errores)
    assert db.scalars(select(Producto)).all() == []
