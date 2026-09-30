from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.modules.products.model import Product
from src.tests.conftest import QueryCounter

PRODUCTS_URL: str = "/api/v1/products"
ITEM_URL: str = "https://www.mercadolibre.com.ar/p/MLA1234567"

pytestmark = pytest.mark.usefixtures("mock_extraction_task")


def _create(
    client: TestClient,
    headers: dict[str, str],
    url: str = ITEM_URL,
    price: float | None = 15000.0,
) -> object:
    payload: dict[str, object] = {"product_url": url}
    if price is not None:
        payload["target_price"] = price
    return client.post(PRODUCTS_URL, json=payload, headers=headers)


def test_create_requires_authentication(client: TestClient) -> None:
    response = client.post(PRODUCTS_URL, json={"product_url": ITEM_URL})
    assert response.status_code == 401


def test_create_product_returns_201_with_contract(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = _create(client, auth_headers)
    assert response.status_code == 201
    body: dict = response.json()
    assert body["id"]
    assert body["url"].startswith(ITEM_URL)
    assert float(body["target_price"]) == 15000.0


def test_create_enqueues_extraction_exactly_once(
    client: TestClient,
    auth_headers: dict[str, str],
    mock_extraction_task: MagicMock,
) -> None:
    body: dict = _create(client, auth_headers).json()
    mock_extraction_task.delay.assert_called_once()
    kwargs: dict = mock_extraction_task.delay.call_args.kwargs
    assert kwargs["product_id"] == body["id"]
    assert kwargs["url"].startswith("https://www.mercadolibre.com.ar")


def test_create_survives_broker_outage(
    client: TestClient,
    auth_headers: dict[str, str],
    mock_extraction_task: MagicMock,
) -> None:
    """Redis caído no debe perder el producto ya persistido."""
    mock_extraction_task.delay.side_effect = ConnectionError("redis down")
    response = _create(client, auth_headers)
    assert response.status_code == 201
    assert len(client.get(PRODUCTS_URL, headers=auth_headers).json()) == 1


def test_create_same_url_twice_updates_price_without_duplicating(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _create(client, auth_headers, price=15000.0)
    response = _create(client, auth_headers, price=12000.0)
    assert response.status_code in (200, 201)
    items: list[dict] = client.get(PRODUCTS_URL, headers=auth_headers).json()
    assert len(items) == 1
    assert float(items[0]["target_price"]) == 12000.0


@pytest.mark.parametrize(
    "payload",
    [
        {"product_url": "no-es-url"},
        {"product_url": "javascript:alert(1)"},
        {"product_url": "ftp://tienda.com/item"},
        {"product_url": ITEM_URL, "target_price": -5},
        {"product_url": ITEM_URL, "target_price": 0},
        {"product_url": ITEM_URL, "target_price": "abc"},
        {},
    ],
)
def test_create_rejects_invalid_payloads(
    client: TestClient,
    auth_headers: dict[str, str],
    payload: dict,
) -> None:
    response = client.post(PRODUCTS_URL, json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_create_without_target_price_is_allowed(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    assert _create(client, auth_headers, price=None).status_code == 201


def test_list_requires_authentication(client: TestClient) -> None:
    assert client.get(PRODUCTS_URL).status_code == 401


def test_list_only_returns_own_products(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    """Aislamiento entre usuarios (previene IDOR)."""
    _create(client, auth_headers, url="https://tienda.com/item/1")
    _create(client, other_auth_headers, url="https://tienda.com/item/2")
    mine: list[dict] = client.get(PRODUCTS_URL, headers=auth_headers).json()
    assert len(mine) == 1
    assert mine[0]["url"].endswith("/item/1")


def test_list_is_ordered_newest_first(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    for index in range(3):
        _create(client, auth_headers, url=f"https://tienda.com/item/{index}")
    items: list[dict] = client.get(PRODUCTS_URL, headers=auth_headers).json()
    assert [product["url"].rsplit("/", 1)[-1] for product in items] == ["2", "1", "0"]


def test_list_respects_limit(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    for index in range(3):
        _create(client, auth_headers, url=f"https://tienda.com/item/{index}")
    response = client.get(f"{PRODUCTS_URL}?limit=2", headers=auth_headers)
    assert len(response.json()) == 2


@pytest.mark.parametrize("limit", [0, -1, 101])
def test_list_rejects_out_of_range_limit(
    client: TestClient,
    auth_headers: dict[str, str],
    limit: int,
) -> None:
    response = client.get(f"{PRODUCTS_URL}?limit={limit}", headers=auth_headers)
    assert response.status_code == 422


def test_list_does_not_have_n_plus_one(
    client: TestClient,
    auth_headers: dict[str, str],
    query_counter: QueryCounter,
) -> None:
    """La cantidad de queries debe ser constante, sin importar cuántos productos haya."""
    _create(client, auth_headers, url="https://tienda.com/item/0")
    query_counter.count = 0
    client.get(PRODUCTS_URL, headers=auth_headers)
    queries_with_one: int = query_counter.count

    for index in range(1, 6):
        _create(client, auth_headers, url=f"https://tienda.com/item/{index}")
    query_counter.count = 0
    client.get(PRODUCTS_URL, headers=auth_headers)
    assert query_counter.count == queries_with_one


def test_deleting_user_cascades_to_products(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    from src.modules.identity.model import User

    _create(client, auth_headers)
    assert db_session.query(Product).count() == 1
    db_session.delete(db_session.query(User).first())
    db_session.commit()
    assert db_session.query(Product).count() == 0