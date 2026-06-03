"""rename receipt_url to receipt_key

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-06-03 00:00:00.000000

The column now stores an opaque object key (path within the storage bucket)
instead of a fully-qualified public URL. URL projection moved into the
application layer.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "l2m3n4o5p6q7"
down_revision: Union[str, None] = "k1l2m3n4o5p6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("expenses", "receipt_url", new_column_name="receipt_key")


def downgrade() -> None:
    op.alter_column("expenses", "receipt_key", new_column_name="receipt_url")
