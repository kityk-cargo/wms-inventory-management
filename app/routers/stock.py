from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import StockOperation, StockResponse
from app.services.notification import send_low_stock_alert
import app.repository.stock_repository as stock_repo
import app.repository.product_repository as product_repo
import app.repository.location_repository as location_repo

router = APIRouter()


@router.post("/inbound", response_model=StockResponse)
def add_stock(operation: StockOperation, db: Session = Depends(get_db)):
    if operation.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    product_id = operation.product_id  # renamed for clarity
    location_id = operation.location_id  # renamed for clarity
    product = product_repo.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    location = location_repo.get_by_id(db, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    stock = stock_repo.get_stock(db, product_id, location_id)
    if stock:
        stock = stock_repo.update_stock_quantity(db, stock, operation.quantity)
    else:
        stock_data = {
            "product_id": product_id,
            "location_id": location_id,
            "quantity": operation.quantity,
        }
        stock = stock_repo.create_stock(db, stock_data)
    if stock.quantity < 20:
        send_low_stock_alert(stock)
    return stock


@router.post("/outbound", response_model=StockResponse)
def remove_stock(operation: StockOperation, db: Session = Depends(get_db)):
    if operation.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    product_id = operation.product_id  # renamed for clarity
    location_id = operation.location_id  # renamed for clarity
    stock = stock_repo.get_stock(db, product_id, location_id)
    if not stock:
        raise HTTPException(
            status_code=404,
            detail="No stock found for this product at the specified location",
        )
    if stock.quantity < operation.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    stock = stock_repo.update_stock_quantity(db, stock, -operation.quantity)
    if stock.quantity < 20:
        send_low_stock_alert(stock)
    return stock


@router.get("/", response_model=List[StockResponse])
def list_stock_endpoint(db: Session = Depends(get_db)):
    return stock_repo.list_stock(db)
