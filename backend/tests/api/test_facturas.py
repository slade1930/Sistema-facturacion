"""Pruebas de los endpoints de facturas."""


def _payload(cliente: str = "Cliente API") -> dict:
    return {
        "cliente_nombre": cliente,
        "cliente_ruc": "123456789-1-2026",
        "lineas": [
            {
                "descripcion": "Producto de prueba",
                "cantidad": "2",
                "precio_unitario": "10.00",
                "gravada": True,
            }
        ],
    }


def test_crear_y_obtener_factura(client):
    creada = client.post("/api/v1/facturas", json=_payload())

    assert creada.status_code == 201, creada.text
    datos = creada.json()
    assert datos["numero_serie"].startswith("FAC-")
    assert len(datos["codigo_verificacion"]) == 12
    assert datos["total"] == "21.40"
    assert len(datos["lineas"]) == 1

    obtenida = client.get(f"/api/v1/facturas/{datos['id']}")

    assert obtenida.status_code == 200
    assert obtenida.json()["numero_serie"] == datos["numero_serie"]


def test_anular_factura(client):
    creada = client.post("/api/v1/facturas", json=_payload())
    factura_id = creada.json()["id"]

    anulada = client.post(f"/api/v1/facturas/{factura_id}/anular")

    assert anulada.status_code == 200, anulada.text
    assert anulada.json()["estado"] == "anulada"
    assert anulada.json()["fecha_anulacion"] is not None

    repetida = client.post(f"/api/v1/facturas/{factura_id}/anular")

    assert repetida.status_code == 409


def test_duplicar_factura(client):
    creada = client.post("/api/v1/facturas", json=_payload("Cliente original"))
    original = creada.json()

    duplicada = client.post(f"/api/v1/facturas/{original['id']}/duplicar")

    assert duplicada.status_code == 201, duplicada.text
    datos = duplicada.json()
    assert datos["id"] != original["id"]
    assert datos["numero_serie"] != original["numero_serie"]
    assert datos["cliente_nombre"] == "Cliente original"
    assert datos["estado"] == "emitida"


def test_factura_inexistente(client):
    respuesta = client.get("/api/v1/facturas/999999")

    assert respuesta.status_code == 404


def test_api_key_invalida(client):
    respuesta = client.post(
        "/api/v1/facturas",
        json=_payload(),
        headers={"X-API-Key": "clave-incorrecta"},
    )

    assert respuesta.status_code == 401
