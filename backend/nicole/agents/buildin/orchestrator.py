"""Orchestrator Agent — 入口分析器。

职责: 分析用户输入意图，判断是否需要检索/图谱/代码执行，分发任务。
参考 Yuxi 的意图路由机制 + agent-service-toolkit 的 Agent 模式。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from ..base import BaseAgent
from ..state import PlanReflectState

logger = logging.getLogger(__name__)

ORCHESTRATOR_PROMPT = """你是一个智能笔记本系统的入口分析器。
请分析用户输入，判断用户的意图类型。

意图类型包括：
- retrieval: 用户需要查找/检索已有知识
- graph_query: 用户询问概念关系/知识图谱相关问题
- general: 一般性对话、写作、创作等

请只返回以下 JSON 格式：
{"intent": "意图类型", "reason": "判断理由"}

用户输入: {user_input}
"""


class OrchestratorAgent(BaseAgent):
    """入口分析 Agent，识别用户意图并初始化状态。"""

    def __init__(self):
        super().__init__(
            agent_id="orchestrator",
            name="Orchestrator",
            description="分析用户意图并分发给适当的子 Agent",
            system_prompt=ORCHESTRATOR_PROMPT,
        )

    async def run(self, state: PlanReflectState) -> PlanReflectState:
        """分析用户输入并设置意图。"""
        user_input = state.get("user_input", "")
        if not user_input:
            state["errors"].append("Orchestrator: empty user input")
            return state

        # 简单意图分析（可通过 LLM 调用增强）
        # 此处使用关键词匹配作为快速路径，生产环境可替换为 LLM 调用
        state["user_intent"] = self._classify_intent(user_input)
        logger.info(f"Classified intent: {state['user_intent']} for: {user_input[:50]}")
        return state

    @staticmethod
    def _classify_intent(text: str) -> str:
        """基于关键词的快速意图分类。"""
        text_lower = text.lower()
        retrieval_keywords = ["搜索", "查找", "检索", "回忆", "找一下", "search", "find", "lookup"]
        graph_keywords = ["关系", "关联", "连接", "图谱", "联系", "related", "connection", "graph"]

        for kw in retrieval_keywords:
            if kw in text_lower:
                return "retrieval"
        for kw in graph_keywords:
            if kw in text_lower:
                return "graph_query"
        return "general"
