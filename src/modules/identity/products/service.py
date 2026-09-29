from uuid import UUID
from typing import List
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from src.modules.products.model import Product
from src.modules.products.schema import CreateProductRequest


class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def create_product(self, user_id: UUID, product_in: CreateProductRequest) -> Product:
        url_str = str(product_in.product_url)
        try:
            existing = self.db.query(Product).filter(
                Product.user_id == user_id,
                Product.url == url_str
            ).first()

            if existing:
                if product_in.target_price is not None:
                    existing.target_price = product_in.target_price
                    self.db.commit()
                    self.db.refresh(existing)
                return existing

            new_product = Product(
                user_id=user_id,
                url=url_str,
                target_price=product_in.target_price
            )
            self.db.add(new_product)
            self.db.commit()
            self.db.refresh(new_product)
            return new_product

        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un registro activo para esta URL bajo su usuario."
            )
        except Exception:
            self.db.rollback()
            raise

    def get_user_products(self, user_id: UUID, limit: int = 20) -> List[Product]:
        # Previene desbordamiento de paginación (Tope de 100 registros)
        safe_limit = max(1, min(limit, 100))
        return (
            self.db.query(Product)
            .options(
                selectinload(Product.price_histories),
                selectinload(Product.alert_rules)
            )
            .filter(Product.user_id == user_id)
            .order_by(Product.created_at.desc())
            .limit(safe_limit)
            .all()
        )