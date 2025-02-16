from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import Stock, Product, Location
from app.schemas import StockOperation, StockResponse
from app.services.notification import send_low_stock_alert  # new import

router = APIRouter()


@router.post("/inbound", response_model=StockResponse)
def add_stock(operation: StockOperation, db: Session = Depends(get_db)):
    if operation.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    # Convert IDs to integers
    prod_id = int(operation.product_id)
    loc_id = int(operation.location_id)
    # Verify product exists
    product = db.query(Product).filter(Product.id == prod_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    # Verify location exists
    location = db.query(Location).filter(Location.id == loc_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    stock = (
        db.query(Stock)
        .filter(
            Stock.product_id == prod_id,
            Stock.location_id == loc_id,
        )
        .first()
    )
    if stock:
        stock.quantity += operation.quantity  # type: ignore[assignment]
        stock.updated_at = datetime.utcnow()  # type: ignore
    else:
        stock = Stock(
            product_id=prod_id,
            location_id=loc_id,
            quantity=operation.quantity,
        )
        db.add(stock)

    db.commit()
    db.refresh(stock)
    # Trigger alert if low stock (<20)
    if stock.quantity < 20:
        send_low_stock_alert(stock)
    return stock


@router.post("/outbound", response_model=StockResponse)
def remove_stock(operation: StockOperation, db: Session = Depends(get_db)):
    if operation.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    # Convert IDs to integers
    prod_id = int(operation.product_id)
    loc_id = int(operation.location_id)
    stock = (
        db.query(Stock)
        .filter(
            Stock.product_id == prod_id,
            Stock.location_id == loc_id,
        )
        .first()
    )
    if not stock:
        raise HTTPException(
            status_code=404,
            detail="No stock found for this product at the specified location",
        )

    if stock.quantity < operation.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    stock.quantity -= operation.quantity  # type: ignore[assignment]
    stock.updated_at = datetime.utcnow()  # type: ignore
    db.commit()
    db.refresh(stock)
    # Trigger alert if low stock (<20)
    if stock.quantity < 20:
        send_low_stock_alert(stock)
    return stock


@router.get("/", response_model=List[StockResponse])
def list_stock(db: Session = Depends(get_db)):
    return db.query(Stock).all()
