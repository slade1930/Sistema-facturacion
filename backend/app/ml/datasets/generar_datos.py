"""Datos de EJEMPLO para los módulos 2, 3 y 4 del ML (Equipo 1).

Genera facturas y pedidos sintéticos con casos raros inyectados.
Nada de datos reales. La salida va a backend/app/ml/datos_generados/,
carpeta que ya está ignorada por Git.
"""
from __future__ import annotations

import json
import random
import sys
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

SEMILLA = 20261126
HOY = date(2026, 11, 26)
SALIDA = Path(__file__).resolve().parents[1] / "datos_generados"
CENTAVOS = Decimal("0.01")
CANTIDAD_FACTURAS = 60
CANTIDAD_PEDIDOS = 40

rng = random.Random(SEMILLA)


def d(valor):
    """Decimal a 2 decimales, sin depender de float."""
    return Decimal(str(valor)).quantize(CENTAVOS)


def money(valor):
    return str(d(valor))


def caso_raro(i):
    """Casos inyectados para anomalías, pronóstico y recomendaciones."""
    if i % 17 == 0:
        return "total_muy_alto"
    if i % 13 == 0:
        return "descuento_alto"
    if i % 11 == 0:
        return "sin_itbms"
    if i % 7 == 0:
        return "cliente_sin_ruc"
    if i % 5 == 0:
        return "factura_anulada"
    return None


CATEGORIAS = ["Bebidas", "Snacks", "Limpieza", "Papeleria", "Congelados"]

# nombre, sku, precio_caja, precio_unidad, unidades_por_caja
PRODUCTOS = [
    ("Agua mineral 500 ml", "BEB-001", "48.00", "1.00", 12),
    ("Refresco naranja 1.5 L", "BEB-002", "72.00", "3.00", 6),
    ("Jugo de manzana 1 L", "BEB-003", "60.00", "2.50", 6),
    ("Galletas de soda", "SNA-001", "36.00", "0.75", 12),
    ("Papas fritas naturales", "SNA-002", "54.00", "2.25", 6),
    ("Detergente liquido 1 L", "LIM-001", "96.00", "4.00", 6),
    ("Papel higienico x12", "LIM-002", "120.00", "10.00", 1),
    ("Cuaderno A4 100 hojas", "PAP-001", "30.00", "1.25", 12),
    ("Boligrafo azul x10", "PAP-002", "45.00", "0.90", 10),
    ("Helado vainilla 1 L", "CON-001", "84.00", "7.00", 4),
]

NOMBRES_CLIENTES = [
    "Distribuidora Norte",
    "Mercado Central",
    "Tienda La Esquina",
    "Supermercado Delta",
    "Comercial Sur",
    "Abarrotes Roma",
    "Farmacia Vida",
    "Restaurante Sol",
    "Minimarket 24",
    "Grupo Andino",
]


def construir_catalogo():
    categorias = [
        {"id": idx, "nombre": nombre, "es_ejemplo": True}
        for idx, nombre in enumerate(CATEGORIAS, start=1)
    ]

    productos = []
    for idx, (nombre, sku, precio_caja, precio_unidad, unidades) in enumerate(
        PRODUCTOS, start=1
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
                "aplica_itbms": idx % 3 != 0,
                "estado_activo": True,
                "fecha_creacion": f"{HOY - timedelta(days=90)}T08:00:00",
                "fecha_actualizacion": f"{HOY - timedelta(days=1)}T08:00:00",
                "es_ejemplo": True,
            }
        )

    clientes = []
    for idx, nombre in enumerate(NOMBRES_CLIENTES, start=1):
        clientes.append(
            {
                "id": idx,
                "nombre_empresa": nombre,
                "ruc": f"RUC-EJ-{idx:06d}",
                "email_contacto": f"contacto{idx}@ejemplo.local",
                "telefono": f"6000{idx:04d}",
                "direccion": f"Direccion de ejemplo {idx}",
                "fecha_registro": f"{HOY - timedelta(days=120)}T08:00:00",
                "activo": True,
                "es_ejemplo": True,
            }
        )

    return {
        "es_ejemplo": True,
        "semilla": SEMILLA,
        "categorias": categorias,
        "productos": productos,
        "clientes": clientes,
    }


def construir_facturas(productos):
    facturas = []
    todas_las_lineas = []
    fid = 1
    lid = 1

    for i in range(1, CANTIDAD_FACTURAS + 1):
        caso = caso_raro(i)
        anulada = caso == "factura_anulada"
        fecha = HOY - timedelta(days=(i * 3) % 180)
        cliente = rng.choice(NOMBRES_CLIENTES)
        lineas = []

        subtotal = Decimal("0.00")
        descuento_total = Decimal("0.00")
        base_gravada = Decimal("0.00")
        base_exenta = Decimal("0.00")

        for orden in range(1, rng.randint(1, 4) + 1):
            producto = rng.choice(productos)
            cantidad = rng.choice([1, 2, 3, 5, 10])
            if caso == "total_muy_alto" and orden == 1:
                cantidad = 250
            precio = d(producto["precio_unidad"])
            descuento_pct = d(
                rng.choice([0, 0, 0, 5, 10, 30 if caso == "descuento_alto" else 15])
            )
            bruto = d(cantidad * precio)
            monto = d(bruto * (Decimal("1") - descuento_pct / Decimal("100")))
            descuento = d(bruto - monto)
            gravada = caso != "sin_itbms" and producto["aplica_itbms"]

            subtotal += bruto
            descuento_total += descuento
            if gravada:
                base_gravada += monto
            else:
                base_exenta += monto

            lineas.append(
                {
                    "id": lid,
                    "factura_id": fid,
                    "orden": orden,
                    "descripcion": producto["nombre"],
                    "codigo_barras": producto["codigo_barras"],
                    "categoria": CATEGORIAS[producto["categoria_id"] - 1],
                    "cantidad": money(cantidad),
                    "precio_unitario": money(precio),
                    "precio_unidad": money(precio),
                    "descuento_pct": money(descuento_pct),
                    "gravada": gravada,
                    "unidades_por_caja": producto["unidades_por_caja"],
                    "cobrar_por": rng.choice([e.value for e in CobrarPor]),
                    "monto": money(monto),
                    "producto_id": producto["id"],
                    "es_ejemplo": True,
                }
            )
            todas_las_lineas.append(lineas[-1])
            lid += 1

        portes = d("0.00")
        itbms = d("0.00") if caso == "sin_itbms" else d(base_gravada * Decimal("0.07"))
        total = d(subtotal - descuento_total + portes + itbms)

        facturas.append(
            {
                "id": fid,
                "numero_serie": f"FAC-EJ-2026-{i:04d}",
                "codigo_verificacion": f"CVEJ{i:06d}",
                "fecha": fecha.isoformat(),
                "cliente_nombre": cliente,
                "cliente_ruc": None if caso == "cliente_sin_ruc" else f"RUC-EJ-{i % 10 + 1:06d}",
                "mostrar_ruc": caso != "cliente_sin_ruc",
                "cliente_direccion": f"Direccion de ejemplo {i}",
                "cliente_telefono": f"6000{i:04d}",
                "cliente_correo": f"cliente{i}@ejemplo.local",
                "sucursal": "Sucursal Ejemplo",
                "vendedor": "Vendedor Ejemplo",
                "orden_compra": f"OC-EJ-{i:04d}",
                "condicion_pago": rng.choice([e.value for e in CondicionPago]),
                "portes": money(portes),
                "notas": f"EJEMPLO - {caso or 'caso normal'}",
                "subtotal": money(subtotal),
                "descuento_total": money(descuento_total),
                "base_gravada": money(base_gravada),
                "base_exenta": money(base_exenta),
                "itbms": money(itbms),
                "total": money(total),
                "estado": EstadoFactura.ANULADA.value if anulada else EstadoFactura.EMITIDA.value,
                "fecha_creacion": f"{fecha}T08:00:00",
                "fecha_anulacion": f"{fecha}T09:00:00" if anulada else None,
                "es_ejemplo": True,
                "caso_raro": caso,
                "lineas": lineas,
            }
        )
        fid += 1

    return facturas, todas_las_lineas


def construir_pedidos(clientes, productos, facturas):
    pedidos = []
    todas_las_lineas = []
    pid = 1
    lid = 1

    for i in range(1, CANTIDAD_PEDIDOS + 1):
        caso = caso_raro(i)
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
        factura_id = (
            rng.choice(facturas)["id"] if estado == EstadoPedido.FACTURADO.value else None
        )
        cliente = rng.choice(clientes)
        lineas = []
        total_estimado = Decimal("0.00")

        for orden in range(1, rng.randint(1, 3) + 1):
            producto = rng.choice(productos)
            cantidad = rng.choice([1, 2, 4, 8])
            tipo = rng.choice([e.value for e in TipoEmpaque])
            precio = d(
                producto["precio_caja"]
                if tipo == TipoEmpaque.CAJA.value
                else producto["precio_unidad"]
            )
            subtotal = d(cantidad * precio)
            total_estimado += subtotal
            lineas.append(
                {
                    "id": lid,
                    "pedido_id": pid,
                    "producto_id": producto["id"],
                    "tipo_empaque": tipo,
                    "cantidad": money(cantidad),
                    "subtotal": money(subtotal),
                    "orden": orden,
                    "es_ejemplo": True,
                }
            )
            todas_las_lineas.append(lineas[-1])
            lid += 1

        pedidos.append(
            {
                "id": pid,
                "cliente_id": cliente["id"],
                "estado": estado,
                "total_estimado": money(total_estimado),
                "notas": f"EJEMPLO - {caso or 'caso normal'}",
                "factura_generada_id": factura_id,
                "fecha_creacion": f"{HOY - timedelta(days=i)}T10:00:00",
                "fecha_actualizacion": f"{HOY - timedelta(days=i)}T11:00:00",
                "es_ejemplo": True,
                "caso_raro": caso,
                "lineas": lineas,
            }
        )
        pid += 1

    return pedidos, todas_las_lineas


def _escribir(nombre, datos):
    destino = SALIDA / nombre
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return destino


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    catalogo = construir_catalogo()
    facturas, lineas_factura = construir_facturas(catalogo["productos"])
    pedidos, lineas_pedido = construir_pedidos(
        catalogo["clientes"], catalogo["productos"], facturas
    )

    archivos = [
        _escribir("catalogo_ejemplo.json", catalogo),
        _escribir(
            "facturas_ejemplo.json",
            {"es_ejemplo": True, "total": len(facturas), "facturas": facturas},
        ),
        _escribir(
            "pedidos_ejemplo.json",
            {"es_ejemplo": True, "total": len(pedidos), "pedidos": pedidos},
        ),
    ]

    print(f"Semilla: {SEMILLA}")
    print(f"Facturas: {len(facturas)} | lineas: {len(lineas_factura)}")
    print(f"Pedidos: {len(pedidos)} | lineas: {len(lineas_pedido)}")
    for archivo in archivos:
        print(f"  {archivo}")


if __name__ == "__main__":
    main()