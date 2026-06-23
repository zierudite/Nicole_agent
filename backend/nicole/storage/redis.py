"""RedisClient — Redis 客户端管理。

提供异步 Redis 连接、连接池管理和常用操作封装。
参考 Yuxi 的 Redis 集成 + Keji-agent 的缓存设计。
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings
from redis.asyncio import ConnectionPool, Redis

logger = logging.getLogger(__name__)


class RedisSettings(BaseSettings):
    """Redis 配置。"""
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    redis_max_connections: int = Field(default=20, validation_alias="REDIS_MAX_CONNECTIONS")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


class RedisClient:
    """异步 Redis 客户端。封装连接池和常用操作。"""

    def __init__(self, settings: Optional[RedisSettings] = None):
        self.settings = settings or RedisSettings()
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None

    async def initialize(self):
        """初始化 Redis 连接池。"""
        if not self.settings.redis_url:
            logger.warning("REDIS_URL not set, Redis disabled")
            return

        self._pool = ConnectionPool.from_url(
            self.settings.redis_url,
            max_connections=self.settings.redis_max_connections,
            decode_responses=True,
        )
        self._redis = Redis(connection_pool=self._pool)

        try:
            await self._redis.ping()
            logger.info(f"Redis connected: {self.settings.redis_url}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._redis = None

    @property
    def client(self) -> Optional[Redis]:
        return self._redis

    # ── Key-Value 操作 ──

    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """设置缓存。"""
        if not self._redis:
            return False
        try:
            val = json.dumps(value, ensure_ascii=False) if not isinstance(value, (str, bytes)) else value
            return await self._redis.setex(key, expire, val)
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存。"""
        if not self._redis:
            return None
        try:
            val = await self._redis.get(key)
            if val is None:
                return None
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return val
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """删除缓存。"""
        if not self._redis:
            return False
        return bool(await self._redis.delete(key))

    # ── Pub/Sub ──

    async def publish(self, channel: str, message: Any) -> int:
        """发布消息到频道。"""
        if not self._redis:
            return 0
        msg = json.dumps(message, ensure_ascii=False) if not isinstance(message, (str, bytes)) else message
        return await self._redis.publish(channel, msg)

    async def subscribe(self, channel: str) -> AsyncIterator[Dict]:
        """订阅频道。"""
        if not self._redis:
            return
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                    except (json.JSONDecodeError, TypeError):
                        data = message["data"]
                    yield {"channel": channel, "data": data}
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    # ── Queue (Stream / List) ──

    async def push_to_queue(self, queue: str, data: Any) -> int:
        """向队列推入数据（右侧）。"""
        if not self._redis:
            return 0
        val = json.dumps(data, ensure_ascii=False)
        return await self._redis.rpush(queue, val)

    async def pop_from_queue(self, queue: str, timeout: int = 0) -> Optional[Any]:
        """从队列取出数据（左侧阻塞）。"""
        if not self._redis:
            return None
        result = await self._redis.blpop(queue, timeout=timeout)
        if result:
            _, val = result
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return val
        return None

    async def get_queue_length(self, queue: str) -> int:
        """获取队列长度。"""
        if not self._redis:
            return 0
        return await self._redis.llen(queue)

    # ── ARQ Worker 支持 ──

    def get_arq_pool(self):
        """获取 ARQ 兼容的 Redis 连接池。"""
        if not self._pool:
            return None
        import aredis
        return aredis.ConnectionPool.from_url(self.settings.redis_url)

    # ── 生命周期 ──

    async def close(self):
        """关闭连接池。"""
        if self._redis:
            await self._redis.close()
        if self._pool:
            await self._pool.disconnect()
        logger.info("Redis connection closed")

    async def flush_all(self):
        """清空所有数据（危险操作）。"""
        if self._redis:
            await self._redis.flushall()
