
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sections_v1_endpoint():
    response = client.get("/sections?version=v1")

    assert response.status_code == 200

    data = response.json()
    assert data["version"] == "v1"
    assert data["total_sections"] == 28
    assert len(data["sections"]) == 28


def test_compare_endpoint():
    response = client.get("/compare")

    assert response.status_code == 200

    data = response.json()
    assert data["total_changes"] == 5

    statuses = [item["status"] for item in data["changes"]]

    assert statuses.count("changed") == 4
    assert statuses.count("added") == 1
