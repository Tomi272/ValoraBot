"""initial schema: users, products, alerts, price_history

Revision ID: 0001
Revises:
Create Date: 2026-09-29
"""
from typing import Optional, Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Optional[str] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("plan_type", sa.String(32), nullable=False, server_default="consumidor"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.String(64), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("current_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("min_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("url_hash", name=op.f("uq_products_url_hash")),
    )
    op.create_index(op.f("ix_products_domain"), "products", ["domain"], unique=False)

    op.create_table(
        "price_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ARS"),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"],
            name=op.f("fk_price_history_product_id_products"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_history")),
    )
    op.create_index(
        op.f("ix_price_history_product_id_scraped_at"),
        "price_history",
        ["product_id", "scraped_at"],
        unique=False,
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("target_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("target_variation_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("channel", sa.String(32), nullable=False, server_default="telegram"),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_triggered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_alerts_user_id_users"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"],
            name=op.f("fk_alerts_product_id_products"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
        sa.UniqueConstraint("user_id", "product_id", name=op.f("uq_alerts_user_id_product_id")),
        sa.CheckConstraint(
            "target_price IS NULL OR target_price > 0",
            name=op.f("ck_alerts_target_price_positive"),
        ),
    )
    op.create_index(op.f("ix_alerts_product_id"), "alerts", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_alerts_product_id"), table_name="alerts")
    op.drop_table("alerts")
    op.drop_index(op.f("ix_price_history_product_id_scraped_at"), table_name="price_history")
    op.drop_table("price_history")
    op.drop_index(op.f("ix_products_domain"), table_name="products")
    op.drop_table("products")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")