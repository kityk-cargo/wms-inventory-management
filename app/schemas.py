from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.utils import ISO_8601_UTC_FORMAT


class StrictBaseModel(BaseModel):
    class Config:
        extra = "forbid"
        json_encoders = {datetime: lambda dt: dt.strftime(ISO_8601_UTC_FORMAT)}


# STOCK MODELS
class StockOperation(StrictBaseModel):
    product_id: int = Field(..., example=1)
    location_id: int = Field(..., example=103)
    quantity: int = Field(..., example=50)


class StockResponse(StrictBaseModel):
    product_id: int = Field(..., example=1)
    location_id: int = Field(..., example=103)
    quantity: int = Field(..., example=50)

    class Config:
        orm_mode = True


# LOCATION MODELS
class LocationBase(StrictBaseModel):
    aisle: str = Field(..., example="B07")
    bin: str = Field(..., example="R42")


class LocationCreate(LocationBase):
    pass


class LocationResponse(LocationBase):
    id: int = Field(..., example=103)
    created_at: datetime = Field(..., example=datetime(2023, 1, 1, 0, 0, 0))

    class Config:
        orm_mode = True


# PRODUCT MODELS
class ProductBase(StrictBaseModel):
    sku: str = Field(..., example="EL-2745-89B")
    name: str = Field(..., example="LED Panel 40W")
    category: str = Field(..., example="Lighting Equipment")
    description: Optional[str] = Field(
        None, example="40W LED Panel, 600x600mm, 4000K, IP20"
    )


class ProductCreate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: int = Field(..., example=1)
    created_at: datetime = Field(..., example=datetime(2023, 1, 1, 0, 0, 0))
    updated_at: datetime = Field(..., example=datetime(2023, 1, 2, 0, 0, 0))

    class Config:
        orm_mode = True
