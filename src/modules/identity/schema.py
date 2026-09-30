# Archivo: src/modules/identity/schema.py
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from src.modules.identity.model import PlanType


class UserCreate(BaseModel):
    """Esquema para la creación/registro de un usuario."""
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Contraseña de entre 8 y 72 caracteres"
    )
class UserResponse(BaseModel):
    """Esquema de respuesta pública de datos de usuario."""
    id: UUID
    email: EmailStr
    plan_type: PlanType

    class Config:
        from_attributes = True  # Para compatibilidad con Pydantic v2 y SQLAlchemy (o orm_mode = True en v1)


class LoginRequest(BaseModel):
    """Esquema para la solicitud de autenticación."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Esquema de respuesta tras autenticación exitosa con JWT."""
    access_token: str
    token_type: str = "bearer"
    role: str