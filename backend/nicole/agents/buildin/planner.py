"""Planner Agent — 计划生成器。

职责: 根据用户意图生成详细的执行计划，分解为可执行的步骤。
参考 Yuxi 的 Agent planning 设计。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..base import BaseAgent
from ..state import PlanReflectState

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """你是一个任务规划专家。请根据用户的请求生成一个详细的执行计划。

用户请求: {user_input}
用户意图: {user_intent}

请将计划分解为具体的步骤，每步应当明确、可执行。
返回 JSON 格式:
{"steps": ["步骤1", "步骤2", ...], "plan_summary": "计划的简要描述"}
"""


class PlannerAgent(BaseAgent):
    """计划生成 Agent，将用户输入分解为可执行的步骤序列。"""

    def __init__(self):
        super().__init__(
            agent_id="planner",
            name="Planner",
            description="将用户请求分解为结构化执行计划",
            system_prompt=PLANNER_PROMPT,
        )

    async def run(self, state: PlanReflectState) -> PlanReflectState:
        """生成执行计划。"""
        intent = state.get("user_intent", "general")

        # 根据意图类型生成默认计划
        steps = self._generate_steps(intent, state.get("user_input", ""))
        state["plan_steps"] = steps
        state["plan"] = " -> ".join(steps)
        state["current_step"] = 0
        logger.info(f"Plan generated: {state['plan']}")
        return state

    @staticmethod
    def _generate_steps(intent: str, user_input: str) -> List[str]:
        """根据意图生成默认步骤计划。"""
        base_steps = [
            "理解用户需求并收集上下文",
            "检索相关知识库",
            "查询知识图谱关联信息",
            "综合分析与推理",
            "质量检查与验证",
            "生成最终回答",
        ]

        if intent == "retrieval":
            return [
                "解析查询关键词",
                "执行多路检索（向量 + 关键词）",
                "重排序检索结果",
                "从检索结果提取关键信息",
                "结构化输出检索结果",
            ]
        elif intent == "graph_query":
            return [
                "识别查询中的实体和关系",
                "构建 Cypher 查询",
                "执行 Neo4j 图谱查询",
                "推理关联路径",
                "可视化或结构化输出结果",
            ]
        else:
            return base_steps
