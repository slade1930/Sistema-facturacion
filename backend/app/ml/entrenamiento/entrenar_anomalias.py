"""Entrenamiento del Isolation Forest de anomalías.

No usa etiquetas: aprende qué es normal de los CSV de ejemplo y guarda
el modelo en backend/ml_models/. Las etiquetas se usan sólo al evaluar.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from app.ml.datasets import generar_datos
from app.ml.features.anomalias import RasgosFactura
from app.ml.modelos import anomalias as modelo


def rasgos_desde_fila(fila):
    """Convierte una fila de los CSV en RasgosFactura (para entrenar/evaluar)."""
    descuentos = [
        Decimal(str(linea.get("descuento_pct") or "0"))
        for linea in fila.get("lineas") or []
    ]
    return RasgosFactura(
        factura_id=int(fila["id"]),
        cliente=fila.get("cliente_ruc") or fila.get("cliente_nombre") or "",
        fecha=date.fromisoformat(str(fila["fecha"])[:10]),
        total=Decimal(str(fila["total"])),
        descuento_max_pct=max(descuentos, default=Decimal("0")),
        anulada=str(fila.get("estado", "")).lower() == "anulada",
    )


def entrenar_anomalias(
    guardar=True,
    nombre=modelo.NOMBRE_MODELO,
    directorio=generar_datos.SALIDA,
    n_arboles=modelo.N_ARBOLES,
    semilla=modelo.SEMILLA,
):
    """Entrena con los CSV; devuelve los datos y opcionalmente los guarda."""
    facturas, _ = generar_datos.leer_dataset_csv(directorio)
    rasgos = [rasgos_desde_fila(fila) for fila in facturas]
    datos = modelo.entrenar(rasgos, n_arboles=n_arboles, semilla=semilla)
    if datos is None:
        return None
    if guardar:
        ruta = modelo.guardar(datos, nombre)
        if ruta is not None:
            datos["ruta"] = str(ruta)
    return datos


if __name__ == "__main__":
    datos = entrenar_anomalias()
    print(json.dumps({
        "entrenado": datos is not None,
        "facturas": datos["n"] if datos else 0,
        "modelo": modelo.NOMBRE_MODELO,
        "ruta": datos.get("ruta") if datos else None,
    }, ensure_ascii=False))
