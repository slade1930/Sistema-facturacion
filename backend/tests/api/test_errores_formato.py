def _comprobar(respuesta, status, code):
    assert respuesta.status_code == status
    cuerpo = respuesta.json()
    assert isinstance(cuerpo["detail"], str)
    assert cuerpo["code"] == code


def test_404_factura_inexistente(client):
    r = client.get("/api/v1/facturas/999999999")
    _comprobar(r, 404, "NOT_FOUND")


def test_404_ruta_inexistente(client):
    r = client.get("/api/v1/esta-ruta-no-existe")
    _comprobar(r, 404, "NOT_FOUND")


def test_401_clave_incorrecta(client):
    r = client.get("/api/v1/facturas/1", headers={"X-API-Key": "incorrecta"})
    _comprobar(r, 401, "UNAUTHORIZED")


def test_422_datos_invalidos(client):
    r = client.post("/api/v1/facturas", json={})
    _comprobar(r, 422, "VALIDATION_ERROR")
    assert isinstance(r.json()["errors"], list)