# Archivo: src/modules/identity/model.py
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.modules.products.model import Alert

class PlanType(enum.Enum):
    CONSUMIDOR = "consumidor"
    DROPSHIPPER = "dropshipper"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    plan_type: Mapped[PlanType] = mapped_column(
        Enum(
            PlanType,
            name="plan_type",
            native_enum=False,
            length=32,
            values_callable=lambda enum_type: [member.value for member in enum_type],
            validate_strings=True,
        ),
        default=PlanType.CONSUMIDOR,
        server_default=PlanType.CONSUMIDOR.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    alerts: Mapped[list["Alert"]] = relationship(back_populates="user", cascade="all, delete-orphan")