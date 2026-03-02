from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    global _engine, _session_factory
    settings = get_settings()
    url = settings.database_url
    if not url:
        logger.warning("DATABASE_URL 未配置，数据库功能不可用")
        return

    _engine = create_async_engine(url, echo=False, pool_size=5, max_overflow=10)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    async with _engine.begin() as conn:
        from app.models.db_models import User, CreditRecord, GenerationHistory, Project  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
        await _apply_schema_updates(conn)

    logger.info("数据库初始化完成: %s", url.split("@")[-1] if "@" in url else url)


async def close_db() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("数据库连接关闭")


@asynccontextmanager
async def get_session():
    if not _session_factory:
        raise RuntimeError("数据库未初始化，请配置 DATABASE_URL")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def is_db_available() -> bool:
    return _session_factory is not None


async def _apply_schema_updates(conn) -> None:
    """
    在无 Alembic 场景下做幂等 schema 补丁，避免老环境缺少新增列。
    """
    await conn.execute(
        text(
            """
            ALTER TABLE generation_history
            ADD COLUMN IF NOT EXISTS project_id VARCHAR(36)
            """
        )
    )
    await conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_generation_history_project_id
            ON generation_history (project_id)
            """
        )
    )
