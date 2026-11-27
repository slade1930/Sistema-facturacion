def test_404_producto_inexistente(client):
    r = client.get("/api/v1/productos/999999999")
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_404_cliente_inexistente(client):
    r = client.get("/api/v1/clientes/999999999")
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_404_categoria_inexistente(client):
    r = client.get("/api/v1/categorias/999999999")
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_422_cliente_datos_vacios(client):
    r = client.post("/api/v1/clientes", json={})
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"
