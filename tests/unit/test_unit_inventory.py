"""
NOTE:
- These tests use simplified mocks to simulate SQLAlchemy behavior. They do not cover full ORM features
  (e.g., transaction commit/rollback, lazy loading) and bypass FastAPI's dependency injection/request lifecycle.
- For full end-to-end testing, use FastAPI's TestClient with a real or properly simulated database.
- Each test receives a fresh InMemoryDB instance to avoid shared state.
"""
import pytest
from datetime import datetime
from fastapi import HTTPException
from app.routers import products, locations, stock
from app.schemas import ProductCreate, LocationCreate, StockOperation
from unittest.mock import patch
import app.models as models
import app.repository.stock_repository as stock_repo
import app.repository.product_repository as product_repo
import app.repository.location_repository as location_repo

# Add module-level fixture usage so pact_setup is initialized once for the file.
pytestmark = pytest.mark.usefixtures("pact_setup")


# Helpers for simulating SQLAlchemy column expressions
class ColumnExpression:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return (self.name, other)


class Column:
    def __init__(self, name):
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return ColumnExpression(self.name)
        return instance.__dict__.get(self.name)

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value


# Updated Mock classes with descriptors.
# These mocks provide basic attribute management, without full SQLAlchemy functionality.
class MockProduct:
    id = Column("id")
    sku = Column("sku")
    name = Column("name")
    category = Column("category")
    description = Column("description")
    created_at = Column("created_at")
    updated_at = Column("updated_at")

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


class MockLocation:
    id = Column("id")
    aisle = Column("aisle")
    bin = Column("bin")
    created_at = Column("created_at")

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class MockStock:
    product_id = Column("product_id")
    location_id = Column("location_id")
    quantity = Column("quantity")
    updated_at = Column("updated_at")

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if self.quantity is None:
            self.quantity = 0


# Replace original model imports with mocks
products.Product = MockProduct  # type: ignore
locations.Location = MockLocation  # type: ignore
stock.Stock = MockStock  # type: ignore
stock.Product = MockProduct  # type: ignore
stock.Location = MockLocation  # type: ignore

# Existing patch for app.models
models.Product = MockProduct  # type: ignore
models.Location = MockLocation  # type: ignore
models.Stock = MockStock  # type: ignore

# NEW: Patch repository modules so that they use the mocks.
stock_repo.Stock = MockStock  # type: ignore
product_repo.Product = MockProduct  # type: ignore
location_repo.Location = MockLocation  # type: ignore


# InMemoryDB and QuerySimulator simulate basic DB operations.
class InMemoryDB:
    def __init__(self):
        self.data = {"products": {}, "locations": {}, "stock": {}}
        self._id_counter = {"products": 1, "locations": 1}
        self._original_state = {}

    def _backup_state(self):
        self._original_state = {
            "products": self.data["products"].copy(),
            "locations": self.data["locations"].copy(),
            "stock": self.data["stock"].copy(),
        }

    def rollback(self):
        if self._original_state:
            self.data = {
                "products": self._original_state["products"].copy(),
                "locations": self._original_state["locations"].copy(),
                "stock": self._original_state["stock"].copy(),
            }
        self._original_state = {}

    def commit(self):
        self._original_state = {}  # Clear backup after successful commit

    def query(self, model):
        if model == MockProduct:
            return QuerySimulator(list(self.data["products"].values()))
        elif model == MockLocation:
            return QuerySimulator(list(self.data["locations"].values()))
        elif model == MockStock:
            return QuerySimulator(list(self.data["stock"].values()))
        return QuerySimulator([])

    def add(self, obj):
        if isinstance(obj, MockProduct):
            obj.id = self._id_counter["products"]
            obj.created_at = datetime.utcnow()
            obj.updated_at = datetime.utcnow()
            self.data["products"][obj.id] = obj
            self._id_counter["products"] += 1
        elif isinstance(obj, MockLocation):
            obj.id = self._id_counter["locations"]
            obj.created_at = datetime.utcnow()
            self.data["locations"][obj.id] = obj
            self._id_counter["locations"] += 1
        elif isinstance(obj, MockStock):
            key = (obj.product_id, obj.location_id)
            self.data["stock"][key] = obj

    def refresh(self, obj):
        # Simulated refresh.
        pass


class QuerySimulator:
    def __init__(self, data):
        self.data = data

    def filter(self, *conditions):
        filtered_data = self.data
        for cond in conditions:
            if isinstance(cond, tuple) and len(cond) == 2:
                field, expected = cond
                filtered_data = [
                    item for item in filtered_data if getattr(item, field) == expected
                ]
        return QuerySimulator(filtered_data)

    def first(self):
        return self.data[0] if self.data else None

    def all(self):
        return self.data


@pytest.fixture
def db():
    # Returns a fresh InMemoryDB instance per test to avoid shared state.
    return InMemoryDB()


# ---------------------- Product Tests ----------------------
@pytest.mark.parametrize(
    "product_data",
    [
        pytest.param(
            {
                "sku": "TEST001",
                "name": "Test Product 1",
                "category": "Test Cat",
                "description": "Test Desc",
            },
            id="Product with full details",
        ),
        pytest.param(
            {
                "sku": "TEST002",
                "name": "Test Product 2",
                "category": "Test Cat 2",
                "description": None,
            },
            id="Product with missing description",
        ),
    ],
)
def test_create_product(db, product_data):
    """Should successfully create a product with the given valid data."""
    # Arrange
    product_in = ProductCreate(**product_data)
    # Act
    result = products.create_product_endpoint(product_in, db)
    # Assert
    assert result.id is not None
    assert result.sku == product_data["sku"]
    assert result.name == product_data["name"]
    assert result.created_at is not None
    assert result.description == product_data["description"]


def test_get_nonexistent_product(db):
    """Should raise a 404 error when attempting to retrieve a non-existent product."""
    # Arrange (implicit: no product exists)
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        products.get_product_endpoint(999, db)
    # Assert
    assert exc_info.value.status_code == 404


def test_create_product_invalid_sku(db):
    """Should raise validation error when creating a product with invalid SKU format."""
    # Arrange
    invalid_product = ProductCreate(
        sku="",  # Invalid empty SKU
        name="Test Product",
        category="Test",
        description="Test",
    )
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        products.create_product_endpoint(invalid_product, db)
    assert exc_info.value.status_code == 400


def test_create_product_duplicate_sku(db):
    """Should raise conflict error when creating a product with duplicate SKU."""
    # Arrange
    product_data = {
        "sku": "DUPLICATE-SKU",
        "name": "Test Product",
        "category": "Test",
        "description": "Test",
    }
    products.create_product_endpoint(ProductCreate(**product_data), db)
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        products.create_product_endpoint(ProductCreate(**product_data), db)
    assert exc_info.value.status_code == 409


@pytest.mark.parametrize("invalid_id", [-1, 0, 999999])
def test_get_product_invalid_id(db, invalid_id):
    """Should handle invalid product IDs gracefully."""
    # Arrange (implicit in fixture)
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        products.get_product_endpoint(invalid_id, db)
    assert exc_info.value.status_code == 404


# ---------------------- Location Tests ----------------------
@pytest.mark.parametrize(
    "location_data",
    [
        pytest.param({"aisle": "A1", "bin": "B1"}, id="Valid location A1-B1"),
        pytest.param({"aisle": "A2", "bin": "B2"}, id="Valid location A2-B2"),
    ],
)
def test_create_location(db, location_data):
    """Should successfully create a location when provided valid data."""
    # Arrange
    location_in = LocationCreate(**location_data)
    # Act
    result = locations.create_location_endpoint(location_in, db)
    # Assert
    assert result.id is not None
    assert result.aisle == location_data["aisle"]
    assert result.bin == location_data["bin"]


def test_create_duplicate_location(db):
    """Should raise a 400 error when creating a duplicate location."""
    # Arrange
    loc_data = {"aisle": "A1", "bin": "B1"}
    locations.create_location_endpoint(LocationCreate(**loc_data), db)
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        locations.create_location_endpoint(LocationCreate(**loc_data), db)
    # Assert
    assert exc_info.value.status_code == 400


def test_create_location_invalid_format(db):
    """Should reject location creation with invalid aisle/bin format."""
    # Arrange
    invalid_location = LocationCreate(aisle="", bin="")  # Invalid empty values
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        locations.create_location_endpoint(invalid_location, db)
    assert exc_info.value.status_code == 400


@pytest.mark.parametrize(
    "invalid_data",
    [
        {"aisle": "A1", "bin": " "},
        {"aisle": " ", "bin": "B1"},
    ],
)
def test_create_location_invalid_data(db, invalid_data):
    """Should reject location creation with various invalid data formats."""
    # Arrange
    location_in = LocationCreate(**invalid_data)
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        locations.create_location_endpoint(location_in, db)
    assert exc_info.value.status_code == 400


# ---------------------- Stock Tests ----------------------
@pytest.mark.parametrize(
    "quantity",
    [
        pytest.param(1, id="Add 1 unit of stock (alert expected)"),
        pytest.param(5, id="Add 5 units of stock (alert expected)"),
        pytest.param(10, id="Add 10 units of stock (alert expected)"),
        pytest.param(25, id="Add 25 units of stock (no alert)"),
    ],
)
def test_add_stock(db, quantity):
    """Should add stock and trigger a low stock alert only if quantity is below threshold."""
    # Arrange
    with patch("app.routers.stock.send_low_stock_alert") as mock_alert:
        product = products.create_product_endpoint(
            ProductCreate(
                sku=f"SKU{quantity}", name="Test", category="Test", description="Test"
            ),
            db,
        )
        location = locations.create_location_endpoint(
            LocationCreate(aisle="A1", bin="B1"), db
        )
        operation = StockOperation(
            product_id=product.id, location_id=location.id, quantity=quantity
        )
        # Act
        result = stock.add_stock(operation, db)
        # Assert
        assert result.quantity == quantity
        if result.quantity < 20:
            mock_alert.assert_called_once()
        else:
            mock_alert.assert_not_called()


def test_remove_stock_insufficient(db):
    """Should raise a 400 error when trying to remove more stock than available."""
    # Arrange
    product = products.create_product_endpoint(
        ProductCreate(sku="SKU_TEST", name="Test", category="Test", description="Test"),
        db,
    )
    location = locations.create_location_endpoint(
        LocationCreate(aisle="A1", bin="B1"), db
    )
    stock.add_stock(
        StockOperation(product_id=product.id, location_id=location.id, quantity=5), db
    )
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        stock.remove_stock(
            StockOperation(product_id=product.id, location_id=location.id, quantity=10),
            db,
        )
    # Assert
    assert exc_info.value.status_code == 400


@pytest.mark.parametrize(
    "initial, remove, expected",
    [
        pytest.param(
            25, 25, 0, id="Remove all stock resulting in zero (alert expected)"
        ),
        pytest.param(
            25, 20, 5, id="Remove stock leaving below threshold (alert expected)"
        ),
        pytest.param(25, 3, 22, id="Remove stock leaving above threshold (no alert)"),
    ],
)
def test_stock_operations(db, initial, remove, expected):
    """Should update stock correctly and trigger a low stock alert only when the resulting quantity is below threshold."""
    # Arrange
    product = products.create_product_endpoint(
        ProductCreate(
            sku=f"SKU_OP_{initial}", name="Test", category="Test", description="Test"
        ),
        db,
    )
    location = locations.create_location_endpoint(
        LocationCreate(aisle="A1", bin="B1"), db
    )
    # Add and remove stock with alert patched.
    with patch("app.routers.stock.send_low_stock_alert") as mock_alert:
        stock.add_stock(
            StockOperation(
                product_id=product.id, location_id=location.id, quantity=initial
            ),
            db,
        )
        # Act
        result = stock.remove_stock(
            StockOperation(
                product_id=product.id, location_id=location.id, quantity=remove
            ),
            db,
        )
        # Assert
        assert result.quantity == expected
        if result.quantity < 20:
            mock_alert.assert_called_once()
        else:
            mock_alert.assert_not_called()


def test_stock_transaction_rollback(db):
    """Should rollback stock transaction when an error occurs."""
    # Arrange
    product = products.create_product_endpoint(
        ProductCreate(
            sku="TEST-ROLLBACK", name="Test", category="Test", description="Test"
        ),
        db,
    )
    location = locations.create_location_endpoint(
        LocationCreate(aisle="A1", bin="B1"), db
    )
    initial_stock = StockOperation(
        product_id=product.id, location_id=location.id, quantity=50
    )
    stock.add_stock(initial_stock, db)

    # Act & Assert - Attempt to remove more stock than available
    with pytest.raises(HTTPException) as exc_info:
        stock.remove_stock(
            StockOperation(
                product_id=product.id, location_id=location.id, quantity=100
            ),
            db,
        )

    # Verify stock remains unchanged
    result = (
        db.query(MockStock)
        .filter(
            MockStock.product_id == product.id, MockStock.location_id == location.id
        )
        .first()
    )
    assert result.quantity == 50
    assert exc_info.value.status_code == 400


@pytest.mark.parametrize(
    "initial_qty,remove_qty,expected_alert",
    [
        (50, 40, True),  # Drop below threshold (10 remaining)
        (50, 20, False),  # Stay above threshold (30 remaining)
        (25, 10, True),  # Already below threshold
        (20, 20, True),  # Drop to zero
    ],
)
def test_stock_alert_scenarios(db, initial_qty, remove_qty, expected_alert):
    """Should trigger low stock alerts appropriately based on quantity thresholds."""
    # Arrange
    product = products.create_product_endpoint(
        ProductCreate(
            sku=f"ALERT-{initial_qty}", name="Test", category="Test", description="Test"
        ),
        db,
    )
    location = locations.create_location_endpoint(
        LocationCreate(aisle="A1", bin="B1"), db
    )
    stock.add_stock(
        StockOperation(
            product_id=product.id, location_id=location.id, quantity=initial_qty
        ),
        db,
    )

    # Act
    with patch("app.routers.stock.send_low_stock_alert") as mock_alert:
        stock.remove_stock(
            StockOperation(
                product_id=product.id, location_id=location.id, quantity=remove_qty
            ),
            db,
        )

    # Assert
    if expected_alert:
        mock_alert.assert_called_once()
    else:
        mock_alert.assert_not_called()


def test_concurrent_stock_operations(db):
    """Should handle concurrent stock operations correctly."""
    # Arrange
    product = products.create_product_endpoint(
        ProductCreate(
            sku="CONCURRENT", name="Test", category="Test", description="Test"
        ),
        db,
    )
    location = locations.create_location_endpoint(
        LocationCreate(aisle="A1", bin="B1"), db
    )
    initial_stock = StockOperation(
        product_id=product.id, location_id=location.id, quantity=100
    )
    stock.add_stock(initial_stock, db)

    # Act - Simulate concurrent operations
    op1 = StockOperation(product_id=product.id, location_id=location.id, quantity=30)
    op2 = StockOperation(product_id=product.id, location_id=location.id, quantity=40)

    stock.remove_stock(op1, db)
    stock.remove_stock(op2, db)

    # Assert
    final_stock = (
        db.query(MockStock)
        .filter(
            MockStock.product_id == product.id, MockStock.location_id == location.id
        )
        .first()
    )
    assert final_stock.quantity == 30  # 100 - 30 - 40


@pytest.mark.parametrize("invalid_quantity", [-1, 0])
def test_stock_invalid_quantity(db, invalid_quantity):
    """Should reject stock operations with invalid quantities."""
    # Arrange
    product = products.create_product_endpoint(
        ProductCreate(
            sku="INVALID-QTY", name="Test", category="Test", description="Test"
        ),
        db,
    )
    location = locations.create_location_endpoint(
        LocationCreate(aisle="A1", bin="B1"), db
    )

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        stock.add_stock(
            StockOperation(
                product_id=product.id,
                location_id=location.id,
                quantity=invalid_quantity,
            ),
            db,
        )
    assert exc_info.value.status_code == 400
