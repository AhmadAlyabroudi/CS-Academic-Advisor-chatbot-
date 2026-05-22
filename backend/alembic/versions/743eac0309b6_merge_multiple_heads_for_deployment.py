"""merge multiple heads for deployment

Revision ID: 743eac0309b6
Revises: 003, cede5b01bdc6
Create Date: 2026-05-22 21:58:10.855221

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '743eac0309b6'
down_revision: Union[str, Sequence[str], None] = ('003', 'cede5b01bdc6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
