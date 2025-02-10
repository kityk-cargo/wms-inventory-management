from sqlalchemy import (
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    MetaData,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from datetime import datetime
from typing import List

metadata = MetaData(schema="wms_schema")


class Base(DeclarativeBase):
    metadata = metadata


class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"schema": "wms_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sku: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )  # new field
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    stock: Mapped[List["Stock"]] = relationship("Stock", back_populates="product")
    # Removed direct location relationship


class Stock(Base):
    __tablename__ = "stock"
    __table_args__ = (
        PrimaryKeyConstraint("product_id", "location_id", name="pk_stock"),
    )

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wms_schema.products.id"), nullable=False
    )
    location_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wms_schema.locations.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    product: Mapped["Product"] = relationship("Product", back_populates="stock")
    location: Mapped["Location"] = relationship("Location", back_populates="stock")


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = {"schema": "wms_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    aisle: Mapped[str] = mapped_column(String, nullable=False)
    bin: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    stock: Mapped[List["Stock"]] = relationship("Stock", back_populates="location")
