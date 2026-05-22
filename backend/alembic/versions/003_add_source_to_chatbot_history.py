"""add source column to chatbot_history

Revision ID: 003
Revises: 001_initial_schema
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chatbot_history",
        sa.Column("source", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chatbot_history", "source")
