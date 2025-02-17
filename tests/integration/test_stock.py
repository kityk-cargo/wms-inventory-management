import pytest
import uuid
from sqlalchemy.orm import Session
from app.models import Product, Location, Stock
from app.repository import stock_repository

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


def test_add_stock(db_session: Session, sample_data):
    """Should add stock and return the expected stock details."""
    # Arrange
    product, location = sample_data
    stock_data = {
        "product_id": int(product.id),
        "location_id": int(location.id),
        "quantity": 10,
    }
    # Act
    new_stock = stock_repository.create_stock(db_session, stock_data)
    # Assert
    assert new_stock.product_id == product.id, "Product ID mismatch"
    assert new_stock.location_id == location.id, "Location ID mismatch"
    assert new_stock.quantity == 10, "Quantity incorrect"


def test_remove_stock(db_session: Session, sample_data):
    """Should remove stock correctly and return the updated stock details."""
    # Arrange
    product, location = sample_data
    stock_data = {
        "product_id": int(product.id),
        "location_id": int(location.id),
        "quantity": 10,
    }
    stock = stock_repository.create_stock(db_session, stock_data)
    # Act
    updated_stock = stock_repository.update_stock_quantity(db_session, stock, -5)
    # Assert
    assert updated_stock.product_id == product.id, "Product ID mismatch"
    assert updated_stock.location_id == location.id, "Location ID mismatch"
    assert updated_stock.quantity == 5, "Quantity after update incorrect"


def test_list_stock(db_session: Session, sample_data):
    """Should list stock and include the recently added stock record."""
    # Arrange
    product, location = sample_data
    stock_data = {
        "product_id": int(product.id),
        "location_id": int(location.id),
        "quantity": 10,
    }
    stock_repository.create_stock(db_session, stock_data)
    # Act
    stock_list = stock_repository.list_stock(db_session)
    # Assert
    assert any(
        s.product_id == product.id and s.location_id == location.id and s.quantity == 10
        for s in stock_list
    ), "Expected stock record not found"


def test_remove_stock_negative_overdraw(db_session: Session, sample_data):
    """Negative: Removing more stock than available should raise IntegrityError due to DB constraint."""
    # Arrange
    product, location = sample_data
    stock_data = {
        "product_id": int(product.id),
        "location_id": int(location.id),
        "quantity": 3,
    }
    stock = stock_repository.create_stock(db_session, stock_data)
    # Act & Assert: Expect IntegrityError when subtraction violates the non-negative constraint.
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        stock_repository.update_stock_quantity(db_session, stock, -5)


def test_update_nonexistent_stock(db_session: Session):
    """Negative: Attempting to update stock that does not exist should fail gracefully."""
    # Arrange: Create a fake stock instance not persisted in db
    fake_stock = Stock(product_id=9999, location_id=9999, quantity=10)
    # Act & Assert: Update should raise an exception or return None
    with pytest.raises(Exception):
        stock_repository.update_stock_quantity(db_session, fake_stock, -5)
