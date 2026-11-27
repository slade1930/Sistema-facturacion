"""Pruebas del endpoint de historial."""


def _payload(cliente: str) -> dict:
    return {
        "cliente_nombre": cliente,
        "lineas": [
            {
                "descripcion": "Producto de prueba",
                "cantidad": "1",
                "precio_unitario": "5.00",
            }
        ],
    }


def _payload_con_fecha(cliente: str, fecha: str) -> dict:
    payload = _payload(cliente)
    payload["fecha"] = fecha
    return payload


def test_historial_con_filtros_y_paginacion(client):
    client.post("/api/v1/facturas", json=_payload("Historial Uno"))
    client.post("/api/v1/facturas", json=_payload("Historial Dos"))

    respuesta = client.get(
        "/api/v1/historial",
        params={
            "cliente": "Historial",
            "estado": "emitida",
            "limite": 1,
            "desplazamiento": 0,
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["total"] == 2
    assert datos["limite"] == 1
    assert datos["desplazamiento"] == 0
    assert len(datos["items"]) == 1
    assert datos["items"][0]["cliente_nombre"] in {"Historial Uno", "Historial Dos"}


def test_historial_valida_paginacion(client):
    respuesta = client.get("/api/v1/historial", params={"limite": 0})

    assert respuesta.status_code == 422


def test_historial_paginacion_desplazamiento(client):
    client.post("/api/v1/facturas", json=_payload("Historial Pag Uno"))
    client.post("/api/v1/facturas", json=_payload("Historial Pag Dos"))
    client.post("/api/v1/facturas", json=_payload("Historial Pag Tres"))

    respuesta = client.get(
        "/api/v1/historial",
        params={
            "cliente": "Historial Pag",
            "limite": 1,
            "desplazamiento": 1,
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["total"] == 3
    assert datos["limite"] == 1
    assert datos["desplazamiento"] == 1
    assert len(datos["items"]) == 1
    assert datos["items"][0]["cliente_nombre"].startswith("Historial Pag")


def test_historial_filtro_fechas(client):
    client.post(
        "/api/v1/facturas",
        json=_payload_con_fecha("Historial Fecha Uno", "2026-01-10"),
    )
    client.post(
        "/api/v1/facturas",
        json=_payload_con_fecha("Historial Fecha Dos", "2026-02-15"),
    )
    client.post(
        "/api/v1/facturas",
        json=_payload_con_fecha("Historial Fecha Tres", "2026-03-20"),
    )

    respuesta = client.get(
        "/api/v1/historial",
        params={
            "cliente": "Historial Fecha",
            "fecha_desde": "2026-02-01",
            "fecha_hasta": "2026-02-28",
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["total"] == 1
    assert len(datos["items"]) == 1
    assert datos["items"][0]["cliente_nombre"] == "Historial Fecha Dos"


def test_historial_limite_maximo(client):
    respuesta = client.get("/api/v1/historial", params={"limite": 100})

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["limite"] == 100
    assert "items" in datos
    assert "total" in datos
    assert "desplazamiento" in datos


def test_historial_sin_resultados(client):
    respuesta = client.get(
        "/api/v1/historial",
        params={"cliente": "NoExisteClienteXYZ123"},
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["total"] == 0
    assert datos["items"] == []


def test_historial_desplazamiento_negativo(client):
    respuesta = client.get("/api/v1/historial", params={"desplazamiento": -1})

    assert respuesta.status_code == 422
