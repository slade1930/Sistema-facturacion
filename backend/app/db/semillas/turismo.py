"""Bloques de turismo. El sector se toma del nombre de este archivo."""

BLOQUES = {
    # JESUS — objetivo: 4 productos.
    "JESUS": {
        "categorias": [],
        "productos": [],
    },

    # CRISTHIAN — objetivo: 4 productos.
    "CRISTHIAN": {
        "categorias": [
            {
                "nombre": "Alojamiento",
                "descripcion": "Estadías en hoteles, resorts y cabañas en destinos turísticos de Panamá.",
            },
            {
                "nombre": "Paquetes todo incluido",
                "descripcion": "Paquetes turísticos completos con hospedaje, alimentación y actividades incluidas.",
            },
            {
                "nombre": "Tours y excursiones",
                "descripcion": "Recorridos guiados, expediciones marinas y experiencias de aventura por día.",
            },
            {
                "nombre": "Entradas y pasadías",
                "descripcion": "Accesos de día completo a parques, aguas termales y atracciones recreativas.",
            },
        ],
        "productos": [
            {
                "categoria": "Alojamiento",
                "nombre": "Hotel Coclé — Estadía 2 Noches Todo Incluido",
                "descripcion_corta": "Estadía de 2 noches en Penonomé, Provincia de Coclé (Panamá). Incluye desayunos, almuerzos, cenas buffet y tour guiado por el valle.",
                "marca": "Hotel Coclé Resort",
                "presentacion": "paquete 2 noches",
                "precio_unidad": "180.00",
                "unidades_por_caja": 10,
                "permite_media_caja": True,
                "precio_media_caja": "850.00",
                "precio_caja": "1700.00",
                "descuento_pct": "10.00",
                "aplica_itbms": True,
                "estado_activo": True,
                "imagen": None,
                "stock_inicial": "40.00",
            },
            {
                "categoria": "Paquetes todo incluido",
                "nombre": "Expedición Archipiélago de San Blas — 3 Días / 2 Noches",
                "descripcion_corta": "Paquete de 3 días y 2 noches en cabaña frente al mar en Guna Yala (San Blas). Incluye lancha desde puerto Cartí, tres comidas diarias y tour a Isla Perro y Piscina Natural.",
                "marca": "Guna Yala EcoTours",
                "presentacion": "paquete 3 días/2 noches",
                "precio_unidad": "245.00",
                "unidades_por_caja": 8,
                "permite_media_caja": True,
                "precio_media_caja": "940.00",
                "precio_caja": "1880.00",
                "descuento_pct": "15.00",
                "aplica_itbms": True,
                "estado_activo": True,
                "imagen": None,
                "stock_inicial": "24.00",
            },
            {
                "categoria": "Tours y excursiones",
                "nombre": "Tour Avistamiento de Ballenas y Snorkel en Isla Coiba",
                "descripcion_corta": "Excursión de día completo desde Santa Catalina, Veraguas hacia el Parque Nacional Coiba. Incluye lancha rápida, equipo de snorkel, almuerzo ligero y guía certificado.",
                "marca": "Coiba Adventure Panamá",
                "presentacion": "lote de 1 cupo tour",
                "precio_unidad": "95.00",
                "unidades_por_caja": 12,
                "permite_media_caja": False,
                "precio_media_caja": None,
                "precio_caja": "1140.00",
                "descuento_pct": "12.00",
                "aplica_itbms": True,
                "estado_activo": True,
                "imagen": None,
                "stock_inicial": "60.00",
            },
            {
                "categoria": "Entradas y pasadías",
                "nombre": "Pasadía Termal y Senderismo en El Valle de Antón",
                "descripcion_corta": "Entrada general de día completo en El Valle de Antón, Coclé. Incluye acceso a pozos termales, sendero La India Dormida, almuerzo típico panameño y bebida natural.",
                "marca": "Valle Verde Experiencias",
                "presentacion": "entrada general pasadía",
                "precio_unidad": "55.00",
                "unidades_por_caja": 20,
                "permite_media_caja": True,
                "precio_media_caja": "520.00",
                "precio_caja": "1040.00",
                "descuento_pct": "0.00",
                "aplica_itbms": True,
                "estado_activo": True,
                "imagen": None,
                "stock_inicial": "100.00",
            },
        ],
    },

    # ERICK — objetivo: 4 productos.
    "ERICK": {
        "categorias": [],
        "productos": [],
    },

    # LUIS_CASTILLO — objetivo: 4 productos.
    "LUIS_CASTILLO": {
        "categorias": [],
        "productos": [],
    },

    # JOSE_RIVERA — objetivo: 4 productos.
    "JOSE_RIVERA": {
        "categorias": [],
        "productos": [],
    },
}

# EJEMPLO (no cargar): copiar dentro de "productos" del bloque correspondiente.
# En turismo se vende por lotes de cupos, noches o entradas.
# {
#     "categoria": "Alojamiento",  # debe estar declarada en "categorias" del archivo
#     "nombre": "Paquete de ejemplo de dos noches",
#     "sku": "(se genera automáticamente; no lo escribas)",
#     "descripcion_corta": "Lote de ejemplo para mostrar el formato.",
#     "marca": "Operador de ejemplo",
#     "presentacion": "lote de 2 noches",
#     "precio_unidad": "85.00",
#     "unidades_por_caja": 10,
#     "permite_media_caja": False,
#     "precio_media_caja": None,
#     "precio_caja": "850.00",
#     "descuento_pct": "0.00",
#     "aplica_itbms": True,
#     "estado_activo": True,
#     "imagen": None,  # solo None o "media/..."
#     "stock_inicial": "30.00",
# }
