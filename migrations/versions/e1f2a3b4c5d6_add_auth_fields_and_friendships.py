"""add_auth_fields_and_friendships

Revision ID: e1f2a3b4c5d6
Revises: 248992902c36
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "248992902c36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Mevcut test verilerini temizle (email alanı olmayan eski kullanıcılar)
    op.execute("DELETE FROM expense_splits")
    op.execute("DELETE FROM expenses")
    op.execute("DELETE FROM settlements")
    op.execute("DELETE FROM group_members")
    op.execute("DELETE FROM groups")
    op.execute("DELETE FROM users")

    # ── users ────────────────────────────────────────────────────
    # username artık opsiyonel — nullable yap
    op.alter_column("users", "username", existing_type=sa.String(100), nullable=True)

    op.add_column("users", sa.Column("email", sa.String(255), nullable=False, server_default=""))
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=False, server_default=""))
    op.add_column("users", sa.Column("display_name", sa.String(150), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(500), nullable=True))

    # server_default'u temizle (yeni satırlar için zorunlu veri beklenir)
    op.alter_column("users", "email", server_default=None)
    op.alter_column("users", "password_hash", server_default=None)

    op.create_unique_constraint("uq_users_email", "users", ["email"])

    # ── expenses ─────────────────────────────────────────────────
    op.add_column("expenses", sa.Column(
        "split_type", sa.String(20), nullable=False, server_default="equal"
    ))

    # ── settlements ──────────────────────────────────────────────
    op.add_column("settlements", sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("settlements", sa.Column("note", sa.Text(), nullable=True))

    # ── friendships ──────────────────────────────────────────────
    op.create_table(
        "friendships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("requester_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("addressee_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("requester_id", "addressee_id", name="uq_friendships_pair"),
        sa.CheckConstraint("requester_id != addressee_id", name="ck_friendships_no_self"),
    )

    op.create_index("idx_friendships_requester", "friendships", ["requester_id"])
    op.create_index("idx_friendships_addressee", "friendships", ["addressee_id"])
    op.create_index("idx_friendships_status", "friendships", ["status"])


def downgrade() -> None:
    op.drop_table("friendships")

    op.drop_column("settlements", "note")
    op.drop_column("settlements", "settled_at")

    op.drop_column("expenses", "split_type")

    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "display_name")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "email")

    op.alter_column("users", "username", existing_type=sa.String(100), nullable=False)
