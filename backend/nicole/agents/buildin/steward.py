"""Knowledge Steward Agent — 知识沉淀 Agent。

职责: 从对话中提取新知识，更新知识图谱和向量索引。
参考 Yuxi 的知识库/图谱更新机制。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..base import BaseAgent
from ..state import PlanReflectState

logger = logging.getLogger(__name__)


class KnowledgeStewardAgent(BaseAgent):
    """知识沉淀 Agent。将新知识入库（向量 + 图谱）。"""

    def __init__(self):
        super().__init__(
            agent_id="knowledge_steward",
            name="Knowledge Steward",
            description="从交互中提取新知识并更新知识库和图谱",
            system_prompt="",
        )

    async def run(self, state: PlanReflectState) -> PlanReflectState:
        """提取新知识并更新存储。"""
        answer = state.get("synthesized_answer", "")
        citations = state.get("citations", [])
        revision_cycles = state.get("revision_cycles", 0)

        # 仅在非修正轮次（最终轮）执行知识沉淀
        if revision_cycles > 0 and not state.get("needs_revision", False):
            return state

        # 1. 实体提取（从回答中提取新概念）
        new_entities = self._extract_entities(answer)

        # 2. 构建知识更新记录
        updates = []
        for entity in new_entities:
            updates.append({
                "type": "entity",
                "name": entity,
                "source": f"conversation_{state.get('trace_id', 'unknown')}",
                "confidence": 0.7,
            })

        state["knowledge_updates"] = updates
        logger.info(f"Knowledge steward extracted {len(updates)} new entities")
        return state

    @staticmethod
    def _extract_entities(text: str) -> List[str]:
        """从文本中提取潜在的新实体。"""
        # 简单实现: 提取可能的概念性名词
        # 生产环境应使用 LLM 进行实体抽取
        words = text.split()
        entities = [w.strip(".,:;!?") for w in words if len(w) > 2]
        return list(set(entities))[:5]
