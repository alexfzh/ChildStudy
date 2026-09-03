"""add gender column to children

Revision ID: 0002_add_gender
Revises:
Create Date: 2026-09-03 20:35:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_add_gender"
down_revision = "baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "children",
        sa.Column("gender", sa.String(length=8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("children", "gender")
