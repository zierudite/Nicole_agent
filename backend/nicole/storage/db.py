"""DatabaseManager — PostgreSQL 连接管理。

基于 SQLAlchemy 2.0+ async 提供数据库引擎和会话工厂。
参考 Yuxi 的存储层设计 + agent-service-toolkit 的 Pydantic 配置。
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, AsyncIterator, Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncSessionTransaction,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """数据库配置，从环境变量读取。"""
    database_url: str = Field(
        default="postgresql+asyncpg://notemind:notemind_secret@localhost:5432/notemind",
        validation_alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=10, validation_alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, validation_alias="DB_MAX_OVERFLOW")
    db_echo: bool = Field(default=False, validation_alias="DB_ECHO")
    lite_mode: bool = Field(default=False, validation_alias="LITE_MODE")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def effective_url(self) -> str:
        if self.lite_mode:
            return "sqlite+aiosqlite:///app/data/notemind.db"
        return self.database_url


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类。"""
    pass


class DatabaseManager:
    """数据库管理器。管理引擎、会话工厂和生命周期。"""

    def __init__(self, settings: Optional[DatabaseSettings] = None):
        self.settings = settings or DatabaseSettings()
        self._engine = None
        self._session_factory = None
        logger.info(
            f"DatabaseManager initialized (lite={self.settings.lite_mode})"
        )

    async def initialize(self):
        """初始化数据库连接池。"""
        url = self.settings.effective_url
        self._engine = create_async_engine(
            url,
            pool_size=self.settings.db_pool_size,
            max_overflow=self.settings.db_max_overflow,
            echo=self.settings.db_echo,
            pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info(f"Database engine created: {url.split('://')[0]}://...")

        # 测试连接
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection verified")
        except Exception as e:
            logger.warning(f"Database connection test failed: {e}")

    async def create_all(self):
        """创建所有表（基于 ORM 模型）。"""
        if self._engine is None:
            await self.initialize()
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("All database tables created")

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """获取会话工厂。"""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """获取数据库会话（上下文管理器）。"""
        factory = self.get_session_factory()
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self):
        """关闭数据库连接池。"""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database engine disposed")


def get_session_factory(db_manager: DatabaseManager):
    """快捷获取会话工厂。"""
    return db_manager.get_session_factory()
