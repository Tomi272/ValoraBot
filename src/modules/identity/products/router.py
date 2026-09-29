import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import get_current_user
from src.modules.identity.model import User
from src.modules.products.schema import CreateProductRequest, ProductResponse
from src.modules.products.service import ProductService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/products", tags=["Core Analytics & Pricing"])


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo producto para seguimiento"
)
def create_product(
    product_in: CreateProductRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ProductResponse:
    """Registra o asocia un producto para el usuario autenticado."""
    try:
        service = ProductService(db)
        return service.create_product(user_id=current_user.id, product_in=product_in)
    except HTTPException as he:
        if he.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.exception(
                "Fallo interno en create_product para user_id=%s: %s",
                current_user.id,
                he.detail
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al procesar el registro del producto. Contacte al administrador."
            ) from he
        raise
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        ) from ve
    except Exception as e:
        logger.exception(
            "Fallo crítico no controlado en create_product para user_id=%s: %s",
            current_user.id,
            str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al procesar el registro del producto. Contacte al administrador."
        ) from e


@router.get(
    "",
    response_model=List[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar productos monitoreados"
)
def list_products(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Cantidad máxima de registros (1-100)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[ProductResponse]:
    """Lista los productos monitoreados por el usuario autenticado."""
    try:
        service = ProductService(db)
        return service.get_user_products(user_id=current_user.id, limit=limit)
    except HTTPException as he:
        if he.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.exception(
                "Fallo interno en list_products para user_id=%s: %s",
                current_user.id,
                he.detail
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al consultar el catálogo de productos."
            ) from he
        raise
    except Exception as e:
        logger.exception(
            "Fallo crítico no controlado en list_products para user_id=%s: %s",
            current_user.id,
            str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al consultar el catálogo de productos."
        ) from e