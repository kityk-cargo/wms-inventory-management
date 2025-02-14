import uuid
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def sample_product(client_with_db: TestClient):
    # Arrange
    unique_sku = "PROD_" + str(uuid.uuid4())
    payload = {
        "sku": unique_sku,
        "name": "Integration Test Product",
        "category": "Integration Category",
        "description": "Integration product description",
    }
    # Act
    response = client_with_db.post("/products", json=payload)
    # Assert
    assert response.status_code == 200
    product = response.json()
    assert isinstance(product.get("id"), int)
    assert product["sku"] == unique_sku
    return product


def test_create_product(client_with_db: TestClient):
    """Should create a product and return its details."""
    # Arrange
    unique_sku = "PROD_" + str(uuid.uuid4())
    payload = {
        "sku": unique_sku,
        "name": "Integration Create Product",
        "category": "Integration Category",
        "description": "Created via integration test",
    }
    # Act
    response = client_with_db.post("/products", json=payload)
    # Assert
    assert response.status_code == 200
    product = response.json()
    assert isinstance(product.get("id"), int)
    assert product["sku"] == unique_sku
    assert product["name"] == "Integration Create Product"
    assert product["category"] == "Integration Category"
    assert product["description"] == "Created via integration test"


def test_get_product(client_with_db: TestClient, sample_product):
    """Should retrieve product details by id."""
    # Arrange
    product_id = sample_product["id"]
    # Act
    response = client_with_db.get(f"/products/{product_id}")
    # Assert
    assert response.status_code == 200
    product = response.json()
    assert product["id"] == product_id
    assert product["sku"] == sample_product["sku"]
    assert product["name"] == sample_product["name"]
    assert product["category"] == sample_product["category"]
    assert product["description"] == sample_product["description"]


def test_list_products(client_with_db: TestClient, sample_product):
    """Should list products including the created one."""
    # Arrange is done via fixture
    # Act
    response = client_with_db.get("/products")
    # Assert
    assert response.status_code == 200
    products = response.json()
    assert any(prod["id"] == sample_product["id"] for prod in products)
