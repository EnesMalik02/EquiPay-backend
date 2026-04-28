"""add_updated_at_to_expense_splits

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-04-28 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_cols = [c["name"] for c in inspector.get_columns("expense_splits")]
    if "updated_at" not in existing_cols:
        op.add_column(
            "expense_splits",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("now()"),
            ),
        )
        op.execute("UPDATE expense_splits SET updated_at = created_at WHERE updated_at IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_cols = [c["name"] for c in inspector.get_columns("expense_splits")]
    if "updated_at" in existing_cols:
        op.drop_column("expense_splits", "updated_at")
