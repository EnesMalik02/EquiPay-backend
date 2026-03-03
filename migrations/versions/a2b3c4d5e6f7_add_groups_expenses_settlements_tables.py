"""add_groups_expenses_settlements_tables

Revision ID: a2b3c4d5e6f7
Revises: 8ce527299ad1
Create Date: 2026-03-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str]] = "8ce527299ad1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── updated_at trigger function ──
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated_at = NOW();
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # =============================================
    # 1. USERS — alter existing table
    # =============================================
    # name → username (rename + change type)
    op.alter_column("users", "name", new_column_name="username")
    op.alter_column(
        "users",
        "username",
        existing_type=sa.String(),
        type_=sa.String(100),
        existing_nullable=False,
    )

    # phone: make nullable + set length
    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(),
        type_=sa.String(20),
        nullable=True,
    )

    # add new columns
    op.add_column("users", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("users", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # add unique constraint on username
    op.create_unique_constraint("uq_users_username", "users", ["username"])

    # trigger
    op.execute("""
        CREATE TRIGGER trg_users_updated_at
          BEFORE UPDATE ON users
          FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

    # =============================================
    # 2. GROUPS
    # =============================================
    op.create_table(
        "groups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute("""
        CREATE TRIGGER trg_groups_updated_at
          BEFORE UPDATE ON groups
          FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

    # =============================================
    # 3. GROUP_MEMBERS
    # =============================================
    op.create_table(
        "group_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("group_id", UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(20), server_default=sa.text("'member'"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_members_group_user"),
    )

    op.create_index("idx_group_members_group", "group_members", ["group_id"])
    op.create_index("idx_group_members_user", "group_members", ["user_id"])

    # =============================================
    # 4. EXPENSES
    # =============================================
    op.create_table(
        "expenses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("group_id", UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("paid_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default=sa.text("'TRY'"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("expense_date", sa.Date(), server_default=sa.text("CURRENT_DATE")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
    )

    op.create_index("idx_expenses_group", "expenses", ["group_id"])
    op.create_index("idx_expenses_paid_by", "expenses", ["paid_by"])
    op.execute(
        "CREATE INDEX idx_expenses_active ON expenses(group_id) WHERE deleted_at IS NULL;"
    )

    op.execute("""
        CREATE TRIGGER trg_expenses_updated_at
          BEFORE UPDATE ON expenses
          FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

    # =============================================
    # 5. EXPENSE_SPLITS
    # =============================================
    op.create_table(
        "expense_splits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("expense_id", UUID(as_uuid=True), sa.ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("owed_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("expense_id", "user_id", name="uq_expense_splits_expense_user"),
        sa.CheckConstraint("owed_amount >= 0", name="ck_expense_splits_owed_non_negative"),
    )

    op.create_index("idx_splits_expense", "expense_splits", ["expense_id"])
    op.create_index("idx_splits_user", "expense_splits", ["user_id"])

    # =============================================
    # 6. SETTLEMENTS
    # =============================================
    op.create_table(
        "settlements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("group_id", UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=True),
        sa.Column("payer_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("receiver_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default=sa.text("'TRY'"), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("amount > 0", name="ck_settlements_amount_positive"),
    )

    op.create_index("idx_settlements_payer", "settlements", ["payer_id"])
    op.create_index("idx_settlements_receiver", "settlements", ["receiver_id"])
    op.create_index("idx_settlements_group", "settlements", ["group_id"])
    op.create_index("idx_settlements_status", "settlements", ["status"])


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trg_expenses_updated_at ON expenses;")
    op.execute("DROP TRIGGER IF EXISTS trg_groups_updated_at ON groups;")
    op.execute("DROP TRIGGER IF EXISTS trg_users_updated_at ON users;")

    # Drop tables in reverse order
    op.drop_table("settlements")
    op.drop_table("expense_splits")
    op.drop_table("expenses")
    op.drop_table("group_members")
    op.drop_table("groups")

    # Revert users table changes
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "is_active")

    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(20),
        type_=sa.String(),
        nullable=False,
    )
    op.alter_column("users", "username", new_column_name="name")
    op.alter_column(
        "users",
        "name",
        existing_type=sa.String(100),
        type_=sa.String(),
        existing_nullable=False,
    )

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
