from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.schemas import ProductCreate, ProductResponse
import app.repository.product_repository as product_repo

router = APIRouter()

# Define Pydantic example instances
example_product_obj = ProductResponse(
    id=42,
    sku="EL-9999-01X",
    name="Super LED Panel 60W",
    category="Lighting Equipment",
    description="A high-end LED panel for industrial use",
    created_at=datetime(2023, 5, 5, 9, 0, 0),
    updated_at=datetime(2023, 5, 6, 10, 0, 0),
)

example_product_obj_alt = ProductResponse(
    id=43,
    sku="EL-1234-XY9",
    name="Eco LED Panel 40W",
    category="Lighting Equipment",
    description="Energy efficient 40W LED panel",
    created_at=datetime(2023, 4, 1, 8, 0, 0),
    updated_at=datetime(2023, 4, 2, 8, 30, 0),
)


@router.post("", response_model=ProductResponse)
def create_product_endpoint(product: ProductCreate, db: Session = Depends(get_db)):
    sku = product.sku.strip()
    name = product.name.strip()
    if not sku:
        raise HTTPException(status_code=400, detail="SKU cannot be empty")
    if product_repo.get_by_sku(db, sku):
        raise HTTPException(
            status_code=409, detail="Product with this SKU already exists"
        )
    if not name:
        raise HTTPException(status_code=400, detail="Product name cannot be empty")
    return product_repo.create_product(db, product.dict())


@router.get("/{product_id}", response_model=ProductResponse)
def get_product_endpoint(product_id: int, db: Session = Depends(get_db)):
    if product_id <= 0:
        raise HTTPException(status_code=404, detail="Invalid product ID")
    product = product_repo.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get(
    "",
    response_model=List[ProductResponse],
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "multiple_products": {
                            "value": [
                                example_product_obj.dict(),
                                example_product_obj_alt.dict(),
                            ]
                        }
                    }
                }
            }
        }
    },
)
def list_products_endpoint(db: Session = Depends(get_db)):
    return product_repo.list_products(db)
