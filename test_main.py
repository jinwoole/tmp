from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_read_item():
    response = client.get("/items/42?q=test")
    assert response.status_code == 200
    assert response.json() == {"item_id": 42, "q": "test"}


def test_create_item():
    item_data = {
        "name": "Test Item",
        "price": 10.99,
        "is_offer": True
    }
    response = client.post("/items/", json=item_data)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Item created"
    assert data["item"] == item_data


def test_update_item():
    item_data = {
        "name": "Updated Item",
        "price": 15.99,
        "is_offer": False
    }
    response = client.put("/items/1", json=item_data)
    assert response.status_code == 200
    data = response.json()
    assert data["item_id"] == 1
    assert data["item"] == item_data