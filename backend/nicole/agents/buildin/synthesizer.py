"""Synthesizer Agent — 综合输出生成器。

职责: 将 RAG 检索结果、图谱推理结果、工具执行结果综合为最终答案。
参考 Yuxi 的回答生成逻辑。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from ..base import BaseAgent
from ..state import PlanReflectState

logger = logging.getLogger(__name__)

SYNTHESIZER_PROMPT = """你是一个知识综合专家。请基于以下多源信息生成完整、准确的回答。

用户问题: {user_input}

检索到的知识库内容: {rag_context}

知识图谱推理结果: {graph_context}

工具调用结果: {tool_results}

要求:
1. 全面回答用户问题
2. 明确标注信息来源（引用）
3. 结构清晰，使用 Markdown 格式
4. 如果信息不足，明确指出
"""


class SynthesizerAgent(BaseAgent):
    """综合 Agent。将所有中间结果融合为最终输出。"""

    def __init__(self):
        super().__init__(
            agent_id="synthesizer",
            name="Synthesizer",
            description="综合多源信息生成最终回答",
            system_prompt=SYNTHESIZER_PROMPT,
        )

    async def run(self, state: PlanReflectState) -> PlanReflectState:
        """综合多源信息生成最终回答。"""
        user_input = state.get("user_input", "")
        rag_ctx = state.get("rag_context", "")
        graph_ctx = state.get("graph_context", "")
        tool_results = state.get("tool_results", [])
        plan_steps = state.get("plan_steps", [])

        # 构建综合回答（此处为模板，生产环境应调用 LLM）
        answer_parts = [f"# {user_input}\n"]

        if rag_ctx:
            answer_parts.append("## 检索结果\n")
            answer_parts.append(rag_ctx[:2000])
            answer_parts.append("\n")

        if graph_ctx:
            answer_parts.append("## 知识图谱关联\n")
            answer_parts.append(graph_ctx[:1000])
            answer_parts.append("\n")

        if tool_results:
            answer_parts.append("## 工具输出\n")
            for i, tr in enumerate(tool_results[:5]):
                answer_parts.append(f"### 结果 {i+1}\n")
                answer_parts.append(str(tr.get("output", ""))[:500])
                answer_parts.append("\n")

        # 添加引用溯源
        citations = self._build_citations(rag_ctx, graph_ctx, tool_results)
        state["citations"] = citations
        if citations:
            answer_parts.append("## 引用来源\n")
            for c in citations:
                answer_parts.append(f"- {c.get('source', 'unknown')}: {c.get('snippet', '')[:100]}\n")

        state["synthesized_answer"] = "\n".join(answer_parts)
        logger.info(f"Synthesized answer: {len(state['synthesized_answer'])} chars, {len(citations)} citations")
        return state

    @staticmethod
    def _build_citations(rag: str, graph: str, tools: List[Dict]) -> List[Dict[str, str]]:
        """构建引用溯源列表。"""
        citations = []
        if rag:
            citations.append({"source": "知识库检索", "snippet": rag[:200], "type": "rag"})
        if graph:
            citations.append({"source": "知识图谱", "snippet": graph[:200], "type": "graph"})
        for i, t in enumerate(tools):
            citations.append({
                "source": f"工具调用 #{i+1}",
                "snippet": str(t.get("output", ""))[:200],
                "type": "tool",
                "tool_name": t.get("name", "unknown"),
            })
        return citations
