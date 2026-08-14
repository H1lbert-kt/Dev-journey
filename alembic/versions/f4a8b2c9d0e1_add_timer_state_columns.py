"""add timer state columns to users

Revision ID: f4a8b2c9d0e1
Revises: e6f7a8b9c0d1
Create Date: 2026-08-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4a8b2c9d0e1'
down_revision = 'e6f7a8b9c0d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('timer_state_seconds', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('timer_state_subject', sa.String(100), nullable=False, server_default=''))


def downgrade() -> None:
    op.drop_column('users', 'timer_state_subject')
    op.drop_column('users', 'timer_state_seconds')
