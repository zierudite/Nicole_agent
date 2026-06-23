"""Neo4jManager — Neo4j 图数据库驱动管理。

封装 Neo4j 异步驱动的初始化和连接管理。
参考 Yuxi 的 Neo4j 集成。
"""

from __future__ import annotations

import logging
from typing import Optional

from neo4j import AsyncGraphDatabase, AsyncDriver
from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Neo4jSettings(BaseSettings):
    """Neo4j 配置。"""
    neo4j_uri: str = Field(default="bolt://localhost:7687", validation_alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", validation_alias="NEO4J_USER")
    neo4j_password: str = Field(default="notemind_secret", validation_alias="NEO4J_PASSWORD")
    neo4j_max_connection_pool_size: int = Field(default=50, validation_alias="NEO4J_MAX_POOL_SIZE")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


class Neo4jManager:
    """Neo4j 驱动管理器。"""

    def __init__(self, settings: Optional[Neo4jSettings] = None):
        self.settings = settings or Neo4jSettings()
        self._driver: Optional[AsyncDriver] = None

    async def initialize(self):
        """创建 Neo4j 异步驱动。"""
        if not self.settings.neo4j_uri:
            logger.warning("NEO4J_URI not set, Neo4j disabled")
            return

        self._driver = AsyncGraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
            max_connection_pool_size=self.settings.neo4j_max_connection_pool_size,
            connection_acquisition_timeout=30.0,
        )

        # 验证连接
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 AS ok")
                record = await result.single()
                if record and record.get("ok") == 1:
                    logger.info(f"Neo4j connected: {self.settings.neo4j_uri}")
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}")

    @property
    def driver(self) -> Optional[AsyncDriver]:
        return self._driver

    def get_driver(self) -> AsyncDriver:
        if self._driver is None:
            raise RuntimeError("Neo4j not initialized. Call initialize() first.")
        return self._driver

    async def verify_connectivity(self) -> bool:
        """验证 Neo4j 连接。"""
        if not self._driver:
            return False
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1")
                await result.single()
            return True
        except Exception as e:
            logger.warning(f"Neo4j connectivity check failed: {e}")
            return False

    async def close(self):
        """关闭驱动。"""
        if self._driver:
            await self._driver.close()
            logger.info("Neo4j driver closed")
