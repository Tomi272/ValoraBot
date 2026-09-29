# Archivo: tests/test_products.py
import pytest
from fastapi import status
from src.modules.products.service import ProductService


def test_create_product_unauthorized(client):
    """Verifica que la creación de producto requiera autenticación previa (HTTP 401)."""
    payload = {"product_url": "https://www.mercadolibre.com.ar/p/MLA123456"}
    response = client.post("/api/v1/products", json=payload)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_product_success_and_triggers_redis(client, auth_headers, mock_celery_task):
    """Verifica la creación del producto y la emisión inmediata del mensaje a Redis/Celery."""
    payload = {
        "product_url": "https://www.tienda.com/producto/123?utm_source=facebook#reviews",
        "target_price": 12500.50
    }
    
    response = client.post("/api/v1/products", json=payload, headers=auth_headers)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    
    # Normalización de la URL (limpieza de utm y fragmentos)
    assert data["url"] == "https://www.tienda.com/producto/123"
    assert float(data["target_price"]) == 12500.50

    # Confirmar que la tarea de Celery/Redis fue disparada
    assert mock_celery_task.called
    assert mock_celery_task.call_count == 1


def test_url_normalization_unit_test():
    """Prueba unitaria aislada para la función de normalización de URLs."""
    raw_url = "https://www.amazon.com/dp/B08N5WRWNW/?ref_=ast_sto_dp&th=1#customerReviews"
    expected = "https://www.amazon.com/dp/B08N5WRWNW"
    
    normalized = ProductService._normalize_url(raw_url)
    assert normalized == expected


def test_list_products_limit_validation(client, auth_headers):
    """Verifica la paginación y la restricción del límite máximo permitido (1-100)."""
    # Límite fuera de rango superior
    response = client.get("/api/v1/products?limit=101", headers=auth_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Límite dentro de rango válido
    response_valid = client.get("/api/v1/products?limit=10", headers=auth_headers)
    assert response_valid.status_code == status.HTTP_200_OK
    assert isinstance(response_valid.json(), list)