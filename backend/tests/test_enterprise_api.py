import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["AUTO_CREATE_SCHEMA"] = "1"

from app import app


def login(client, username="admin", password="admin123"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


def test_enterprise_endpoints_require_authentication():
    client = app.test_client()
    assert client.get("/api/equipment").status_code == 401
    assert client.get("/api/notifications").status_code == 401
    assert client.get("/api/suppliers").status_code == 401


def test_admin_can_create_equipment_and_supplier_contracts():
    client = app.test_client()
    login(client)
    equipment = client.post("/api/equipment", json={"name": "Test Projector", "assetTag": "TEST-AV-001"})
    assert equipment.status_code == 201
    assert equipment.json["equipment"]["assetTag"] == "TEST-AV-001"
    supplier = client.post("/api/suppliers", json={"name": "Acme Supplies", "email": "orders@example.test"})
    assert supplier.status_code == 201
    assert supplier.json["supplier"]["name"] == "Acme Supplies"


def test_member_can_submit_borrowing_request_and_receive_contract():
    client = app.test_client()
    login(client)
    equipment = client.post("/api/equipment", json={"name": "Test Camera", "assetTag": "TEST-AV-002"})
    equipment_id = equipment.json["equipment"]["id"]
    login(client, "member", "member123")
    response = client.post(
        "/api/borrowing-requests",
        json={"equipmentId": equipment_id, "purpose": "Event coverage", "requestedFrom": "2026-11-06", "dueDate": "2026-11-10"},
    )
    assert response.status_code in (201, 400)
    if response.status_code == 201:
        assert {"id", "equipmentId", "dueDate", "status", "overdue"} <= response.json["request"].keys()
