"""BGE-Reranker 重排序器。

使用 BAAI/bge-reranker-v2-m3 交叉编码器对检索结果进行二次精排。
参考 Yuxi 的重排序链路。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .rag import SearchResult

logger = logging.getLogger(__name__)


class BGEReranker:
    """BGE-Reranker 重排序器。

    使用交叉编码器 (Cross-Encoder) 对 (query, document) 对打分，
    比双编码器 (Bi-Encoder) 的向量检索更精确，但速度较慢。
    通常只对 Top-K 结果 (如 Top-20) 重排。
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = "cpu",
        use_fp16: bool = False,
        batch_size: int = 32,
    ):
        self.model_name = model_name
        self.device = device
        self.use_fp16 = use_fp16
        self.batch_size = batch_size
        self._model = None
        logger.info(f"BGEReranker initialized (model={model_name}, device={device})")

    async def _lazy_load(self):
        """延迟加载模型。"""
        if self._model is not None:
            return
        try:
            from FlagEmbedding import FlagReranker

            self._model = FlagReranker(
                self.model_name,
                use_fp16=self.use_fp16,
            )
            logger.info(f"BGE-Reranker model loaded: {self.model_name}")
        except ImportError:
            logger.warning(
                "FlagEmbedding not installed. "
                "Reranker will be bypassed."
            )
            self._model = None
        except Exception as e:
            logger.error(f"Failed to load reranker: {e}")
            self._model = None

    async def rerank(
        self,
        query: str,
        documents: List[SearchResult],
        top_k: int = 5,
    ) -> List[SearchResult]:
        """重排序检索结果。

        Args:
            query: 原始查询
            documents: 候选文档列表
            top_k: 返回前 N 条

        Returns:
            按重排分数降序排列的结果
        """
        if not documents:
            return []

        await self._lazy_load()
        if self._model is None:
            # 模型不可用，按原有分数排序返回
            return sorted(documents, key=lambda x: x.score, reverse=True)[:top_k]

        try:
            pairs = [(query, doc.content) for doc in documents]
            scores = self._model.compute_score(pairs, normalize=True)

            for doc, score in zip(documents, scores):
                doc.score = float(score)

            reranked = sorted(documents, key=lambda x: x.score, reverse=True)
            logger.info(
                f"Reranked {len(documents)} items -> top {top_k}: "
                f"best score={reranked[0].score:.4f}"
            )
            return reranked[:top_k]

        except Exception as e:
            logger.error(f"Reranker failed: {e}")
            return sorted(documents, key=lambda x: x.score, reverse=True)[:top_k]

    async def rerank_pairs(
        self,
        query: str,
        texts: List[str],
    ) -> List[float]:
        """对 (query, text) 对打分，返回分数列表。"""
        await self._lazy_load()
        if self._model is None:
            return [1.0] * len(texts)

        try:
            pairs = [(query, text) for text in texts]
            scores = self._model.compute_score(pairs, normalize=True)
            return [float(s) for s in scores]
        except Exception as e:
            logger.error(f"Reranker pairs failed: {e}")
            return [1.0] * len(texts)
