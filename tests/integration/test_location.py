import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def sample_location(client_with_db: TestClient):
    # Arrange
    payload = {"aisle": "A1", "bin": "B1"}
    # Act
    response = client_with_db.post("/locations", json=payload)
    # Assert
    assert response.status_code == 200
    location = response.json()
    assert isinstance(location.get("id"), int)
    assert location["aisle"] == "A1"
    assert location["bin"] == "B1"
    return location


def test_create_location(client_with_db: TestClient):
    """Should create a location and return its details."""
    # Arrange
    payload = {"aisle": "A2", "bin": "B2"}
    # Act
    response = client_with_db.post("/locations", json=payload)
    # Assert
    assert response.status_code == 200
    location = response.json()
    assert isinstance(location.get("id"), int)
    assert location["aisle"] == "A2"
    assert location["bin"] == "B2"


def test_get_location(client_with_db: TestClient, sample_location):
    """Should retrieve location details by id."""
    # Arrange
    location_id = sample_location["id"]
    # Act
    response = client_with_db.get(f"/locations/{location_id}")
    # Assert
    assert response.status_code == 200
    location = response.json()
    assert location["id"] == location_id
    assert location["aisle"] == sample_location["aisle"]
    assert location["bin"] == sample_location["bin"]


def test_list_locations(client_with_db: TestClient, sample_location):
    """Should list locations including the created one."""
    # Arrange is done via fixture
    # Act
    response = client_with_db.get("/locations")
    # Assert
    assert response.status_code == 200
    locations = response.json()
    assert any(loc["id"] == sample_location["id"] for loc in locations)
