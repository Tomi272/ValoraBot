from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from src.core.database import Base

ROOT: Path = Path(__file__).resolve().parents[2]
EXPECTED_TABLES: set[str] = {"users", "products", "alerts", "price_history"}


@pytest.fixture
def alembic_cfg(tmp_path: Path) -> Config:
    cfg: Config = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path / 'migration.db'}")
    return cfg


def _tables(cfg: Config) -> set[str]:
    engine = create_engine(cfg.get_main_option("sqlalchemy.url") or "")
    try:
        return set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def test_there_is_a_single_head(alembic_cfg: Config) -> None:
    assert len(ScriptDirectory.from_config(alembic_cfg).get_heads()) == 1


def test_upgrade_head_creates_expected_tables(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    assert _tables(alembic_cfg) == EXPECTED_TABLES


def test_downgrade_base_removes_everything(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    assert _tables(alembic_cfg) == set()


def test_models_and_migrations_have_no_drift(alembic_cfg: Config) -> None:
    """Si alguien cambia un modelo sin generar migración, este test falla.

    compare_type=False: la reflexión de tipos en SQLite (UUID -> CHAR(32)) da falsos
    positivos. La comparación de tipos se verifica con `alembic check` contra PostgreSQL.
    """
    command.upgrade(alembic_cfg, "head")
    engine = create_engine(alembic_cfg.get_main_option("sqlalchemy.url") or "")
    try:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn, opts={"compare_type": False})
            assert compare_metadata(ctx, Base.metadata) == []
    finally:
        engine.dispose()


def test_alerts_constraints(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    engine = create_engine(alembic_cfg.get_main_option("sqlalchemy.url") or "")
    try:
        insp = inspect(engine)
        uq_names: set[str | None] = {u["name"] for u in insp.get_unique_constraints("alerts")}
        assert "uq_alerts_user_id_product_id" in uq_names
        ondelete: set[str | None] = {
            fk["options"].get("ondelete") for fk in insp.get_foreign_keys("alerts")
        }
        assert ondelete == {"CASCADE"}
    finally:
        engine.dispose()