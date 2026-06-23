"""BGE-M3 双通道编码器。

使用 BAAI/bge-m3 模型同时生成 dense 和 sparse 向量。
参考 Yuxi 的 embedding 链路设计 + FlagEmbedding 官方用法。
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class BGEM3Encoder:
    """BGE-M3 编码器，支持 dense + sparse 双通道编码。

    用法:
        encoder = BGEM3Encoder(model_name="BAAI/bge-m3")
        result = await encoder.encode("量子计算")
        # result["dense"]  -> List[float] (1024维)
        # result["sparse"] -> Dict[str, float] (词权重映射)
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cpu",
        use_fp16: bool = False,
        batch_size: int = 32,
    ):
        self.model_name = model_name
        self.device = device
        self.use_fp16 = use_fp16
        self.batch_size = batch_size
        self._model = None
        logger.info(f"BGEM3Encoder initialized (model={model_name}, device={device})")

    async def _lazy_load(self):
        """延迟加载模型（首次编码时加载）。"""
        if self._model is not None:
            return
        try:
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel(
                self.model_name,
                use_fp16=self.use_fp16,
                device=self.device,
            )
            logger.info(f"BGE-M3 model loaded: {self.model_name}")
        except ImportError:
            logger.warning(
                "FlagEmbedding not installed. "
                "Install with: pip install FlagEmbedding torch"
            )
            self._model = None
        except Exception as e:
            logger.error(f"Failed to load BGE-M3 model: {e}")
            self._model = None

    async def encode(
        self,
        texts: str | List[str],
        return_dense: bool = True,
        return_sparse: bool = True,
        return_colbert_vecs: bool = False,
    ) -> Dict[str, any]:
        """编码文本，返回 dense/sparse 向量。

        Args:
            texts: 单个文本或文本列表
            return_dense: 是否返回 dense 向量
            return_sparse: 是否返回 sparse 向量

        Returns:
            {
                "dense": List[List[float]] or None,
                "sparse": List[Dict[str, float]] or None,
                "lexical_weights": List[Dict[str, float]],
            }
        """
        await self._lazy_load()
        if self._model is None:
            return self._fallback_encode(texts)

        single = isinstance(texts, str)
        texts_list = [texts] if single else texts
        if not texts_list:
            return {"dense": None, "sparse": None, "lexical_weights": None}

        try:
            output = self._model.encode(
                texts_list,
                return_dense=return_dense,
                return_sparse=return_sparse,
                return_colbert_vecs=return_colbert_vecs,
            )

            result = {}
            if return_dense and "dense_vecs" in output:
                dense = output["dense_vecs"].tolist()
                result["dense"] = dense[0] if single else dense
            else:
                result["dense"] = None

            if return_sparse and "lexical_weights" in output:
                weights = [
                    {k: float(v) for k, v in w.items()}
                    for w in output["lexical_weights"]
                ]
                result["sparse"] = weights[0] if single else weights
                result["lexical_weights"] = result["sparse"]
            else:
                result["sparse"] = None
                result["lexical_weights"] = None

            logger.debug(f"Encoded {len(texts_list)} texts, dense={return_dense}, sparse={return_sparse}")
            return result

        except Exception as e:
            logger.error(f"BGE-M3 encode failed: {e}")
            return self._fallback_encode(texts_list, single)

    def _fallback_encode(self, texts, single=True):
        """模型不可用时的降级编码（返回空占位）。"""
        texts_list = [texts] if isinstance(texts, str) else (texts if texts else [])
        n = len(texts_list)
        return {
            "dense": [None] * n if not single else None,
            "sparse": [None] * n if not single else None,
            "lexical_weights": [None] * n if not single else None,
        }

    async def encode_dense(self, text: str) -> Optional[List[float]]:
        """仅编码 dense 向量。"""
        result = await self.encode(text, return_sparse=False)
        return result.get("dense")

    async def encode_sparse(self, text: str) -> Optional[Dict[str, float]]:
        """仅编码 sparse 向量（词权重）。"""
        result = await self.encode(text, return_dense=False)
        return result.get("sparse")

    def dense_to_pgvector(self, dense_vec: List[float]) -> str:
        """将 dense 向量转为 pgvector 可接受的字符串格式。"""
        return "[" + ",".join(str(v) for v in dense_vec) + "]"

    def sparse_to_pgvector(self, sparse_weights: Dict[str, float]) -> str:
        """将 sparse 词权重转为 pgvector sparsevec 格式。

        pgvector sparsevec 格式: "{idx1:val1,idx2:val2,...}"
        使用词汇表映射 token 到整数索引。
        """
        # 简化为 JSON 字符串，实际生产环境需要词汇表映射
        import json
        return json.dumps(sparse_weights, ensure_ascii=False)
