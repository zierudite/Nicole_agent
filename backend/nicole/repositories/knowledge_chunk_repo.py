"""KnowledgeChunkRepository — 知识块数据访问"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .base import BaseRepository


class KnowledgeChunkRepository(BaseRepository):
    """知识块仓储"""

    def __init__(self, session_factory=None):
        super().__init__(session_factory, table_name="knowledge_chunks")

    async def create_with_vectors(
        self,
        content: str,
        knowledge_base_id: str,
        dense_embedding: Optional[List[float]] = None,
        sparse_embedding: Optional[str] = None,
        source_type: str = "",
        chunk_index: int = 0,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """创建带向量的知识块"""
        data = {
            "knowledge_base_id": knowledge_base_id,
            "content": content,
            "source_type": source_type,
            "chunk_index": chunk_index,
            "metadata": metadata or {},
        }
        if dense_embedding is not None:
            data["dense_embedding"] = dense_embedding
        return await self.create(data)

    async def search_dense(
        self, query_embedding: List[float], kb_id: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict]:
        """Dense 向量搜索。"""
        if not self.session_factory:
            return []

        kb_filter = "AND knowledge_base_id = :kb_id" if kb_id else ""

        async with self.session_factory() as session:
            result = await session.execute(
                text(f"""
                    SELECT id, content, source_type, metadata,
                           1 - (dense_embedding <=> :query) AS score
                    FROM knowledge_chunks
                    WHERE dense_embedding IS NOT NULL {kb_filter}
                    ORDER BY dense_embedding <=> :query
                    LIMIT :top_k
                """),
                {"query": str(query_embedding), "kb_id": kb_id, "top_k": top_k},
            )
            return [dict(row) for row in result.mappings().fetchall()]

    async def delete_by_knowledge_base(self, kb_id: str) -> int:
        """删除知识库的所有块"""
        if not self.session_factory:
            return 0

        async with self.session_factory() as session:
            result = await session.execute(
                text("DELETE FROM knowledge_chunks WHERE knowledge_base_id = :kb_id"),
                {"kb_id": kb_id},
            )
            await session.commit()
            return result.rowcount

    async def get_chunks_by_source(
        self, source_type: str, source_id: str,
    ) -> List[Dict]:
        """按来源获取知识块"""
        if not self.session_factory:
            return []

        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM knowledge_chunks
                    WHERE source_type = :source_type AND source_id = :source_id
                    ORDER BY chunk_index
                """),
                {"source_type": source_type, "source_id": source_id},
            )
            return [dict(row) for row in result.mappings().fetchall()]
