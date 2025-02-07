from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, MetaData, PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

# Configure schema-aware metadata
metadata = MetaData(schema="wms_schema")
Base = declarative_base(metadata=metadata)

class Product(Base):
    __tablename__ = "products"
    __table_args__ = {'schema': 'wms_schema'}
    
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, nullable=False)  # new field
    name = Column(String, index=True, nullable=False)
    category = Column(String)
    description = Column(Text)  # new field
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    stock = relationship("Stock", back_populates="product")
    # Removed direct location relationship

class Stock(Base):
    __tablename__ = "stock"
    __table_args__ = (
        PrimaryKeyConstraint('product_id', 'location_id', name='pk_stock'),
    )
    
    product_id = Column(Integer, ForeignKey("wms_schema.products.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("wms_schema.locations.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    product = relationship("Product", back_populates="stock")
    location = relationship("Location", back_populates="stock")

class Location(Base):
    __tablename__ = "locations"
    __table_args__ = {'schema': 'wms_schema'}
    
    id = Column(Integer, primary_key=True, index=True)
    aisle = Column(String, nullable=False)
    bin = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    stock = relationship("Stock", back_populates="location")
