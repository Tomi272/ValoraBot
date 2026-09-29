# Archivo: tests/conftest.py
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from unittest.mock import patch

from src.main import app
from src.core.database import Base, get_db
from src.core.security import create_access_token

# Base de datos SQLite en memoria para ejecución rápida de tests aislados
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Crea la estructura de tablas en la BD de pruebas al iniciar la sesión."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Proporciona una sesión de BD limpia por cada test con Rollback automático."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Sobreescribe la dependencia get_db de FastAPI y retorna el TestClient."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_celery_task():
    """Mockea la llamada al encolador de Redis / Celery."""
    with patch("src.modules.products.service.extract_initial_price_task.delay") as mock_delay:
        yield mock_delay


@pytest.fixture
def auth_headers(db_session: Session) -> dict:
    """Crea un usuario ficticio de prueba y retorna la cabecera Authorization Bearer."""
    from src.modules.identity.model import User, PlanType
    from src.core.security import get_password_hash
    import uuid

    user_id = uuid.uuid4()
    test_user = User(
        id=user_id,
        email="test.user@valorabot.io",
        password_hash=get_password_hash("SecretPass123!"),
        plan_type=PlanType.CONSUMIDOR
    )
    db_session.add(test_user)
    db_session.commit()

    token = create_access_token(data={"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}