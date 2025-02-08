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

# InMemoryDB and QuerySimulator simulate basic DB operations.
class InMemoryDB:
    def __init__(self):
        self.data = {
            'products': {},
            'locations': {},
            'stock': {}
        }
        self._id_counter = {'products': 1, 'locations': 1}

    def query(self, model):
        if model == MockProduct:
            return QuerySimulator(list(self.data['products'].values()))
        elif model == MockLocation:
            return QuerySimulator(list(self.data['locations'].values()))
        elif model == MockStock:
            return QuerySimulator(list(self.data['stock'].values()))
        return QuerySimulator([])

    def add(self, obj):
        if isinstance(obj, MockProduct):
            obj.id = self._id_counter['products']
            obj.created_at = datetime.utcnow()
            obj.updated_at = datetime.utcnow()
            self.data['products'][obj.id] = obj
            self._id_counter['products'] += 1
        elif isinstance(obj, MockLocation):
            obj.id = self._id_counter['locations']
            obj.created_at = datetime.utcnow()
            self.data['locations'][obj.id] = obj
            self._id_counter['locations'] += 1
        elif isinstance(obj, MockStock):
            key = (obj.product_id, obj.location_id)
            self.data['stock'][key] = obj

    def commit(self):
        # Simulated commit.
        pass

    def refresh(self, obj):
        # Simulated refresh.
        pass

class QuerySimulator:
    def __init__(self, data):
        self.data = data

    def filter(self, *conditions):
        filtered_data = self.data
        for cond in conditions:
            if isinstance(cond, tuple) and len(cond)==2:
                field, expected = cond
                filtered_data = [item for item in filtered_data if getattr(item, field) == expected]
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
@pytest.mark.parametrize("product_data", [
    pytest.param({"sku": "TEST001", "name": "Test Product 1", "category": "Test Cat", "description": "Test Desc"}, id="Product with full details"),
    pytest.param({"sku": "TEST002", "name": "Test Product 2", "category": "Test Cat 2", "description": None}, id="Product with missing description"),
])
def test_create_product(db, product_data):
    """Should successfully create a product with the given valid data."""
    product_in = ProductCreate(**product_data)
    result = products.create_product(product_in, db)
    assert result.id is not None
    assert result.sku == product_data["sku"]
    assert result.name == product_data["name"]
    assert result.created_at is not None

def test_get_nonexistent_product(db):
    """Should raise a 404 error when attempting to retrieve a non-existent product."""
    with pytest.raises(HTTPException) as exc_info:
        products.get_product(999, db)
    assert exc_info.value.status_code == 404

# ---------------------- Location Tests ----------------------
@pytest.mark.parametrize("location_data", [
    pytest.param({"aisle": "A1", "bin": "B1"}, id="Valid location A1-B1"),
    pytest.param({"aisle": "A2", "bin": "B2"}, id="Valid location A2-B2"),
])
def test_create_location(db, location_data):
    """Should successfully create a location when provided valid data."""
    location_in = LocationCreate(**location_data)
    result = locations.create_location(location_in, db)
    assert result.id is not None
    assert result.aisle == location_data["aisle"]
    assert result.bin == location_data["bin"]

def test_create_duplicate_location(db):
    """Should raise a 400 error when creating a duplicate location."""
    loc_data = {"aisle": "A1", "bin": "B1"}
    locations.create_location(LocationCreate(**loc_data), db)
    with pytest.raises(HTTPException) as exc_info:
        locations.create_location(LocationCreate(**loc_data), db)
    assert exc_info.value.status_code == 400

# ---------------------- Stock Tests ----------------------
@pytest.mark.parametrize("quantity", [
    pytest.param(1, id="Add 1 unit of stock"),
    pytest.param(5, id="Add 5 units of stock"),
    pytest.param(10, id="Add 10 units of stock"),
])
def test_add_stock(db, quantity):
    """Should successfully add stock to a location for a product."""
    product = products.create_product(
        ProductCreate(sku=f"SKU{quantity}", name="Test", category="Test", description="Test"),
        db
    )
    location = locations.create_location(LocationCreate(aisle="A1", bin="B1"), db)
    operation = StockOperation(product_id=product.id, location_id=location.id, quantity=quantity)
    result = stock.add_stock(operation, db)
    assert result.quantity == quantity

def test_remove_stock_insufficient(db):
    """Should raise a 400 error when trying to remove more stock than available."""
    product = products.create_product(
        ProductCreate(sku="SKU_TEST", name="Test", category="Test", description="Test"),
        db
    )
    location = locations.create_location(LocationCreate(aisle="A1", bin="B1"), db)
    stock.add_stock(StockOperation(product_id=product.id, location_id=location.id, quantity=5), db)
    with pytest.raises(HTTPException) as exc_info:
        stock.remove_stock(StockOperation(product_id=product.id, location_id=location.id, quantity=10), db)
    assert exc_info.value.status_code == 400

@pytest.mark.parametrize("initial, remove, expected", [
    pytest.param(5, 5, 0, id="Remove all stock resulting in zero"),
    pytest.param(15, 7, 8, id="Remove stock leaving a positive remainder"),
])
def test_stock_operations(db, initial, remove, expected):
    """Should update the stock correctly after adding and then removing a specific quantity."""
    product = products.create_product(
        ProductCreate(sku=f"SKU_OP_{initial}", name="Test", category="Test", description="Test"),
        db
    )
    location = locations.create_location(LocationCreate(aisle="A1", bin="B1"), db)
    stock.add_stock(StockOperation(product_id=product.id, location_id=location.id, quantity=initial), db)
    result = stock.remove_stock(StockOperation(product_id=product.id, location_id=location.id, quantity=remove), db)
    assert result.quantity == expected
