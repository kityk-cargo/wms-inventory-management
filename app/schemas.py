from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StockOperation(BaseModel):
    product_id: int
    location_id: int
    quantity: int


class LocationBase(BaseModel):
    aisle: str
    bin: str


class LocationCreate(BaseModel):
    aisle: str
    bin: str


class LocationResponse(BaseModel):
    id: int
    aisle: str
    bin: str
    created_at: datetime

    class Config:
        orm_mode = True


class StockResponse(BaseModel):
    product_id: int
    location_id: int
    quantity: int

    class Config:
        orm_mode = True


class ProductCreate(BaseModel):
    sku: str
    name: str
    category: str
    description: Optional[str] = None


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
