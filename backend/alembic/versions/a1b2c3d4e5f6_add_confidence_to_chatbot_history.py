"""add_confidence_to_chatbot_history

Revision ID: a1b2c3d4e5f6
Revises: 6bc18fc973db
Create Date: 2026-06-05 19:45:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6bc18fc973db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add confidence column to chatbot_history (nullable float)
    op.add_column(
        'chatbot_history',
        sa.Column('confidence', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('chatbot_history', 'confidence')
