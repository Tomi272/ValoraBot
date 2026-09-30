import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("JWT_SECRET_KEY", "t" * 48)

from typing import Callable, Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.database import Base, get_db
from src.main import app

import src.modules.identity.model  # noqa: F401
import src.modules.products.model  # noqa: F401

REGISTER_URL: str = "/api/v1/auth/register"
LOGIN_URL: str = "/api/v1/auth/login"
DEFAULT_PASSWORD: str = "Secreta123!"


class QueryCounter:
    def __init__(self) -> None:
        self.count: int = 0


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    """SQLite en memoria aislada por test y compartida entre hilos."""
    test_engine: Engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        session: Session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def mock_extraction_task(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Sustituye el task en el punto donde ProductService lo usa."""
    mock: MagicMock = MagicMock()
    monkeypatch.setattr("src.modules.products.service.extract_initial_price_task", mock)
    return mock


@pytest.fixture
def mock_celery_task(mock_extraction_task: MagicMock) -> MagicMock:
    """Compatibilidad con los tests existentes que usan el nombre anterior."""
    return mock_extraction_task.delay


@pytest.fixture
def create_auth_headers(client: TestClient) -> Callable[[str], dict[str, str]]:
    def _create(email: str) -> dict[str, str]:
        register_response = client.post(
            REGISTER_URL,
            json={"email": email, "password": DEFAULT_PASSWORD}
        )
        assert register_response.status_code == 201, register_response.text
        login_response = client.post(
            LOGIN_URL,
            json={"email": email, "password": DEFAULT_PASSWORD}
        )
        assert login_response.status_code == 200, login_response.text
        return {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    return _create


@pytest.fixture
def auth_headers(create_auth_headers: Callable[[str], dict[str, str]]) -> dict[str, str]:
    return create_auth_headers("ana@valorabot.com")


@pytest.fixture
def other_auth_headers(create_auth_headers: Callable[[str], dict[str, str]]) -> dict[str, str]:
    return create_auth_headers("beto@valorabot.com")


@pytest.fixture
def query_counter(engine: Engine) -> Generator[QueryCounter, None, None]:
    counter: QueryCounter = QueryCounter()

    def _before(conn, cursor, statement, parameters, context, executemany) -> None:  # type: ignore[no-untyped-def]
        counter.count += 1

    event.listen(engine, "before_cursor_execute", _before)
    yield counter
    event.remove(engine, "before_cursor_execute", _before)