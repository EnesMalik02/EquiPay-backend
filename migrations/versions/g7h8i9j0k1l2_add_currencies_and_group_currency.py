"""add_currencies_and_group_currency

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-04-28 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "currencies" not in inspector.get_table_names():
        op.create_table(
            "currencies",
            sa.Column("code", sa.String(10), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("symbol", sa.String(10), nullable=False),
            sa.Column("decimal_places", sa.Integer(), nullable=False, server_default="2"),
        )

    op.execute("""
        INSERT INTO currencies (code, name, symbol, decimal_places) VALUES
        ('TRY', 'Turkish Lira', '₺', 2),
        ('USD', 'US Dollar', '$', 2),
        ('EUR', 'Euro', '€', 2),
        ('JPY', 'Japanese Yen', '¥', 0)
        ON CONFLICT (code) DO NOTHING
    """)

    existing_cols = [c["name"] for c in inspector.get_columns("groups")]
    if "currency_code" not in existing_cols:
        op.add_column(
            "groups",
            sa.Column("currency_code", sa.String(10), nullable=True),
        )
        op.execute("UPDATE groups SET currency_code = 'TRY' WHERE currency_code IS NULL")
        op.alter_column("groups", "currency_code", nullable=False)
        op.create_foreign_key(
            "fk_groups_currency_code",
            "groups",
            "currencies",
            ["currency_code"],
            ["code"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_cols = [c["name"] for c in inspector.get_columns("groups")]
    if "currency_code" in existing_cols:
        op.drop_constraint("fk_groups_currency_code", "groups", type_="foreignkey")
        op.drop_column("groups", "currency_code")
    if "currencies" in inspector.get_table_names():
        op.drop_table("currencies")
