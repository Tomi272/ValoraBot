from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field, field_serializer


class AlertBase(BaseModel):
    target_price: float = Field(..., gt=0, description="Precio objetivo para la alerta")


class AlertCreate(AlertBase):
    pass


class AlertResponse(AlertBase):
    id: UUID
    user_id: UUID
    product_id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    url: HttpUrl = Field(..., description="URL válida del producto en e-commerce")

    @field_serializer("url")
    def serialize_url(self, url: HttpUrl, _info) -> str:
        return str(url)


class ProductCreate(ProductBase):
    target_price: float = Field(..., gt=0, description="Precio objetivo inicial")


class CreateProductRequest(BaseModel):
    product_url: HttpUrl = Field(..., description="URL válida del producto")
    target_price: Optional[float] = Field(default=None, gt=0, description="Precio objetivo inicial")


class ProductResponse(ProductBase):
    id: UUID
    title: Optional[str] = None
    current_price: Optional[float] = None
    target_price: Optional[float] = None
    created_at: datetime
    alert: Optional[AlertResponse] = None

    class Config:
        from_attributes = True