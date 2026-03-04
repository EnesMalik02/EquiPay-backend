"""remove_created_by_from_expenses

Revision ID: 248992902c36
Revises: d5e6f7a8b9c0
Create Date: 2026-03-04 14:36:25.127284

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '248992902c36'
down_revision: Union[str, Sequence[str], None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f('expenses_created_by_fkey'), 'expenses', type_='foreignkey')
    op.drop_column('expenses', 'created_by')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('expenses', sa.Column('created_by', sa.UUID(), autoincrement=False, nullable=False))
    op.create_foreign_key(op.f('expenses_created_by_fkey'), 'expenses', 'users', ['created_by'], ['id'])
