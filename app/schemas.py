from pydantic import BaseModel, Field  # Updated import: added Field
from typing import Optional
from datetime import datetime


class StrictBaseModel(BaseModel):
    class Config:
        extra = "forbid"


class StockOperation(StrictBaseModel):
    product_id: int = Field(..., example=1)
    location_id: int = Field(..., example=103)
    quantity: int = Field(..., example=50)


class LocationBase(StrictBaseModel):
    aisle: str = Field(..., example="B07")
    bin: str = Field(..., example="R42")


class LocationCreate(StrictBaseModel):
    aisle: str = Field(..., example="B07")
    bin: str = Field(..., example="R42")


class LocationResponse(StrictBaseModel):
    id: int = Field(..., example=103)
    aisle: str = Field(..., example="B07")
    bin: str = Field(..., example="R42")
    created_at: datetime = Field(..., example=datetime(2023, 1, 1, 0, 0, 0))

    class Config:
        orm_mode = True


class StockResponse(StrictBaseModel):
    product_id: int = Field(..., example=1)
    location_id: int = Field(..., example=103)
    quantity: int = Field(..., example=50)

    class Config:
        orm_mode = True


class ProductCreate(StrictBaseModel):
    sku: str = Field(..., example="EL-2745-89B")
    name: str = Field(..., example="LED Panel 40W")
    category: str = Field(..., example="Lighting Equipment")
    description: Optional[str] = Field(
        None, example="40W LED Panel, 600x600mm, 4000K, IP20"
    )


class ProductResponse(StrictBaseModel):
    id: int = Field(..., example=1)
    sku: str = Field(..., example="EL-2745-89B")
    name: str = Field(..., example="LED Panel 40W")
    category: str = Field(..., example="Lighting Equipment")
    description: Optional[str] = Field(
        None, example="40W LED Panel, 600x600mm, 4000K, IP20"
    )
    created_at: datetime = Field(..., example=datetime(2023, 1, 1, 0, 0, 0))
    updated_at: datetime = Field(..., example=datetime(2023, 1, 2, 0, 0, 0))

    class Config:
        orm_mode = True
