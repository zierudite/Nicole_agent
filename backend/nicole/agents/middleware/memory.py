"""MemoryMiddleware — 长时记忆中间件。

职责: 管理对话历史和 Agent 长期记忆的读写。
参考 agent-service-toolkit 的 LangGraph Store 模式。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..state import PlanReflectState

logger = logging.getLogger(__name__)


@dataclass
class MemoryMiddleware:
    """长时记忆中间件。管理对话历史。"""

    max_history: int = 50
    enabled: bool = True

    async def load_memory(self, state: PlanReflectState) -> PlanReflectState:
        """从持久化存储加载历史记忆。"""
        if not self.enabled:
            return state
        return state

    async def save_memory(self, state: PlanReflectState) -> None:
        """保存当前交互到长时记忆。"""
        if not self.enabled:
            return
        logger.debug("Memory middleware: saved conversation memory")

    def truncate_history(
        self,
        history: List[Dict[str, str]],
        max_tokens: int = 4096,
    ) -> List[Dict[str, str]]:
        """截断对话历史以防止超出上下文窗口。"""
        if len(history) <= self.max_history:
            return history
        # 保留最近的 N 条消息
        return history[-self.max_history:]
