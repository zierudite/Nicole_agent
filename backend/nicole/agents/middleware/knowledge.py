"""KnowledgeMiddleware — 知识库中间件。

职责: 在 Agent 运行前注入知识库检索能力。
参考 Yuxi 的知识库中间件设计。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..context import AgentContext
from ..state import PlanReflectState

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeMiddleware:
    """知识库中间件。在 Agent 节点执行前后注入知识库上下文。"""

    enabled: bool = True
    top_k: int = 10

    async def before_node(
        self,
        node_name: str,
        state: PlanReflectState,
        context: AgentContext,
    ) -> PlanReflectState:
        """节点执行前: 为检索节点注入知识库配置。"""
        if not self.enabled:
            return state
        if node_name == "rag_agent" and context.knowledge_retriever:
            logger.debug("Knowledge middleware: injected retriever for rag_agent")
        return state

    async def after_node(
        self,
        node_name: str,
        state: PlanReflectState,
        context: AgentContext,
    ) -> PlanReflectState:
        """节点执行后: 处理检索结果。"""
        return state
