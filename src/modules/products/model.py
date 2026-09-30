import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.modules.identity.model import User


class Product(Base):
    """Producto global: una URL se extrae una sola vez, sin importar sus seguidores."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True)
    domain: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[Optional[str]] = mapped_column(String(500))
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    min_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    alerts: Mapped[list["Alert"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    price_histories: Mapped[list["PriceHistory"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class PriceHistory(Base):
    __tablename__ = "price_history"

    __table_args__ = (Index("ix_price_history_product_id_scraped_at", "product_id", "scraped_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="ARS", server_default="ARS")
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped[Product] = relationship(back_populates="price_histories")


class Alert(Base):
    """Regla de umbral de un usuario sobre un producto global."""

    __tablename__ = "alerts"

    __table_args__ = (
        UniqueConstraint("user_id", "product_id"),
        CheckConstraint("target_price IS NULL OR target_price > 0", name="target_price_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    target_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    target_variation_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    channel: Mapped[str] = mapped_column(String(32), default="telegram", server_default="telegram")
    webhook_url: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="alerts")
    product: Mapped[Product] = relationship(back_populates="alerts")