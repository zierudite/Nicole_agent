"""RunScheduler — 运行调度器。

职责: 管理运行队列、并发控制、超时管理。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RunScheduler:
    """运行调度器，控制 Agent 运行的并发和资源配额。"""

    def __init__(self, max_concurrent: int = 10, default_timeout: int = 300):
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_runs: set = set()

    @property
    def active_count(self) -> int:
        return len(self._active_runs)

    async def acquire(self, run_id: str) -> bool:
        """获取运行许可。"""
        if len(self._active_runs) >= self.max_concurrent:
            return False
        self._active_runs.add(run_id)
        return True

    def release(self, run_id: str) -> None:
        """释放运行许可。"""
        self._active_runs.discard(run_id)

    async def run_with_timeout(self, coro, timeout: Optional[int] = None):
        """带超时的运行。"""
        return await asyncio.wait_for(
            coro,
            timeout=timeout or self.default_timeout,
        )
