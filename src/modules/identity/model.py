# Archivo: src/modules/identity/model.py
import uuid
from sqlalchemy import Column, String, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.core.database import Base # Asumiendo Base = declarative_base()
import enum

class PlanType(enum.Enum):
    CONSUMIDOR = "consumidor"
    DROPSHIPPER = "dropshipper"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    # Llave Primaria UUID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Índices y campos obligatorios
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    
    # Control de roles (RBAC)
    plan_type = Column(Enum(PlanType), default=PlanType.CONSUMIDOR, nullable=False)

    products = relationship("Product", back_populates="user", cascade="all, delete-orphan")