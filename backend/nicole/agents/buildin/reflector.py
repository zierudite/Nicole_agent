"""Reflector Agent — 质量检查器。

职责: 评估执行结果的质量，决定是否需要修正（Plan-Reflection 核心）。
参考 agent-service-toolkit 的 LLM-as-Judge 思路。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..base import BaseAgent
from ..state import PlanReflectState

logger = logging.getLogger(__name__)

REFLECTOR_PROMPT = """你是一个回答质量评审专家。请评估以下对用户问题的回答质量。

用户问题: {user_input}
当前回答: {current_answer}
检索到的相关上下文的长度: {rag_length} 字符
图谱查询结果长度: {graph_length} 字符
工具调用次数: {tool_count}

请评估以下维度:
1. 完整性: 是否全面回答了用户问题
2. 准确性: 是否有事实错误
3. 引用: 是否有足够的引用来源
4. 连贯性: 回答是否结构清晰

返回 JSON: {"score": 0-10, "issues": ["问题1", ...], "needs_revision": true/false, "suggestions": "改进建议"}
"""


class ReflectorAgent(BaseAgent):
    """反思 Agent。评估回答质量，触发放射修正循环。"""

    def __init__(self):
        super().__init__(
            agent_id="reflector",
            name="Reflector",
            description="评估回答质量，决定是否需要修正",
            system_prompt=REFLECTOR_PROMPT,
        )

    async def run(self, state: PlanReflectState) -> PlanReflectState:
        """评估当前结果，设置是否需要修正的标志。"""
        rag_ctx = state.get("rag_context", "")
        graph_ctx = state.get("graph_context", "")
        answer = state.get("synthesized_answer", "")
        tool_results = state.get("tool_results", [])

        # 质量评分规则
        score = 10
        issues = []

        if not rag_ctx and not graph_ctx:
            score -= 2
            issues.append("缺少知识库和图谱检索结果")
        if not answer:
            score -= 3
            issues.append("无综合回答")
        if len(tool_results) == 0 and state.get("user_intent") == "retrieval":
            score -= 1
            issues.append("检索类请求但未调用工具")

        state["quality_score"] = max(0, score)
        state["reflection"] = "; ".join(issues) if issues else "质量通过"
        state["needs_revision"] = score < 7
        state["revision_cycles"] = state.get("revision_cycles", 0) + (
            1 if score < 7 else 0
        )

        logger.info(
            f"Quality score: {score}/10, needs_revision={state['needs_revision']}, "
            f"cycle={state['revision_cycles']}/{state['max_revisions']}"
        )
        return state
