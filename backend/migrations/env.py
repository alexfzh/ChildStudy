"""Alembic migration environment (ChildStudy).

Note: by default the project uses Base.metadata.create_all in database.py
plus startup-time ALTER migrations to manage schema. Alembic is an optional
versioned migration tool. Activation steps:

    1. pip install alembic          # already in requirements.txt
    2. alembic stamp baseline       # mark the existing DB as baseline
    3. alembic revision --autogenerate -m "desc"
    4. alembic upgrade head

Caveat: settings.database_url uses sqlite+aiosqlite (async). Alembic is sync,
so we rewrite the URL to plain sqlite:// for migration runs. The async engine
in database.py is unaffected.
"""
import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import models  # noqa: F401  ensure models register to Base.metadata
from database import Base, settings

config = context.config

# Strip the +aiosqlite driver so Alembic uses a sync sqlite3 connection.
SYNC_URL = re.sub(r"\+aiosqlite", "", settings.database_url, count=1)
config.set_main_option("sqlalchemy.url", SYNC_URL)

if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=SYNC_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    if section is None:
        section = {}
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
