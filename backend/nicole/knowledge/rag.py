"""LightweightRAG — 轻量级 RAG 检索器。

核心检索流程:
  1. BGE-M3 编码 (dense + sparse 双通道)
  2. pgvector 双路检索
  3. RRF 融合
  4. BGE-Reranker 二次精排 (可选)
  5. 上下文构建

参考 Yuxi 的知识库检索链路 + agent-service-toolkit 的 RAG Assistant。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .embedding import BGEM3Encoder
from .reranker import BGEReranker

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """单条检索结果。"""
    chunk_id: str
    content: str
    score: float
    source_type: str = ""
    source_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HybridSearchConfig:
    """混合检索配置。"""
    top_k: int = 10
    dense_weight: float = 0.5      # dense vs sparse 融合权重
    rerank_top_k: int = 5          # 重排后保留的条数
    enable_rerank: bool = True
    min_score: float = 0.0         # 分数阈值
    rrf_k: int = 60                # RRF 算法常数


class LightweightRAG:
    """轻量级 RAG 检索器。

    使用 BGE-M3 实现 dense + sparse 双通道检索，
    无需额外的搜索引擎（如 Elasticsearch）。
    """

    def __init__(
        self,
        encoder: Optional[BGEM3Encoder] = None,
        reranker: Optional[BGEReranker] = None,
        db_session_factory=None,
        config: Optional[HybridSearchConfig] = None,
    ):
        self.encoder = encoder or BGEM3Encoder()
        self.reranker = reranker or BGEReranker()
        self.db_session_factory = db_session_factory
        self.config = config or HybridSearchConfig()

    async def hybrid_search(
        self,
        query: str,
        knowledge_base_id: Optional[str] = None,
        config: Optional[HybridSearchConfig] = None,
    ) -> List[SearchResult]:
        """执行 BGE-M3 双通道混合检索。

        流程: BGE-M3编码 → pgvector Dense + Sparse → RRF融合 → Reranker精排
        """
        cfg = config or self.config
        logger.info(f"Hybrid search: query={query[:50]}, top_k={cfg.top_k}")

        # 1. BGE-M3 编码 (双通道)
        embeddings = await self.encoder.encode(query)
        dense_vec = embeddings.get("dense")
        sparse_weights = embeddings.get("sparse")

        # 2. pgvector 双路检索
        dense_results = await self._dense_search(dense_vec, knowledge_base_id, cfg)
        sparse_results = await self._sparse_search(sparse_weights, knowledge_base_id, cfg)

        # 3. RRF 融合
        fused = self._rrf_fusion(dense_results, sparse_results, cfg.rrf_k, cfg.top_k)

        # 4. 重排序 (可选)
        if cfg.enable_rerank and len(fused) > 1:
            fused = await self.reranker.rerank(query, fused, cfg.rerank_top_k)

        # 5. 过滤低分结果
        fused = [r for r in fused if r.score >= cfg.min_score]

        logger.info(f"Hybrid search results: {len(fused)} items")
        return fused[:cfg.top_k]

    async def _dense_search(
        self,
        dense_vec: Optional[List[float]],
        kb_id: Optional[str],
        config: HybridSearchConfig,
    ) -> List[SearchResult]:
        """pgvector dense 向量检索 (cosine 相似度)。"""
        if dense_vec is None or self.db_session_factory is None:
            return []

        try:
            async with self.db_session_factory() as session:
                from sqlalchemy import text

                sql = """
                    SELECT id, content, source_type, source_id, metadata,
                           1 - (dense_embedding <=> :query_vec) AS score
                    FROM knowledge_chunks
                    WHERE (:kb_id IS NULL OR knowledge_base_id = :kb_id)
                    ORDER BY dense_embedding <=> :query_vec
                    LIMIT :limit
                """
                result = await session.execute(
                    text(sql),
                    {
                        "query_vec": str(dense_vec),
                        "kb_id": kb_id,
                        "limit": config.top_k * 2,
                    },
                )
                rows = result.fetchall()
                return [
                    SearchResult(
                        chunk_id=str(r[0]), content=r[1],
                        source_type=r[2] or "", source_id=str(r[3] or ""),
                        metadata=r[4] or {}, score=float(r[5]),
                    )
                    for r in rows
                ]
        except Exception as e:
            logger.warning(f"Dense search failed (pgvector may not be ready): {e}")
            return []

    async def _sparse_search(
        self,
        sparse_weights: Optional[Dict[str, float]],
        kb_id: Optional[str],
        config: HybridSearchConfig,
    ) -> List[SearchResult]:
        """BGE-M3 sparse 词权重检索 (替代传统 FTS/BM25)。

        使用 pgvector sparsevec 或 JSONB 近似匹配。
        """
        if sparse_weights is None or self.db_session_factory is None:
            return []

        try:
            async with self.db_session_factory() as session:
                from sqlalchemy import text

                # 使用 sparsevec 或通过 token 匹配降级
                sql = """
                    SELECT id, content, source_type, source_id, metadata,
                           1 - (sparse_embedding <=> :query_sparse) AS score
                    FROM knowledge_chunks
                    WHERE (:kb_id IS NULL OR knowledge_base_id = :kb_id)
                    ORDER BY sparse_embedding <=> :query_sparse
                    LIMIT :limit
                """
                import json
                result = await session.execute(
                    text(sql),
                    {
                        "query_sparse": json.dumps(sparse_weights),
                        "kb_id": kb_id,
                        "limit": config.top_k * 2,
                    },
                )
                rows = result.fetchall()
                return [
                    SearchResult(
                        chunk_id=str(r[0]), content=r[1],
                        source_type=r[2] or "", source_id=str(r[3] or ""),
                        metadata=r[4] or {}, score=float(r[5]),
                    )
                    for r in rows
                ]
        except Exception as e:
            logger.warning(f"Sparse search failed: {e}")
            return []

    @staticmethod
    def _rrf_fusion(
        dense: List[SearchResult],
        sparse: List[SearchResult],
        k: int = 60,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """Reciprocal Rank Fusion 融合算法。

        将多路检索结果按排名倒数加权融合。
        """
        scores: Dict[str, Dict] = {}

        for rank, doc in enumerate(dense):
            scores[doc.chunk_id] = {
                "result": doc,
                "score": 1.0 / (k + rank + 1),
            }

        for rank, doc in enumerate(sparse):
            if doc.chunk_id in scores:
                scores[doc.chunk_id]["score"] += 1.0 / (k + rank + 1)
            else:
                scores[doc.chunk_id] = {
                    "result": doc,
                    "score": 1.0 / (k + rank + 1),
                }

        sorted_items = sorted(
            scores.values(), key=lambda x: x["score"], reverse=True
        )
        for item in sorted_items:
            item["result"].score = item["score"]

        return [item["result"] for item in sorted_items[:top_k]]

    async def simple_search(
        self,
        query: str,
        kb_id: Optional[str] = None,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """简化单次搜索接口。"""
        cfg = HybridSearchConfig(top_k=top_k)
        return await self.hybrid_search(query, kb_id, cfg)

    async def batch_search(
        self,
        queries: List[str],
        kb_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[List[SearchResult]]:
        """批量搜索多个查询。"""
        results = []
        for query in queries:
            result = await self.simple_search(query, kb_id, top_k)
            results.append(result)
        return results
