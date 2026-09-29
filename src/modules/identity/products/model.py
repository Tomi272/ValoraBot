import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Boolean, DateTime, ForeignKey, BigInteger, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    title = Column(String(500), nullable=True)
    target_price = Column(Numeric(12, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Restricción única compuesta para evitar duplicados por usuario
    __table_args__ = (
        UniqueConstraint('user_id', 'url', name='uq_user_product_url'),
    )

    user = relationship("User", back_populates="products")
    price_histories = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    alert_rules = relationship("AlertRule", back_populates="product", cascade="all, delete-orphan")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default='USD')
    scraped_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    product = relationship("Product", back_populates="price_histories")


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    threshold_percentage = Column(Numeric(5, 2), nullable=True)
    channel = Column(String(50), nullable=False)
    channel_destination = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)

    product = relationship("Product", back_populates="alert_rules")