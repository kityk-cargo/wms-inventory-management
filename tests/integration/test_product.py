import uuid
import pytest
from sqlalchemy.orm import Session
from app.repository import product_repository


@pytest.fixture
def sample_product(db_session: Session):
    # Arrange
    unique_sku = "PROD_" + str(uuid.uuid4())
    product_data = {
        "sku": unique_sku,
        "name": "Integration Test Product",
        "category": "Integration Category",
        "description": "Integration product description",
    }
    # Act
    product = product_repository.create_product(db_session, product_data)
    # Assert
    assert isinstance(product.id, int), "Invalid Product ID"
    assert product.sku == unique_sku, "SKU mismatch"
    return product


def test_create_product(db_session: Session):
    """Positive: Should create a product and return its details."""
    # Arrange
    unique_sku = "PROD_" + str(uuid.uuid4())
    product_data = {
        "sku": unique_sku,
        "name": "Integration Create Product",
        "category": "Integration Category",
        "description": "Created via integration test",
    }
    # Act
    product = product_repository.create_product(db_session, product_data)
    # Assert
    assert isinstance(product.id, int), "Product ID is not an integer"
    assert product.sku == unique_sku, "SKU does not match"
    assert product.name == "Integration Create Product", "Name mismatch"
    assert product.category == "Integration Category", "Category mismatch"
    assert product.description == "Created via integration test", "Description mismatch"


def test_get_product(db_session: Session, sample_product):
    """Positive: Should retrieve product details by valid id."""
    # Arrange
    product_id = sample_product.id
    # Act
    fetched_product = product_repository.get_by_id(db_session, product_id)
    # Assert
    assert fetched_product is not None, "Fetched product is None"
    assert fetched_product.id == sample_product.id, "Product ID mismatch"
    assert fetched_product.sku == sample_product.sku, "SKU mismatch"
    assert fetched_product.name == sample_product.name, "Name mismatch"
    assert fetched_product.category == sample_product.category, "Category mismatch"
    assert (
        fetched_product.description == sample_product.description
    ), "Description mismatch"


def test_list_products(db_session: Session, sample_product):
    """Positive: Should list products including the created one."""
    # Arrange
    # sample_product fixture provides an existing product
    # Act
    products = product_repository.list_products(db_session)
    # Assert
    assert any(
        p.id == sample_product.id for p in products
    ), "Created product not found in product list"


def test_create_duplicate_product(db_session: Session, sample_product):
    """Negative: Should not allow creation of a duplicate product SKU."""
    # Arrange
    duplicate_data = {
        "sku": sample_product.sku,  # same SKU as existing product
        "name": "Duplicate Product",
        "category": "Integration Category",
        "description": "Duplicate product test",
    }
    # Act & Assert: Expect an Exception due to duplicate SKU constraint.
    with pytest.raises(Exception):
        product_repository.create_product(db_session, duplicate_data)


def test_get_nonexistent_product(db_session: Session):
    """Edge: Retrieving a product using an invalid id should return None."""
    # Arrange
    invalid_id = 999999
    # Act
    product = product_repository.get_by_id(db_session, invalid_id)
    # Assert
    assert product is None, "Expected None for non-existent product"
