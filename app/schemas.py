from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.utils import ISO_8601_UTC_FORMAT


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_encoders={datetime: lambda dt: dt.strftime(ISO_8601_UTC_FORMAT)},
    )


# STOCK MODELS
class StockOperation(StrictBaseModel):
    product_id: int = Field(..., json_schema_extra={"example": 1})
    location_id: int = Field(..., json_schema_extra={"example": 103})
    quantity: int = Field(..., json_schema_extra={"example": 50})


class StockResponse(StrictBaseModel):
    product_id: int = Field(..., json_schema_extra={"example": 1})
    location_id: int = Field(..., json_schema_extra={"example": 103})
    quantity: int = Field(..., json_schema_extra={"example": 50})

    model_config = ConfigDict(from_attributes=True)


# LOCATION MODELS
class LocationBase(StrictBaseModel):
    aisle: str = Field(..., json_schema_extra={"example": "B07"})
    bin: str = Field(..., json_schema_extra={"example": "R42"})


class LocationCreate(LocationBase):
    pass


class LocationResponse(LocationBase):
    id: int = Field(..., json_schema_extra={"example": 103})
    created_at: datetime = Field(
        ..., json_schema_extra={"example": "2023-01-01T00:00:00Z"}
    )

    model_config = ConfigDict(from_attributes=True)


# PRODUCT MODELS
class ProductBase(StrictBaseModel):
    sku: str = Field(..., json_schema_extra={"example": "EL-2745-89B"})
    name: str = Field(..., json_schema_extra={"example": "LED Panel 40W"})
    category: str = Field(..., json_schema_extra={"example": "Lighting Equipment"})
    description: Optional[str] = Field(
        None, json_schema_extra={"example": "40W LED Panel, 600x600mm, 4000K, IP20"}
    )


class ProductCreate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: int = Field(..., json_schema_extra={"example": 1})
    created_at: datetime = Field(
        ..., json_schema_extra={"example": "2023-01-01T00:00:00Z"}
    )
    updated_at: datetime = Field(
        ..., json_schema_extra={"example": "2023-01-02T00:00:00Z"}
    )

    model_config = ConfigDict(from_attributes=True)
