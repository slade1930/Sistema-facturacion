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
