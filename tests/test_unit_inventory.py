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
    # For updates, we simulate updated_at in add_stock implicitly if needed.
    updated_at = Column("updated_at")

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if self.quantity is None:
            self.quantity = 0

# Replace original model imports with mocks
products.Product = MockProduct
locations.Location = MockLocation
stock.Stock = MockStock
stock.Product = MockProduct    # <--- added line
stock.Location = MockLocation  # <--- added line

# InMemoryDB and QuerySimulator
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
        pass

    def refresh(self, obj):
        pass

class QuerySimulator:
    def __init__(self, data):
        self.data = data

    def filter(self, *conditions):
        filtered_data = self.data
        for cond in conditions:
            # Expect condition as tuple: (field_name, expected_value)
            if isinstance(cond, tuple) and len(cond)==2:
                field, expected = cond
                filtered_data = [item for item in filtered_data if getattr(item, field) == expected]
            else:
                # Fallback to no filtering if condition not tuple
                pass
        return QuerySimulator(filtered_data)

    def first(self):
        return self.data[0] if self.data else None

    def all(self):
        return self.data

@pytest.fixture
def db():
    return InMemoryDB()

# Product Tests
@pytest.mark.parametrize("product_data", [
    {"sku": "TEST001", "name": "Test Product 1", "category": "Test Cat", "description": "Test Desc"},
    {"sku": "TEST002", "name": "Test Product 2", "category": "Test Cat 2", "description": None},
])
def test_create_product(db, product_data):
    product_in = ProductCreate(**product_data)
    result = products.create_product(product_in, db)
    assert result.id is not None
    assert result.sku == product_data["sku"]
    assert result.name == product_data["name"]
    assert result.created_at is not None

def test_get_nonexistent_product(db):
    with pytest.raises(HTTPException) as exc_info:
        products.get_product(999, db)
    assert exc_info.value.status_code == 404

# Location Tests
@pytest.mark.parametrize("location_data", [
    {"aisle": "A1", "bin": "B1"},
    {"aisle": "A2", "bin": "B2"},
])
def test_create_location(db, location_data):
    location_in = LocationCreate(**location_data)
    result = locations.create_location(location_in, db)
    assert result.id is not None
    assert result.aisle == location_data["aisle"]
    assert result.bin == location_data["bin"]

def test_create_duplicate_location(db):
    loc_data = {"aisle": "A1", "bin": "B1"}
    locations.create_location(LocationCreate(**loc_data), db)
    with pytest.raises(HTTPException) as exc_info:
        locations.create_location(LocationCreate(**loc_data), db)
    assert exc_info.value.status_code == 400

# Stock Tests
@pytest.mark.parametrize("quantity", [1, 5, 10])
def test_add_stock(db, quantity):
    product = products.create_product(
        ProductCreate(sku=f"SKU{quantity}", name="Test", category="Test", description="Test"),
        db
    )
    location = locations.create_location(LocationCreate(aisle="A1", bin="B1"), db)
    operation = StockOperation(product_id=product.id, location_id=location.id, quantity=quantity)
    result = stock.add_stock(operation, db)
    assert result.quantity == quantity

def test_remove_stock_insufficient(db):
    product = products.create_product(
        ProductCreate(sku="SKU_TEST", name="Test", category="Test", description="Test"),
        db
    )
    location = locations.create_location(LocationCreate(aisle="A1", bin="B1"), db)
    stock.add_stock(StockOperation(product_id=product.id, location_id=location.id, quantity=5), db)
    with pytest.raises(HTTPException) as exc_info:
        stock.remove_stock(StockOperation(product_id=product.id, location_id=location.id, quantity=10), db)
    assert exc_info.value.status_code == 400

@pytest.mark.parametrize("initial,remove,expected", [
    (10, 5, 5),
    (5, 5, 0),
    (15, 7, 8),
])
def test_stock_operations(db, initial, remove, expected):
    product = products.create_product(
        ProductCreate(sku=f"SKU_OP_{initial}", name="Test", category="Test", description="Test"),
        db
    )
    location = locations.create_location(LocationCreate(aisle="A1", bin="B1"), db)
    stock.add_stock(StockOperation(product_id=product.id, location_id=location.id, quantity=initial), db)
    result = stock.remove_stock(StockOperation(product_id=product.id, location_id=location.id, quantity=remove), db)
    assert result.quantity == expected
