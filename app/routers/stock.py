from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Stock, Product, Location
from app.schemas import StockOperation, StockResponse
from datetime import datetime

router = APIRouter()

@router.post("/inbound", response_model=StockResponse)
def add_stock(operation: StockOperation, db: Session = Depends(get_db)):
    # Verify product exists
    product = db.query(Product).filter(Product.id == operation.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    # Verify location exists
    location = db.query(Location).filter(Location.id == operation.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    stock = db.query(Stock).filter(
        Stock.product_id == operation.product_id,
        Stock.location_id == operation.location_id
    ).first()
    if stock:
        stock.quantity += operation.quantity
        stock.updated_at = datetime.utcnow()
    else:
        stock = Stock(
            product_id=operation.product_id,
            location_id=operation.location_id,
            quantity=operation.quantity
        )
        db.add(stock)
    
    db.commit()
    db.refresh(stock)
    return stock

@router.post("/outbound", response_model=StockResponse)
def remove_stock(operation: StockOperation, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(
        Stock.product_id == operation.product_id,
        Stock.location_id == operation.location_id
    ).first()
    if not stock:
        raise HTTPException(status_code=404, detail="No stock found for this product at the specified location")
    
    if stock.quantity < operation.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    stock.quantity -= operation.quantity
    stock.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(stock)
    return stock

@router.get("/", response_model=List[StockResponse])
def list_stock(db: Session = Depends(get_db)):
    return db.query(Stock).all()
