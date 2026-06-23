"""KnowledgeService — 知识库服务。

管理知识库、文档上传解析、向量索引构建与检索。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..knowledge.rag import LightweightRAG, SearchResult
from ..knowledge.embedding import BGEM3Encoder
from ..knowledge.chunking import Chunker, ChunkConfig, ChunkStrategy
from ..knowledge.parser.manager import DocumentParser

logger = logging.getLogger(__name__)


class KnowledgeService:
    """知识库服务。"""

    def __init__(
        self,
        chunk_repo=None,
        knowledge_base_repo=None,
        rag: Optional[LightweightRAG] = None,
        encoder: Optional[BGEM3Encoder] = None,
        parser: Optional[DocumentParser] = None,
        chunker: Optional[Chunker] = None,
    ):
        self.chunk_repo = chunk_repo
        self.knowledge_base_repo = knowledge_base_repo
        self.rag = rag
        self.encoder = encoder
        self.parser = parser or DocumentParser()
        self.chunker = chunker or Chunker(ChunkConfig(strategy=ChunkStrategy.RECURSIVE))

    async def create_knowledge_base(
        self, name: str, user_id: str, description: str = "",
    ) -> Dict:
        """创建知识库。"""
        kb = await self.knowledge_base_repo.create({
            "name": name,
            "user_id": user_id,
            "description": description,
        })
        logger.info(f"Knowledge base created: {kb.get('id')}")
        return kb

    async def upload_and_index(
        self, file_path: str, knowledge_base_id: str,
    ) -> Dict:
        """上传文档并建立索引（解析 -> 分块 -> 向量化 -> 入库）。"""
        # 1. 文档解析
        parsed = await self.parser.parse(file_path)
        if not parsed:
            return {"status": "error", "message": "Parse failed"}

        # 2. 文本分块
        chunks = self.chunker.chunk(parsed.text, {
            "source_type": parsed.file_type,
            "knowledge_base_id": knowledge_base_id,
        })
        if not chunks:
            return {"status": "error", "message": "No chunks generated"}

        # 3. 向量化 + 入库
        indexed_count = 0
        for chunk in chunks:
            if self.encoder:
                emb = await self.encoder.encode(chunk.content)
            else:
                emb = {"dense": None, "sparse": None}

            await self.chunk_repo.create({
                "knowledge_base_id": knowledge_base_id,
                "content": chunk.content,
                "dense_embedding": emb.get("dense"),
                "sparse_embedding": emb.get("sparse"),
                "source_type": parsed.file_type,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
            })
            indexed_count += 1

        logger.info(f"Indexed {indexed_count} chunks for KB {knowledge_base_id}")
        return {
            "status": "success",
            "chunks": indexed_count,
            "file_type": parsed.file_type,
        }

    async def search(
        self, query: str, knowledge_base_id: Optional[str] = None, top_k: int = 10,
    ) -> List[SearchResult]:
        """搜索知识库。"""
        if self.rag:
            return await self.rag.hybrid_search(query, knowledge_base_id)
        return []

    async def list_knowledge_bases(self, user_id: str) -> List[Dict]:
        """列出用户的知识库。"""
        return await self.knowledge_base_repo.list_by_user(user_id)

    async def delete_knowledge_base(self, kb_id: str) -> bool:
        """删除知识库（含所有 chunks）。"""
        await self.chunk_repo.delete_by_knowledge_base(kb_id)
        return await self.knowledge_base_repo.delete(kb_id)
