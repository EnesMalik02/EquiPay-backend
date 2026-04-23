"""add_group_member_status_and_notifications

Revision ID: f6a7b8c9d0e1
Revises: e1f2a3b4c5d6
Create Date: 2026-04-23 00:00:00.000000

group_members tablosuna status alanı eklendi (active/pending).
notifications tablosu zaten varsa atla.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy import inspect


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str]] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # status kolonu yoksa ekle
    existing_cols = [c["name"] for c in inspector.get_columns("group_members")]
    if "status" not in existing_cols:
        op.add_column(
            "group_members",
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="active",
            ),
        )

    # notifications tablosu yoksa oluştur
    if "notifications" not in inspector.get_table_names():
        op.create_table(
            "notifications",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("type", sa.String(50), nullable=False),
            sa.Column("data", JSON, nullable=True),
            sa.Column(
                "is_read",
                sa.Boolean,
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "notifications" in inspector.get_table_names():
        op.drop_index("ix_notifications_user_id", table_name="notifications")
        op.drop_table("notifications")
    existing_cols = [c["name"] for c in inspector.get_columns("group_members")]
    if "status" in existing_cols:
        op.drop_column("group_members", "status")
