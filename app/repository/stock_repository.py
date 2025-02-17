from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.models import Stock


def get_stock(db: Session, product_id: int, location_id: int) -> Optional[Stock]:
    return (
        db.query(Stock)
        .filter(Stock.product_id == product_id, Stock.location_id == location_id)
        .first()
    )


def create_stock(db: Session, stock_data: dict) -> Stock:
    stock = Stock(**stock_data)
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock


def update_stock_quantity(db: Session, stock: Stock, quantity_change: int) -> Stock:
    stock.quantity += quantity_change
    stock.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(stock)
    return stock


def list_stock(db: Session):
    return db.query(Stock).all()
