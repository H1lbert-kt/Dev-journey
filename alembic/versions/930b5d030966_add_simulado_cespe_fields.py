"""add_simulado_cespe_fields

Revision ID: 930b5d030966
Revises: a98dd1bca3a6
Create Date: 2026-08-10 12:27:44.046178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '930b5d030966'
down_revision: Union[str, None] = 'a98dd1bca3a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('simulados', sa.Column('wrong_answers', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('simulados', sa.Column('null_answers', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('simulados', sa.Column('correction_method', sa.String(length=20), nullable=False, server_default='normal'))
    op.add_column('simulados', sa.Column('final_score', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('simulados', 'final_score')
    op.drop_column('simulados', 'correction_method')
    op.drop_column('simulados', 'null_answers')
    op.drop_column('simulados', 'wrong_answers')
