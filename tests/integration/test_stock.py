import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Product, Location

pytestmark = pytest.mark.db


@pytest.fixture
def sample_data(db_session: Session):
    unique_sku = "TESTSKU_" + str(uuid.uuid4())
    product = Product(
        sku=unique_sku,
        name="Test Product",
        category="Test Category",
        description="Test Description",
    )
    location = Location(aisle="A1", bin="B1")
    db_session.add(product)
    db_session.add(location)
    db_session.flush()
    db_session.commit()
    db_session.refresh(product)
    db_session.refresh(location)
    return product, location


def test_add_stock(client_with_db: TestClient, sample_data):
    """Should add stock and return the expected stock details."""
    # Arrange
    product, location = sample_data
    # Act
    response = client_with_db.post(
        "/stock/inbound",
        json={
            "product_id": int(product.id),
            "location_id": int(location.id),
            "quantity": 10,
        },
    )
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == int(product.id)
    assert data["location_id"] == int(location.id)
    assert data["quantity"] == 10


def test_remove_stock(client_with_db: TestClient, sample_data):
    """Should remove stock correctly and return the updated stock details."""
    # Arrange
    product, location = sample_data
    client_with_db.post(
        "/stock/inbound",
        json={
            "product_id": int(product.id),
            "location_id": int(location.id),
            "quantity": 10,
        },
    )
    # Act
    response = client_with_db.post(
        "/stock/outbound",
        json={
            "product_id": int(product.id),
            "location_id": int(location.id),
            "quantity": 5,
        },
    )
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == int(product.id)
    assert data["location_id"] == int(location.id)
    assert data["quantity"] == 5


def test_list_stock(client_with_db: TestClient, sample_data):
    """Should list stock and include the recently added stock record."""
    # Arrange
    product, location = sample_data
    client_with_db.post(
        "/stock/inbound",
        json={
            "product_id": int(product.id),
            "location_id": int(location.id),
            "quantity": 10,
        },
    )
    # Act
    response = client_with_db.get("/stock/")
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["product_id"] == int(product.id)
    assert data[0]["location_id"] == int(location.id)
    assert data[0]["quantity"] == 10
