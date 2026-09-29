import logging
from importlib import import_module
from uuid import UUID
from typing import List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from src.modules.products.model import Product
from src.modules.products.schema import CreateProductRequest

logger = logging.getLogger(__name__)


class ProductService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _normalize_url(raw_url: str) -> str:
        parsed = urlparse(raw_url.strip())
        tracking_params = {
            "dclid", "fbclid", "gclid", "igshid", "mc_cid", "mc_eid",
            "msclkid", "yclid",
        }
        query_params = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() not in tracking_params and not key.lower().startswith("utm_")
        ]
        clean_path = parsed.path.rstrip("/")
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            clean_path,
            parsed.params,
            urlencode(query_params),
            "",
        ))

    @staticmethod
    def _enqueue_initial_price(product: Product) -> None:
        try:
            task_module = import_module("src.workers.ingestion_tasks")
        except ModuleNotFoundError as e:
            if e.name in {"src.workers", "src.workers.ingestion_tasks"}:
                logger.warning(
                    "Initial price worker is not configured; product_id=%s was saved without enqueueing",
                    product.id
                )
                return
            logger.exception("Unable to load the initial price worker")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo programar el análisis inicial del producto."
            ) from e
        except Exception as e:
            logger.exception("Unable to load the initial price worker")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo programar el análisis inicial del producto."
            ) from e

        task = getattr(task_module, "extract_initial_price_task", None)
        if task is None:
            logger.error("The initial price worker does not expose its Celery task")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo programar el análisis inicial del producto."
            )

        try:
            task.delay(product_id=str(product.id), url=product.url)
        except Exception as e:
            logger.exception("Unable to enqueue initial price extraction for product_id=%s", product.id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo programar el análisis inicial del producto."
            ) from e

    def create_product(self, user_id: UUID, product_in: CreateProductRequest) -> Product:
        normalized_url = self._normalize_url(str(product_in.product_url))
        try:
            existing = self.db.query(Product).filter(
                Product.user_id == user_id,
                Product.url == normalized_url
            ).first()

            if existing:
                if product_in.target_price is not None:
                    existing.target_price = product_in.target_price
                    self.db.commit()
                    self.db.refresh(existing)
                self._enqueue_initial_price(existing)
                return existing

            new_product = Product(
                user_id=user_id,
                url=normalized_url,
                target_price=product_in.target_price
            )
            self.db.add(new_product)
            self.db.commit()
            self.db.refresh(new_product)
            self._enqueue_initial_price(new_product)
            return new_product

        except IntegrityError:
            self.db.rollback()
            existing_concurrent = self.db.query(Product).filter(
                Product.user_id == user_id,
                Product.url == normalized_url
            ).first()

            if existing_concurrent:
                if product_in.target_price is not None:
                    existing_concurrent.target_price = product_in.target_price
                    self.db.commit()
                    self.db.refresh(existing_concurrent)
                try:
                    self._enqueue_initial_price(existing_concurrent)
                except HTTPException:
                    self.db.rollback()
                    raise
                return existing_concurrent

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

    def get_user_products(self, user_id: UUID, limit: int = 20) -> List[Product]:
        # Previene desbordamiento de paginación (Tope de 100 registros)
        safe_limit = max(1, min(limit, 100))
        try:
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
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al consultar la lista de productos: {str(e)}"
            ) from e