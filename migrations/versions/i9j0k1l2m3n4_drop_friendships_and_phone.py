"""drop_friendships_and_phone

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-05-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'i9j0k1l2m3n4'
down_revision: Union[str, None] = 'h8i9j0k1l2m3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('friendships')

    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS phone")


def downgrade() -> None:
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))

    op.create_table(
        'friendships',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('requester_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('addressee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint('requester_id != addressee_id', name='ck_friendships_no_self'),
        sa.ForeignKeyConstraint(['addressee_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('requester_id', 'addressee_id', name='uq_friendships_pair'),
    )
