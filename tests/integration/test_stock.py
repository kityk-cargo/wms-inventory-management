import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Product, Location, Stock
from app.schemas import StockOperation

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


import sys

# Remove conflicting mock module if present
sys.modules.pop("tests.test_unit_inventory", None)

import importlib
import app.models

importlib.reload(app.models)
from app.models import Product, Location, Stock

import pytest
import uuid  # new import for unique SKU generation
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.schemas import StockOperation

pytestmark = pytest.mark.db  # mark all tests in this module as DB tests


@pytest.fixture
def sample_data(db_session: Session):
    unique_sku = "TESTSKU_" + str(uuid.uuid4())  # ensure unique SKU
    product = Product(
        sku=unique_sku,
        name="Test Product",
        category="Test Category",
        description="Test Description",
    )
    location = Location(aisle="A1", bin="B1")
    db_session.add(product)
    db_session.add(location)
    db_session.flush()  # assign IDs before commit
    db_session.commit()
    db_session.refresh(product)
    db_session.refresh(location)
    return product, location


def test_add_stock(client_with_db: TestClient, sample_data):
    product, location = sample_data
    response = client_with_db.post(
        "/stock/inbound",
        json={
            "product_id": int(product.id),
            "location_id": int(location.id),
            "quantity": 10,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == int(product.id)
    assert data["location_id"] == int(location.id)
    assert data["quantity"] == 10


def test_remove_stock(client_with_db: TestClient, sample_data):
    product, location = sample_data
    client_with_db.post(
        "/stock/inbound",
        json={
            "product_id": int(product.id),
            "location_id": int(location.id),
            "quantity": 10,
        },
    )
    response = client_with_db.post(
        "/stock/outbound",
        json={
            "product_id": int(product.id),
            "location_id": int(location.id),
            "quantity": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == int(product.id)
    assert data["location_id"] == int(location.id)
    assert data["quantity"] == 5


def test_list_stock(client_with_db: TestClient, sample_data):
    product, location = sample_data
    client_with_db.post(
        "/stock/inbound",
        json={
            "product_id": int(product.id),
            "location_id": int(location.id),
            "quantity": 10,
        },
    )
    response = client_with_db.get("/stock/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["product_id"] == int(product.id)
    assert data[0]["location_id"] == int(location.id)
    assert data[0]["quantity"] == 10
