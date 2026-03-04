"""revert_cascade_fk_keep_data_on_group_delete

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-03-04 00:00:00.000000

Grup silindiğinde expenses ve settlements verileri korunur.
  - expenses.group_id:    CASCADE → SET NULL
  - settlements.group_id: CASCADE → SET NULL
"""
from typing import Sequence, Union

from alembic import op


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str]] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── expenses.group_id: CASCADE → SET NULL ────────────────────────
    op.execute("""
        DO $$
        DECLARE r RECORD;
        BEGIN
            FOR r IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'expenses'::regclass AND contype = 'f'
                  AND conname LIKE '%group_id%'
            LOOP
                EXECUTE 'ALTER TABLE expenses DROP CONSTRAINT ' || r.conname;
            END LOOP;
        END$$;
    """)
    op.execute("""
        ALTER TABLE expenses
            ADD CONSTRAINT expenses_group_id_fkey
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE SET NULL;
    """)

    # ── settlements.group_id: CASCADE → SET NULL ─────────────────────
    op.execute("""
        DO $$
        DECLARE r RECORD;
        BEGIN
            FOR r IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'settlements'::regclass AND contype = 'f'
                  AND conname LIKE '%group_id%'
            LOOP
                EXECUTE 'ALTER TABLE settlements DROP CONSTRAINT ' || r.conname;
            END LOOP;
        END$$;
    """)
    op.execute("""
        ALTER TABLE settlements
            ADD CONSTRAINT settlements_group_id_fkey
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE SET NULL;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE expenses
            DROP CONSTRAINT IF EXISTS expenses_group_id_fkey;
        ALTER TABLE expenses
            ADD CONSTRAINT expenses_group_id_fkey
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE;
    """)

    op.execute("""
        ALTER TABLE settlements
            DROP CONSTRAINT IF EXISTS settlements_group_id_fkey;
        ALTER TABLE settlements
            ADD CONSTRAINT settlements_group_id_fkey
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE;
    """)
