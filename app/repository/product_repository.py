from typing import Optional
from sqlalchemy.orm import Session
from app.models import Product


def get_by_id(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()


def get_by_sku(db: Session, sku: str) -> Optional[Product]:
    return db.query(Product).filter(Product.sku == sku).first()


def create_product(db: Session, product_data: dict) -> Product:
    product = Product(**product_data)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def list_products(db: Session):
    return db.query(Product).all()
