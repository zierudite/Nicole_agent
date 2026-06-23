"""Graph Agent — 知识图谱推理 Agent。

职责: 从 Neo4j 查询关联实体/关系，执行图推理分析。
参考 Yuxi 的图谱查询与服务设计。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..base import BaseAgent
from ..state import PlanReflectState

logger = logging.getLogger(__name__)

GRAPH_SYSTEM_PROMPT = """你是一个知识图谱推理专家。从知识图谱中查询实体关系和关联路径。"""


class GraphAgent(BaseAgent):
    """图谱推理 Agent。查询 Neo4j 并执行关系路径推理。"""

    def __init__(self):
        super().__init__(
            agent_id="graph_agent",
            name="Graph Agent",
            description="查询 Neo4j 知识图谱并执行关系推理",
            system_prompt=GRAPH_SYSTEM_PROMPT,
        )

    async def run(self, state: PlanReflectState) -> PlanReflectState:
        """从用户输入中提取实体，查询知识图谱。"""
        query = state.get("user_input", "")
        if not query:
            return state

        # 1. 实体抽取
        entities = self._extract_entities(query)

        if not entities:
            logger.info("No entities extracted for graph query")
            return state

        # 2. Neo4j 查询
        graph_results = await self._query_neo4j(entities)

        # 3. 推理分析
        reasoning = self._reason(graph_results)

        state["graph_context"] = reasoning
        logger.info(f"Graph queried entities={entities}, results={len(graph_results)}")
        return state

    @staticmethod
    def _extract_entities(text: str) -> List[str]:
        """从文本中提取可能的知识图谱实体。"""
        # 简单实现: 按长度和位置提取关键词
        # 生产环境应使用 LLM 提取
        words = text.replace(",", " ").replace("，", " ").split()
        entities = [w for w in words if len(w) > 1]
        return list(set(entities))[:5]

    async def _query_neo4j(self, entities: List[str]) -> List[Dict]:
        """执行 Neo4j Cypher 查询。"""
        # 生产环境:
        # MATCH (e:Entity) WHERE e.name IN $entities
        # OPTIONAL MATCH (e)-[r]-(related)
        # RETURN e, r, related
        return []  # placeholder

    @staticmethod
    def _reason(results: List[Dict]) -> str:
        """对图谱查询结果进行推理分析。"""
        if not results:
            return "未在知识图谱中找到相关实体。"
        parts = [f"知识图谱中找到 {len(results)} 条关联记录。"]
        for r in results[:10]:
            parts.append(f"- 实体: {r.get('entity', '?')}, 关系: {r.get('relation', '?')}")
        return "\n".join(parts)
