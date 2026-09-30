import logging
from datetime import datetime
from uuid import UUID
from typing import List
from urllib.parse import urlparse, urlunparse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from src.modules.products.model import Alert, PriceHistory, Product
from src.modules.products.schema import CreateProductRequest, ProductResponse

logger = logging.getLogger(__name__)

try:
    from src.workers.ingestion_tasks import extract_initial_price_task
except ModuleNotFoundError as e:
    if e.name not in {"celery", "src.workers", "src.workers.ingestion_tasks"}:
        raise
    extract_initial_price_task = None


class ProductService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _normalize_url(raw_url: str) -> str:
        parsed = urlparse(raw_url.strip())
        clean_path = parsed.path.rstrip("/")
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            clean_path,
            "",
            "",
            "",
        ))

    @staticmethod
    def _enqueue_initial_price(product: Product) -> None:
        if extract_initial_price_task is None:
            logger.warning(
                "Initial price worker is not configured; product_id=%s was saved without enqueueing",
                product.id
            )
            return

        try:
            extract_initial_price_task.delay(product_id=str(product.id), url=product.url)
        except Exception:
            logger.exception("Unable to enqueue initial price extraction for product_id=%s", product.id)

    @staticmethod
    def _to_response(product: Product, alert: Alert) -> ProductResponse:
        latest_price: PriceHistory | None = max(
            product.price_histories,
            key=lambda history: history.scraped_at or datetime.min,
            default=None,
        )
        return ProductResponse(
            id=product.id,
            url=product.url,
            title=product.title,
            current_price=latest_price.price if latest_price is not None else None,
            target_price=alert.target_price,
            created_at=product.created_at,
            alert=alert,
        )

    def create_product(self, user_id: UUID, product_in: CreateProductRequest) -> ProductResponse:
        normalized_url = self._normalize_url(str(product_in.product_url))
        created_product = False
        try:
            product = self.db.query(Product).filter(Product.url == normalized_url).first()
            if product is None:
                product = Product(url=normalized_url)
                self.db.add(product)
                self.db.flush()
                created_product = True

            alert = self.db.query(Alert).filter(
                Alert.user_id == user_id,
                Alert.product_id == product.id,
            ).first()
            if alert is None:
                alert = Alert(
                    user_id=user_id,
                    product_id=product.id,
                    target_price=product_in.target_price,
                )
                self.db.add(alert)
            elif product_in.target_price is not None:
                alert.target_price = product_in.target_price

            self.db.commit()
            self.db.refresh(product)
            self.db.refresh(alert)
            if created_product:
                self._enqueue_initial_price(product)
            return self._to_response(product, alert)

        except IntegrityError:
            self.db.rollback()
            concurrent_product = self.db.query(Product).filter(Product.url == normalized_url).first()
            if concurrent_product is not None:
                concurrent_alert = self.db.query(Alert).filter(
                    Alert.user_id == user_id,
                    Alert.product_id == concurrent_product.id,
                ).first()
                if concurrent_alert is not None:
                    if product_in.target_price is not None:
                        concurrent_alert.target_price = product_in.target_price
                    self.db.commit()
                    self.db.refresh(concurrent_alert)
                    return self._to_response(concurrent_product, concurrent_alert)

                concurrent_alert = Alert(
                    user_id=user_id,
                    product_id=concurrent_product.id,
                    target_price=product_in.target_price,
                )
                self.db.add(concurrent_alert)
                try:
                    self.db.commit()
                    self.db.refresh(concurrent_alert)
                    return self._to_response(concurrent_product, concurrent_alert)
                except IntegrityError:
                    self.db.rollback()
                    concurrent_alert = self.db.query(Alert).filter(
                        Alert.user_id == user_id,
                        Alert.product_id == concurrent_product.id,
                    ).first()
                    if concurrent_alert is not None:
                        if product_in.target_price is not None:
                            concurrent_alert.target_price = product_in.target_price
                        self.db.commit()
                        self.db.refresh(concurrent_alert)
                        return self._to_response(concurrent_product, concurrent_alert)

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflicto de concurrencia al registrar la URL. Intente nuevamente."
            )
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.exception("Unexpected error while creating product for user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al procesar el producto."
            ) from e

    def get_user_products(self, user_id: UUID, limit: int = 20) -> List[ProductResponse]:
        # Previene desbordamiento de paginación (Tope de 100 registros)
        safe_limit = max(1, min(limit, 100))
        try:
            rows = (
                self.db.query(Product, Alert)
                .join(Alert, Alert.product_id == Product.id)
                .options(selectinload(Product.price_histories))
                .filter(Alert.user_id == user_id)
                .order_by(Alert.created_at.desc())
                .limit(safe_limit)
                .all()
            )
            return [self._to_response(product, alert) for product, alert in rows]
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al consultar la lista de productos: {str(e)}"
            ) from e