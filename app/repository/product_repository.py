from sqlalchemy.orm import Session
from app.models import Product

def get_by_id(db: Session, product_id: int) -> Product:
    return db.query(Product).filter(Product.id == product_id).first()

def get_by_sku(db: Session, sku: str) -> Product:
    return db.query(Product).filter(Product.sku == sku).first()

def create_product(db: Session, product_data: dict) -> Product:
    # No duplicate check here; controller must call get_by_sku beforehand.
    product = Product(**product_data)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

def list_products(db: Session):
    return db.query(Product).all()
