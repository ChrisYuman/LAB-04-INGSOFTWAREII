from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_checkout_validation_error():
    # Enviar payload invalido para trigger excepcion
    response = client.post("/ventas/checkout", json={"usuario_id": 0, "items": [], "metodo_pago": "TEST"})
    assert response.status_code == 400
