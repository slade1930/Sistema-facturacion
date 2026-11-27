"""Frases de ejemplo para el asistente (paso 0; las usa Luis en el paso 3).

Módulo app.ml.asistente. Dueño: Luis (Módulo 4). Depende de asistente/intenciones.py.
Frases inventadas, sin CSV ni datos reales.
"""

FRASES_EJEMPLO = (
    "¿Cuánto facturamos en octubre?",
    "Ventas del cliente 3",
    "Productos más vendidos",
    "Facturas anuladas",
    "Facturas en revisión",
    "Qué pidió el cliente 7",
)

FRASES_ROTULOADAS = (
    ("¿Cuánto facturamos en octubre?", "ventas_por_mes"),
    ("Ventas por mes", "ventas_por_mes"),
    ("Facturación mensual de 2026", "ventas_por_mes"),
    ("¿Cuánto vendimos en noviembre?", "ventas_por_mes"),
    ("Muéstrame las ventas del mes", "ventas_por_mes"),
    ("Ventas de enero", "ventas_por_mes"),
    ("Ventas del cliente 3", "ventas_por_cliente"),
    ("¿Cuánto facturó el cliente 7?", "ventas_por_cliente"),
    ("Facturación por cliente", "ventas_por_cliente"),
    ("Ventas por cliente en 2026", "ventas_por_cliente"),
    ("Cliente 2, ¿cuánto nos facturó?", "ventas_por_cliente"),
    ("Qué pidió el cliente 7", "ventas_por_cliente"),
    ("Ventas por producto", "ventas_por_producto"),
    ("¿Qué productos vendimos en octubre?", "ventas_por_producto"),
    ("Facturación por producto", "ventas_por_producto"),
    ("Ventas de productos en 2026", "ventas_por_producto"),
    ("Detalle de ventas por producto", "ventas_por_producto"),
    ("Cuánto vendimos de cada producto", "ventas_por_producto"),
    ("Facturas anuladas", "facturas_anuladas"),
    ("¿Cuántas facturas están anuladas?", "facturas_anuladas"),
    ("Mostrar facturas anuladas de 2026", "facturas_anuladas"),
    ("Facturas anuladas en noviembre", "facturas_anuladas"),
    ("Lista de facturas anuladas", "facturas_anuladas"),
    ("Facturas que fueron anuladas", "facturas_anuladas"),
    ("Productos más vendidos", "top_productos"),
    ("Top 5 productos", "top_productos"),
    ("Los productos más vendidos del mes", "top_productos"),
    ("Top 3 productos vendidos", "top_productos"),
    ("Productos más vendidos en 2026", "top_productos"),
    ("Ranking de productos vendidos", "top_productos"),
    ("Facturas en revisión", "facturas_en_revision"),
    ("¿Cuántas facturas están en revisión?", "facturas_en_revision"),
    ("Facturas en revision de octubre", "facturas_en_revision"),
    ("Lista de facturas en revisión", "facturas_en_revision"),
    ("Facturas pendientes de revisión", "facturas_en_revision"),
    ("Facturas en revisión del cliente 3", "facturas_en_revision"),
)
