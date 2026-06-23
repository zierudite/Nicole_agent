"""RAG Agent — 知识检索 Agent。

职责: 执行 BGE-M3 双通道检索（dense + sparse）、结果重排序。
参考 Yuxi 的知识库检索链路。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..base import BaseAgent
from ..state import PlanReflectState

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """你是一个知识检索专家。使用 BGE-M3 双通道检索检索相关知识。"""


class RAGAgent(BaseAgent):
    """RAG 检索 Agent。执行多路召回 + 重排序。"""

    def __init__(self):
        super().__init__(
            agent_id="rag_agent",
            name="RAG Agent",
            description="使用 BGE-M3 双通道检索执行知识库检索",
            system_prompt=RAG_SYSTEM_PROMPT,
        )

    async def run(self, state: PlanReflectState) -> PlanReflectState:
        """执行双通道检索并更新状态。"""
        query = state.get("user_input", "")
        if not query:
            return state

        logger.info(f"RAG searching for: {query[:50]}")

        # ========== 检索流程 ==========
        # 1. BGE-M3 编码: dense + sparse
        dense_results = await self._dense_search(query)
        sparse_results = await self._sparse_search(query)

        # 2. RRF 融合
        fused = self._rrf_fusion(dense_results, sparse_results)

        # 3. 可选: Reranker 精排
        reranked = await self._rerank(query, fused)

        # 4. 构建上下文
        context = self._build_context(reranked)
        state["rag_context"] = context

        logger.info(f"RAG retrieved {len(fused)} chunks, context: {len(context)} chars")
        return state

    async def _dense_search(self, query: str, top_k: int = 10) -> List[Dict]:
        """BGE-M3 dense 向量检索。"""
        # 生产环境: 调用 pgvector 进行 cosine 相似度搜索
        # SELECT content FROM knowledge_chunks
        # ORDER BY dense_embedding <=> :query_emb LIMIT :top_k
        return []  # placeholder

    async def _sparse_search(self, query: str, top_k: int = 10) -> List[Dict]:
        """BGE-M3 sparse 向量检索（替代传统 FTS）。"""
        # 生产环境: 调用 pgvector sparsevec 搜索
        # SELECT content FROM knowledge_chunks
        # ORDER BY sparse_embedding <=> :sparse_emb LIMIT :top_k
        return []  # placeholder

    async def _rerank(self, query: str, results: List[Dict]) -> List[Dict]:
        """BGE-Reranker 二次精排。"""
        # 生产环境: 调用 FlagEmbedding Reranker
        return results

    @staticmethod
    def _rrf_fusion(dense: List[Dict], sparse: List[Dict], k: int = 60) -> List[Dict]:
        """Reciprocal Rank Fusion 融合算法。"""
        scores = {}
        for rank, doc in enumerate(dense):
            doc_id = doc.get("id", str(rank))
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
        for rank, doc in enumerate(sparse):
            doc_id = doc.get("id", str(rank + 1000))
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
        # 按分数降序排列
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [{"id": doc_id, "score": score} for doc_id, score in sorted_docs[:10]]

    @staticmethod
    def _build_context(results: List[Dict]) -> str:
        """将检索结果拼接为上下文文本。"""
        parts = []
        for i, r in enumerate(results[:5]):
            parts.append(f"[{i+1}] (score: {r.get('score', 0):.3f}) {r.get('content', '')}")
        return "\n\n".join(parts)
