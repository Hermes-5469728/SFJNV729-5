"""Alembic 迁移环境配置 · alembic/env.py"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from src.core.config import settings
from src.core.base import Base
import src.modules.medical.models  # noqa: 注册所有模型
import src.modules.content.models  # noqa: 注册所有模型

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
