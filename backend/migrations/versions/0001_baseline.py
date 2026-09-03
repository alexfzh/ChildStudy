"""baseline

把当前 schema 作为 Alembic 版本链起点。现有库由 database.py 创建，启用 Alembic 时
执行 `alembic stamp baseline` 标记，不重复建表。

Revision ID: baseline
Revises:
Create Date: 2026-09-03 00:00:00.000000
"""
import sqlalchemy as sa  # noqa: F401
from alembic import op  # noqa: F401

revision = "baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 当前表结构由 database.py 管理，此处不建表。
    pass


def downgrade() -> None:
    pass
