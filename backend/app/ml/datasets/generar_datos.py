"""Datos de EJEMPLO para los módulos 2, 3 y 4 del ML (Equipo ML).

Genera ~1.000 facturas sinteticas en 24-36 meses con tendencia y
estacionalidad, mas catalogo, pedidos y etiquetas de anomalías.
Nada de datos reales: todo va marcado con "[DATOS DE EJEMPLO]" y
"es_ejemplo": true.

Salida: backend/app/ml/datasets/generados/ (CSV versionados).
Si el entorno define FACTURA_HMAC_KEY se respeta; para regenerar los CSV
sin cambiar los códigos de verificación, correr sin esa variable.
  - facturas_ejemplo.csv
  - lineas_factura_ejemplo.csv
  - etiquetas_anomalias.csv   (ground truth de los casos raros)

Uso:
  python -m app.ml.datasets.generar_datos            # genera los CSV
  python -m app.ml.datasets.generar_datos --validar  # valida los CSV
  python -m app.ml.datasets.generar_datos --cantidad 200 --salida <dir>
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import sys
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.models import (  # noqa: E402
    CobrarPor,
    CondicionPago,
    EstadoFactura,
    EstadoPedido,
    TipoEmpaque,
)
from app.services.totales import aplicar_totales, calcular_monto_linea  # noqa: E402
from app.services.verificacion import generar_codigo_verificacion  # noqa: E402

# Clave de PRUEBA solo para firmar datos de ejemplo. Nunca una clave real:
# si el entorno ya define FACTURA_HMAC_KEY se respeta ese valor.
os.environ.setdefault(
    "FACTURA_HMAC_KEY", "ML-DATOS-DE-EJEMPLO-NO-SECRETA-0000"
)

SEMILLA = 20261126
HOY = date(2026, 11, 26)
MESES_HISTORIA = 30  # dentro del rango acordado de 24 a 36 meses
SALIDA = Path(__file__).resolve().parent / "generados"
CENTAVOS = Decimal("0.01")
MARCA_EJEMPLO = "[DATOS DE EJEMPLO]"

CANTIDAD_FACTURAS = 1000
CANTIDAD_PEDIDOS = 400
CANTIDAD_PRODUCTOS = 45
CANTIDAD_CLIENTES = 30
CANTIDAD_CATEGORIAS = 6

# Mismo formato que services/serie.py: FAC-AAAA-0001
PREFIJO_FACTURA = "FAC"

FACTURA_CAMPOS = [
    "id", "numero_serie", "codigo_verificacion", "fecha",
    "cliente_nombre", "cliente_ruc", "mostrar_ruc", "cliente_direccion",
    "cliente_telefono", "cliente_correo", "sucursal", "vendedor",
    "orden_compra", "condicion_pago", "portes", "notas",
    "subtotal", "descuento_total", "base_gravada", "base_exenta",
    "itbms", "total", "estado", "fecha_creacion", "fecha_anulacion",
    "es_ejemplo", "caso_raro",
]

LINEA_CAMPOS = [
    "id", "factura_id", "orden", "descripcion", "codigo_barras",
    "categoria", "cantidad", "precio_unitario", "precio_unidad",
    "descuento_pct", "gravada", "unidades_por_caja", "cobrar_por",
    "monto", "producto_id", "es_ejemplo",
]

PEDIDO_CAMPOS = [
    "id", "cliente_id", "estado", "total_estimado", "notas",
    "factura_generada_id", "fecha_creacion", "fecha_actualizacion",
    "es_ejemplo", "caso_raro",
]

LINEA_PEDIDO_CAMPOS = [
    "id", "pedido_id", "producto_id", "tipo_empaque", "cantidad",
    "subtotal", "orden", "es_ejemplo",
]

ETIQUETA_CAMPOS = ["factura_id", "numero_serie", "tipo_anomalia", "detalle"]

TOTALES_CAMPOS = [
    "subtotal", "descuento_total", "base_gravada",
    "base_exenta", "itbms", "total",
]

# Temporada alta: diciembre-enero y noviembre; baja: febrero-marzo.
# Índice = mes del año (1-12).
ESTACIONALIDAD = {
    1: 1.25, 2: 0.70, 3: 0.75, 4: 0.90, 5: 0.95, 6: 1.00,
    7: 1.00, 8: 0.95, 9: 1.00, 10: 1.10, 11: 1.30, 12: 1.35,
}

CATEGORIAS = ["Bebidas", "Snacks", "Limpieza", "Papeleria", "Congelados", "Hogar"]

NOMBRES_CLIENTES = [
    "Distribuidora Norte", "Mercado Central", "Tienda La Esquina",
    "Supermercado Delta", "Comercial Sur", "Abarrotes Roma",
    "Farmacia Vida", "Restaurante Sol", "Minimarket 24", "Grupo Andino",
    "Colmado El Sol", "Deli EXPRESS", "Super Rios", "Abarrotes La 40",
    "Comercial Pacífico", "Tienda Mi Casita", "Autoservicio Uno",
    "Distribuidora Sur", "Minimarket La Esquina", "Comercial Andino",
    "Supermercado Real", "Colmado Don Juan", "Deli Norte",
    "Abarrotes El Trébol", "Comercial La 21", "Restaurante La Costa",
    "Farmacia Central", "Tienda El Ahorro", "Super El Milagro",
    "Comercial Express 24",
]

# nombre, sku, precio_caja, precio_unidad, unidades_por_caja, aplica_itbms
_PRODUCTOS_BASE = [
    ("Agua mineral 500 ml", "BEB-001", "48.00", "1.00", 12, True),
    ("Refresco naranja 1.5 L", "BEB-002", "72.00", "3.00", 6, True),
    ("Jugo de manzana 1 L", "BEB-003", "60.00", "2.50", 6, True),
    ("Café molido 250 g", "BEB-004", "90.00", "3.75", 6, True),
    ("Té en bolsitas x25", "BEB-005", "55.00", "2.20", 10, True),
    ("Gaseosa cola 2 L", "BEB-006", "66.00", "5.50", 6, True),
    ("Leche entera 1 L", "BEB-007", "42.00", "3.50", 12, True),
    ("Yogurt natural 170 g", "BEB-008", "78.00", "6.50", 12, True),
    ("Galletas de soda", "SNA-001", "36.00", "0.75", 12, True),
    ("Papas fritas naturales", "SNA-002", "54.00", "2.25", 6, True),
    ("Maní salado 200 g", "SNA-003", "60.00", "5.00", 12, True),
    ("Chocolate con leche 100 g", "SNA-004", "72.00", "6.00", 12, True),
    ("Detergente liquido 1 L", "LIM-001", "96.00", "4.00", 6, True),
    ("Papel higienico x12", "LIM-002", "120.00", "10.00", 1, True),
    ("Jabón de baño x4", "LIM-003", "48.00", "2.00", 24, True),
    ("Cloro desinfectante 1 L", "LIM-004", "54.00", "4.50", 12, True),
    ("Esponja multiuso x6", "LIM-005", "30.00", "1.25", 24, True),
    ("Cuaderno A4 100 hojas", "PAP-001", "30.00", "1.25", 12, True),
    ("Bolígrafo azul x10", "PAP-002", "45.00", "0.90", 10, True),
    ("Resma papel bond", "PAP-003", "150.00", "6.25", 24, True),
    ("Marcador permanente x3", "PAP-004", "24.00", "1.00", 24, True),
    ("Carpeta con gancho", "PAP-005", "36.00", "1.50", 24, True),
    ("Helado vainilla 1 L", "CON-001", "84.00", "7.00", 4, True),
    ("Pasta dental 100 ml", "HOG-001", "66.00", "5.50", 12, True),
    ("Jabón de plato 750 ml", "HOG-002", "84.00", "3.50", 6, True),
    ("Servilletas desechables", "HOG-003", "45.00", "1.88", 24, True),
    ("Fósforos x10", "HOG-004", "12.00", "0.50", 20, False),
    ("Bolsa de basura x20", "HOG-005", "60.00", "2.50", 24, True),
    ("Insecticida aerosol", "HOG-006", "96.00", "4.00", 6, True),
    ("Arroz 5 lb", "ALM-001", "180.00", "15.00", 12, True),
    ("Azúcar 5 lb", "ALM-002", "150.00", "12.50", 12, True),
    ("Aceite vegetal 1 L", "ALM-003", "72.00", "3.00", 6, True),
    ("Harina de trigo 2 lb", "ALM-004", "90.00", "7.50", 12, True),
    ("Frijoles 2 lb", "ALM-005", "120.00", "10.00", 12, True),
    ("Atún en lata x12", "ALM-006", "168.00", "7.00", 24, True),
    ("Leche en polvo 400 g", "ALM-007", "210.00", "8.75", 24, True),
    ("Galletas dulces surtidas", "SNA-005", "66.00", "1.38", 48, True),
    ("Cereal para niños 400 g", "ALM-008", "180.00", "7.50", 24, True),
    ("Puré de tomate 400 g", "ALM-009", "42.00", "1.75", 24, True),
    ("Mantequilla 250 g", "ALM-010", "132.00", "5.50", 24, True),
    ("Jabón en polvo 800 g", "LIM-006", "240.00", "10.00", 24, True),
    ("Suavizante 900 ml", "LIM-007", "150.00", "6.25", 24, True),
    ("Almohada desechable", "HOG-007", "90.00", "3.75", 24, True),
    ("Jugo de piña 1 L", "BEB-009", "54.00", "4.50", 12, True),
    ("Agua saborizada 500 ml", "BEB-010", "60.00", "5.00", 12, True),
    ("Refresco uva 500 ml", "BEB-011", "48.00", "2.00", 6, True),
]

# Clientes que acumulan anulaciones a propósito (caso raro documentado).
CLIENTES_MUCHAS_ANULACIONES = {0, 4, 12}


def d(valor):
    """Decimal a 2 decimales, sin depender de float."""
    return Decimal(str(valor)).quantize(CENTAVOS)


def money(valor):
    return str(d(valor))


def _estacionalidad(mes):
    return ESTACIONALIDAD.get(mes, 1.0)


def construir_catalogo():
    """Catálogo simulado: ~6 categorías, ~45 productos, 30 clientes."""
    categorias = [
        {"id": idx, "nombre": nombre, "es_ejemplo": True}
        for idx, nombre in enumerate(CATEGORIAS, start=1)
    ]
    productos = []
    for idx, (nombre, sku, precio_caja, precio_unidad, unidades, itbms) in (
        enumerate(_PRODUCTOS_BASE, start=1)
    ):
        productos.append(
            {
                "id": idx,
                "categoria_id": (idx - 1) % len(CATEGORIAS) + 1,
                "nombre": nombre,
                "sku": sku,
                "codigo_barras": f"EJ{sku}",
                "descripcion_corta": f"Producto de ejemplo {sku}",
                "imagen": None,
                "precio_caja": money(precio_caja),
                "precio_media_caja": money(d(precio_caja) / 2),
                "permite_media_caja": True,
                "precio_unidad": money(precio_unidad),
                "precio_consumidor": money(d(precio_unidad) * Decimal("1.10")),
                "unidades_por_caja": unidades,
                "aplica_itbms": itbms,
                "estado_activo": True,
                "fecha_creacion": f"{HOY - timedelta(days=900)}T08:00:00",
                "fecha_actualizacion": f"{HOY - timedelta(days=1)}T08:00:00",
                "es_ejemplo": True,
            }
        )
    clientes = [
        {
            "id": idx,
            "nombre_empresa": nombre,
            "ruc": f"RUC-EJ-{idx:06d}",
            "email_contacto": f"contacto{idx}@ejemplo.local",
            "telefono": f"6000{idx:04d}",
            "direccion": f"Direccion de ejemplo {idx}",
            "fecha_registro": f"{HOY - timedelta(days=1200)}T08:00:00",
            "activo": True,
            "es_ejemplo": True,
        }
        for idx, nombre in enumerate(NOMBRES_CLIENTES, start=1)
    ]
    return {"categorias": categorias, "productos": productos, "clientes": clientes}


def _siguiente_numero_factura(db, anio, contadores):
    """FAC-AAAA-0001.

    Si hay una sesión Postgres real usa services/serie.py (atómico con
    FOR UPDATE). Sin sesión (offline, SQLite, tests) usa un contador
    determinista local con el mismo formato y sin duplicados.
    """
    if db is not None:
        try:
            from app.services.serie import siguiente_numero_factura as _srv

            return _srv(db, anio)
        except Exception:
            pass  # fallback determinista documentado
    ultimo = contadores.get(anio, 0) + 1
    contadores[anio] = ultimo
    return f"{PREFIJO_FACTURA}-{anio}-{ultimo:04d}"


def _fecha_con_temporalidad(rng, meses):
    """Fecha dentro de los últimos `meses` meses, sesgada por temporada."""
    pesos = []
    for m in range(meses):
        fecha_m = HOY - timedelta(days=30 * m + rng.randint(0, 20))
        pesos.append(_estacionalidad(fecha_m.month))
    indice = rng.choices(range(meses), weights=pesos, k=1)[0]
    fecha = HOY - timedelta(days=indice * 30 + rng.randint(0, 27))
    # Nunca antes del inicio de la ventana ni en el futuro.
    limite = HOY - timedelta(days=meses * 30)
    if fecha < limite:
        fecha = limite + timedelta(days=rng.randint(0, 10))
    return fecha


def _objetivo_total(rng, fecha, meses):
    """Total objetivo con tendencia lineal + estacionalidad mensual."""
    meses_atras = max(0, (HOY - fecha).days // 30)
    tendencia = 1.0 + 0.6 * (meses - meses_atras) / meses  # crece ~60 %
    temporada = _estacionalidad(fecha.month)
    return Decimal("350.00") * d(tendencia) * d(temporada) * d(
        rng.uniform(0.5, 1.8)
    )


def _nueva_linea(rng, producto, orden, objetivo, caso):
    """Una línea de factura como dict; `monto` lo fija aplicar_totales."""
    precio_caja = d(producto["precio_caja"])
    precio_unidad = d(producto["precio_unidad"])
    cobrar_por = rng.choice([e.value for e in CobrarPor])
    precio = precio_caja if cobrar_por == CobrarPor.CAJA.value else precio_unidad

    # Cantidad para acercarse al objetivo de la línea.
    cantidad = max(Decimal("1"), d(objetivo / max(precio, CENTAVOS)))
    cantidad = min(cantidad, Decimal("500"))
    if caso == "total_muy_alto" and orden == 1:
        cantidad = Decimal("250")

    # El caso raro tiene que notarse de verdad: siempre por encima del 30 %.
    # Un solo choice por línea mantiene la semilla y el resto del dataset igual.
    opciones = (40, 45, 50) if caso == "descuento_alto" else (0, 0, 0, 5, 10, 15)
    descuento_pct = d(rng.choice(opciones))
    gravada = producto["aplica_itbms"] and caso != "sin_itbms"

    return {
        "orden": orden,
        "descripcion": producto["nombre"],
        "codigo_barras": producto["codigo_barras"],
        "categoria": CATEGORIAS[producto["categoria_id"] - 1],
        "cantidad": money(cantidad),
        "precio_unitario": money(precio),
        "precio_unidad": money(precio_unidad),
        "descuento_pct": money(descuento_pct),
        "gravada": gravada,
        "unidades_por_caja": producto["unidades_por_caja"],
        "cobrar_por": cobrar_por,
        "producto_id": producto["id"],
        "es_ejemplo": True,
    }


def _caso_raro(i, cliente_idx, anuladas_previas, rng):
    """Casos inyectados a propósito para el ground truth de anomalías."""
    if i % 211 == 0:
        return "total_muy_alto"
    if i % 197 == 0:
        return "descuento_alto"
    if i % 181 == 0:
        return "sin_itbms"
    if i % 167 == 0:
        return "cliente_sin_ruc"
    if cliente_idx in CLIENTES_MUCHAS_ANULACIONES and anuladas_previas < 6:
        if rng.random() < 0.35:
            return "factura_anulada"
    elif i % 149 == 0:
        return "factura_anulada"
    return None


def construir_facturas(productos, clientes, n, rng, db=None, contadores=None,
                       inicio_id=1, inicio_linea=1, incluir_series_dup=False):
    """Construye n facturas con líneas; devuelve (facturas, etiquetas).

    `contadores` mapea año -> último número usado (fallback offline).
    `incluir_series_dup` habilita el caso raro 'serie_duplicada': la
    factura repite el numero_serie de la anterior y queda etiquetada.
    """
    contadores = contadores if contadores is not None else {}
    facturas = []
    etiquetas = []
    anuladas_por_cliente = Counter()
    serie_previa = None
    fid = inicio_id
    lid = inicio_linea

    for i in range(n):
        cliente_idx = rng.randrange(len(clientes))
        cliente = clientes[cliente_idx]
        caso = _caso_raro(i, cliente_idx, anuladas_por_cliente[cliente_idx], rng)
        anulada = caso == "factura_anulada"
        fecha = _fecha_con_temporalidad(rng, MESES_HISTORIA)
        objetivo = _objetivo_total(rng, fecha, MESES_HISTORIA)

        lineas = []
        n_lineas = rng.randint(1, 4)
        share = objetivo / n_lineas
        for orden in range(1, n_lineas + 1):
            producto = rng.choice(productos)
            linea = _nueva_linea(rng, producto, orden, share, caso)
            lineas.append(linea)

        factura = {
            "id": fid,
            "numero_serie": "",  # se asigna abajo
            "codigo_verificacion": "",
            "fecha": fecha.isoformat(),
            "cliente_nombre": cliente["nombre_empresa"],
            "cliente_ruc": (
                None if caso == "cliente_sin_ruc" else cliente["ruc"]
            ),
            "mostrar_ruc": caso != "cliente_sin_ruc",
            "cliente_direccion": cliente["direccion"],
            "cliente_telefono": cliente["telefono"],
            "cliente_correo": cliente["email_contacto"],
            "sucursal": "Sucursal Ejemplo",
            "vendedor": "Vendedor Ejemplo",
            "orden_compra": f"OC-EJ-{i:05d}",
            "condicion_pago": rng.choice([e.value for e in CondicionPago]),
            "portes": money(rng.choice(["0.00", "0.00", "5.00", "12.50"])),
            "notas": f"{MARCA_EJEMPLO} - {caso or 'caso normal'}",
            "estado": (
                EstadoFactura.ANULADA.value if anulada
                else EstadoFactura.EMITIDA.value
            ),
            "fecha_creacion": f"{fecha}T08:{rng.randint(0, 59):02d}:00",
            "fecha_anulacion": (
                f"{fecha + timedelta(days=1)}T09:00:00" if anulada else None
            ),
            "es_ejemplo": True,
            "caso_raro": caso,
            "lineas": lineas,
        }

        # Totales reales vía servicio oficial (Decimal, ROUND_HALF_UP).
        totales = aplicar_totales(factura)
        factura["subtotal"] = money(totales["subtotal"])
        for campo in TOTALES_CAMPOS:
            factura[campo] = money(totales[campo])

        # Número de serie y código de verificación reales.
        anio = fecha.year
        factura["numero_serie"] = _siguiente_numero_factura(
            db, anio, contadores
        )
        if incluir_series_dup and i > 0 and i % 89 == 0:
            factura["numero_serie"] = serie_previa
            etiquetas.append({
                "factura_id": fid,
                "numero_serie": factura["numero_serie"],
                "tipo_anomalia": "serie_duplicada",
                "detalle": f"Repite la serie de la factura {fid - 1}",
            })
            factura["caso_raro"] = "serie_duplicada"
            factura["notas"] += " - serie_duplicada"
        serie_previa = factura["numero_serie"]

        factura["codigo_verificacion"] = generar_codigo_verificacion(
            factura["numero_serie"],
            totales["total"],
            factura["cliente_ruc"] or "",
        )

        for linea in lineas:
            linea["factura_id"] = fid
            linea["id"] = lid
            # monto ya lo escribió aplicar_totales; por si acaso, recalcular.
            if linea.get("monto") is None:
                linea["monto"] = money(calcular_monto_linea(linea))
            else:
                linea["monto"] = money(d(linea["monto"]))
            lid += 1

        facturas.append(factura)
        if caso:
            etiquetas.append({
                "factura_id": fid,
                "numero_serie": factura["numero_serie"],
                "tipo_anomalia": caso,
                "detalle": f"Caso inyectado: {caso}",
            })
        if anulada:
            anuladas_por_cliente[cliente_idx] += 1
        fid += 1

    return facturas, etiquetas


def construir_pedidos(clientes, productos, facturas, rng, n=CANTIDAD_PEDIDOS):
    """Pedidos B2B de ejemplo ligados a facturas 'facturado'."""
    pedidos = []
    lineas_pedido = []
    facturables = [f["id"] for f in facturas]
    lid = 1

    for i in range(1, n + 1):
        estado = (
            EstadoPedido.FACTURADO.value
            if i % 3 == 0
            else rng.choice(
                [
                    EstadoPedido.PENDIENTE.value,
                    EstadoPedido.PROCESANDO.value,
                    EstadoPedido.CANCELADO.value,
                ]
            )
        )
        cliente = rng.choice(clientes)
        total_estimado = Decimal("0.00")
        lineas = []
        for orden in range(1, rng.randint(1, 3) + 1):
            producto = rng.choice(productos)
            cantidad = d(rng.choice([1, 2, 4, 8]))
            tipo = rng.choice([e.value for e in TipoEmpaque])
            precio = d(
                producto["precio_caja"]
                if tipo == TipoEmpaque.CAJA.value
                else producto["precio_unidad"]
            )
            subtotal = d(cantidad * precio)
            total_estimado += subtotal
            lineas.append({
                "id": lid,
                "pedido_id": i,
                "producto_id": producto["id"],
                "tipo_empaque": tipo,
                "cantidad": money(cantidad),
                "subtotal": money(subtotal),
                "orden": orden,
                "es_ejemplo": True,
            })
            lineas_pedido.append(lineas[-1])
            lid += 1

        pedidos.append({
            "id": i,
            "cliente_id": cliente["id"],
            "estado": estado,
            "total_estimado": money(total_estimado),
            "notas": f"{MARCA_EJEMPLO} - caso normal",
            "factura_generada_id": (
                rng.choice(facturables) if estado == EstadoPedido.FACTURADO.value
                else None
            ),
            "fecha_creacion": f"{HOY - timedelta(days=i)}T10:00:00",
            "fecha_actualizacion": f"{HOY - timedelta(days=i)}T11:00:00",
            "es_ejemplo": True,
            "caso_raro": None,
            "lineas": lineas,
        })
    return pedidos, lineas_pedido


def construir_dataset(n_facturas=CANTIDAD_FACTURAS, n_pedidos=CANTIDAD_PEDIDOS,
                      semilla=SEMILLA, db=None, contadores=None,
                      inicio_id=1, inicio_linea=1):
    """Dataset completo y determinista: misma semilla -> mismos datos."""
    rng = random.Random(semilla)
    catalogo = construir_catalogo()
    facturas, etiquetas = construir_facturas(
        catalogo["productos"], catalogo["clientes"], n_facturas, rng,
        db=db, contadores=contadores,
        inicio_id=inicio_id, inicio_linea=inicio_linea,
        incluir_series_dup=True,
    )
    pedidos, lineas_pedido = construir_pedidos(
        catalogo["clientes"], catalogo["productos"], facturas, rng, n=n_pedidos
    )
    return {
        "semilla": semilla,
        "catalogo": catalogo,
        "facturas": facturas,
        "lineas_factura": [
            linea for f in facturas for linea in f["lineas"]
        ],
        "etiquetas_anomalias": etiquetas,
        "pedidos": pedidos,
        "lineas_pedido": lineas_pedido,
    }


def _fila(campo_valores, campos):
    return {campo: campo_valores.get(campo, "") for campo in campos}


def _escribir_csv(ruta, campos, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=campos, lineterminator="\n")
        writer.writeheader()
        for fila in filas:
            writer.writerow(_fila(fila, campos))


def _aplanar_facturas(facturas):
    filas_facturas = []
    filas_lineas = []
    for factura in facturas:
        filas_facturas.append({k: v for k, v in factura.items() if k != "lineas"})
        for linea in factura.get("lineas", []):
            filas_lineas.append(dict(linea))
    return filas_facturas, filas_lineas


def escribir_csvs(dataset, directorio=SALIDA):
    """Escribe los 4 CSV en `directorio` (ignorado por Git)."""
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)

    filas_facturas, filas_lineas = _aplanar_facturas(dataset["facturas"])

    # Pedidos: sus líneas van aplanadas igual que las de factura.
    filas_pedidos, filas_lineas_pedido = [], []
    for pedido in dataset.get("pedidos", []):
        filas_pedidos.append({k: v for k, v in pedido.items() if k != "lineas"})
        for linea in pedido.get("lineas", []):
            filas_lineas_pedido.append(dict(linea))

    archivos = {
        "facturas_ejemplo.csv": (FACTURA_CAMPOS, filas_facturas),
        "lineas_factura_ejemplo.csv": (LINEA_CAMPOS, filas_lineas),
        "pedidos_ejemplo.csv": (PEDIDO_CAMPOS, filas_pedidos),
        "lineas_pedido_ejemplo.csv": (LINEA_PEDIDO_CAMPOS, filas_lineas_pedido),
        "etiquetas_anomalias.csv": (
            ETIQUETA_CAMPOS, dataset["etiquetas_anomalias"]
        ),
    }
    escritos = []
    for nombre, (campos, filas) in archivos.items():
        ruta = directorio / nombre
        _escribir_csv(ruta, campos, filas)
        escritos.append(ruta)
    return escritos


def _leer_csv(ruta):
    with open(ruta, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _a_bool(valor):
    """'True'/'False'/1/0 -> bool; lo que llega de CSV es texto."""
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in ("true", "1", "yes", "si")


def leer_dataset_csv(directorio=SALIDA):
    """Lee los CSV generados y reconstruye facturas con sus líneas."""
    directorio = Path(directorio)
    facturas_raw = _leer_csv(directorio / "facturas_ejemplo.csv")
    lineas_raw = _leer_csv(directorio / "lineas_factura_ejemplo.csv")
    etiquetas_raw = _leer_csv(directorio / "etiquetas_anomalias.csv")

    lineas_por_factura = {}
    for linea in lineas_raw:
        lineas_por_factura.setdefault(linea["factura_id"], []).append(linea)

    facturas = []
    for fila in facturas_raw:
        factura = dict(fila)
        factura["mostrar_ruc"] = _a_bool(fila.get("mostrar_ruc"))
        factura["es_ejemplo"] = _a_bool(fila.get("es_ejemplo"))
        factura["lineas"] = sorted(
            lineas_por_factura.get(fila["id"], []),
            key=lambda l: int(l["orden"]),
        )
        for linea in factura["lineas"]:
            linea["gravada"] = _a_bool(linea.get("gravada"))
            linea["es_ejemplo"] = _a_bool(linea.get("es_ejemplo"))
        facturas.append(factura)

    return facturas, etiquetas_raw


def validar_dataset(facturas, etiquetas=None, meses_min=24, meses_max=36,
                    hoy=None):
    """Valida cuadre de totales, series únicas y rango de fechas.

    Devuelve una lista de errores (vacía = dataset válido). Las series
    duplicadas solo se aceptan si aparecen en `etiquetas` con tipo
    'serie_duplicada' (caso inyectado documentado).
    """
    hoy = hoy or HOY
    errores = []
    etiquetas = etiquetas or []
    series_duplicadas_permitidas = {
        e.get("numero_serie") for e in etiquetas
        if "duplicad" in str(e.get("tipo_anomalia", ""))
    }

    conteo_series = Counter(f.get("numero_serie") for f in facturas)
    for serie, veces in conteo_series.items():
        if veces > 1 and serie not in series_duplicadas_permitidas:
            errores.append(
                f"numero_serie duplicado sin etiqueta: {serie} x{veces}"
            )

    limite_min = hoy - timedelta(days=meses_max * 30)
    span_minimo = timedelta(days=meses_min * 30)
    fechas = []

    for factura in facturas:
        fid = factura.get("id", "?")
        # Fechas dentro del rango esperado.
        try:
            fecha = date.fromisoformat(str(factura["fecha"])[:10])
            fechas.append(fecha)
            if fecha < limite_min or fecha > hoy:
                errores.append(
                    f"factura {fid}: fecha {fecha} fuera de rango "
                    f"({limite_min} a {hoy})"
                )
        except (KeyError, ValueError) as exc:
            errores.append(f"factura {fid}: fecha inválida {exc}")
            continue

        # Cuadre de totales contra los servicios reales.
        lineas = factura.get("lineas", [])
        try:
            calculados = aplicar_totales(
                {"lineas": [dict(l) for l in lineas],
                 "portes": factura.get("portes", "0.00")}
            )
        except Exception as exc:
            errores.append(f"factura {fid}: totales no calculables: {exc}")
            continue

        for campo in TOTALES_CAMPOS:
            esperado = d(calculados[campo])
            try:
                real = d(factura.get(campo, "0"))
            except Exception:
                errores.append(f"factura {fid}: {campo} no numérico")
                continue
            if real != esperado:
                errores.append(
                    f"factura {fid}: {campo}={real} esperado {esperado}"
                )

        # Cada monto de línea debe cuadrar con su cálculo.
        for linea in lineas:
            try:
                esperado_linea = calcular_monto_linea(dict(linea))
                real_linea = d(linea.get("monto", "0"))
                if real_linea != esperado_linea:
                    errores.append(
                        f"factura {fid} línea {linea.get('orden')}: "
                        f"monto={real_linea} esperado {esperado_linea}"
                    )
            except Exception as exc:
                errores.append(
                    f"factura {fid} línea {linea.get('orden')}: {exc}"
                )

    if fechas:
        span = max(fechas) - min(fechas)
        if span < span_minimo:
            errores.append(
                f"rango de fechas insuficiente: {span.days} días "
                f"(mínimo ~{span_minimo.days})"
            )

    return errores


def validar_archivos(directorio=SALIDA):
    facturas, etiquetas = leer_dataset_csv(directorio)
    return validar_dataset(facturas, etiquetas)


def anexar_facturas_csv(facturas_nuevas, directorio=SALIDA):
    """Añade facturas (mismo formato interno) a los CSV existentes.

    Asigna `id`/`factura_id` continuando la numeración y deja que la
    validación verifique el dataset combinado. Devuelve los errores de
    `validar_dataset` sobre el resultado completo.
    """
    directorio = Path(directorio)
    facturas, etiquetas = leer_dataset_csv(directorio)

    max_id = max((int(f["id"]) for f in facturas), default=0)
    max_linea = 0
    for f in facturas:
        for linea in f.get("lineas", []):
            max_linea = max(max_linea, int(linea["id"]))

    for nueva in facturas_nuevas:
        max_id += 1
        nueva = dict(nueva)
        nueva["id"] = str(max_id)
        nuevas_lineas = []
        for orden, linea in enumerate(nueva.get("lineas", []), start=1):
            max_linea += 1
            l = dict(linea)
            l["id"] = str(max_linea)
            l["factura_id"] = str(max_id)
            l["orden"] = str(orden)
            nuevas_lineas.append(l)
        nueva["lineas"] = nuevas_lineas
        facturas.append(nueva)

    dataset = {
        "facturas": facturas,
        "etiquetas_anomalias": etiquetas,
        "pedidos": [],
        "lineas_pedido": [],
    }
    # Reescribe conservando pedidos existentes.
    pedidos_raw = _leer_csv(directorio / "pedidos_ejemplo.csv")
    lineas_pedido_raw = _leer_csv(directorio / "lineas_pedido_ejemplo.csv")
    pedidos = []
    lp_por_pedido = {}
    for l in lineas_pedido_raw:
        lp_por_pedido.setdefault(l["pedido_id"], []).append(l)
    for p in pedidos_raw:
        p = dict(p)
        p["lineas"] = lp_por_pedido.get(p["id"], [])
        pedidos.append(p)
    dataset["pedidos"] = pedidos
    dataset["lineas_pedido"] = lineas_pedido_raw

    escribir_csvs(dataset, directorio)
    return validar_dataset(facturas, etiquetas)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validar", action="store_true",
                        help="Valida los CSV existentes en vez de generar")
    parser.add_argument("--cantidad", type=int, default=CANTIDAD_FACTURAS,
                        help="Número de facturas a generar")
    parser.add_argument("--semilla", type=int, default=SEMILLA)
    parser.add_argument("--salida", type=Path, default=SALIDA)
    args = parser.parse_args(argv)

    if args.validar:
        errores = validar_archivos(args.salida)
        if errores:
            print(f"VALIDACIÓN FALLIDA: {len(errores)} error(es)")
            for error in errores[:50]:
                print(f"  - {error}")
            return 1
        print(f"VALIDACIÓN OK: {args.salida}")
        return 0

    dataset = construir_dataset(
        n_facturas=args.cantidad, semilla=args.semilla
    )
    archivos = escribir_csvs(dataset, args.salida)

    n_lineas = len(dataset["lineas_factura"])
    print(f"Semilla: {dataset['semilla']}")
    print(f"Facturas: {len(dataset['facturas'])} | lineas: {n_lineas}")
    print(f"Pedidos: {len(dataset['pedidos'])} | "
          f"lineas: {len(dataset['lineas_pedido'])}")
    print(f"Etiquetas de anomalías: {len(dataset['etiquetas_anomalias'])}")
    for archivo in archivos:
        print(f"  {archivo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
