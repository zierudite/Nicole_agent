"""Executor Agent — 执行器

职责: 执行计划中的各步骤，调用工具、合并多源结果。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..base import BaseAgent
from ..state import PlanReflectState

logger = logging.getLogger(__name__)


class ExecutorAgent(BaseAgent):
    """执行 Agent。合并 RAG/图谱/工具的结果，执行具体的处理步骤。"""

    def __init__(self):
        super().__init__(
            agent_id="executor",
            name="Executor",
            description="执行计划步骤，合并多源结果",
            system_prompt="",
        )

    async def run(self, state: PlanReflectState) -> PlanReflectState:
        """执行当前步骤，合并各 Agent 的中间结果。"""
        state["current_step"] = state.get("current_step", 0) + 1
        revision_cycle = state.get("revision_cycles", 0)

        # 从各 Agent 结果收集信息
        rag_ctx = state.get("rag_context")
        graph_ctx = state.get("graph_context")
        tool_results = state.get("tool_results", [])

        # 如果是修正轮次，记录修正原因
        if revision_cycle > 0:
            reflection = state.get("reflection", "")
            logger.info(f"Executing revision cycle {revision_cycle}: {reflection[:100]}")

        # 合并结果到上下文中供后续使用
        merged = self._merge_sources(rag_ctx, graph_ctx, tool_results)
        state.setdefault("agent_results", {})["executor_merged"] = merged
        logger.info(f"Executor merged {len(tool_results)} tool results")
        return state

    @staticmethod
    def _merge_sources(
        rag: str | None,
        graph: str | None,
        tools: List[Dict],
    ) -> Dict[str, Any]:
        """合并多源信息为一个统一上下文。"""
        return {
            "rag_content": rag or "",
            "graph_content": graph or "",
            "tool_count": len(tools),
            "source_count": sum(1 for s in [rag, graph] if s),
        }
