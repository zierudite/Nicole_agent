"""知识块与知识库数据库模型（含向量字段）。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..storage.db import Base


class KnowledgeBaseModel(Base):
    """知识库。"""
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # 关系
    chunks = relationship("KnowledgeChunkModel", back_populates="knowledge_base",
                          lazy="selectin")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "is_public": self.is_public,
            "chunk_count": len(self.chunks) if self.chunks else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class KnowledgeChunkModel(Base):
    """知识块。存储文档块内容及 BGE-M3 双通道向量。"""
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("knowledge_bases.id"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # BGE-M3 双通道向量 (pgvector 类型通过 SQL 创建，ORM 中映射为文本)
    dense_embedding: Mapped[str] = mapped_column(
        Text, nullable=True, comment="BGE-M3 dense vector (1024d), pgvector format"
    )
    sparse_embedding: Mapped[str] = mapped_column(
        Text, nullable=True, comment="BGE-M3 sparse vector, pgvector sparsevec format"
    )

    # 元数据
    source_type: Mapped[str] = mapped_column(String(32), nullable=True)
    source_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)
    token_count: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # 关系
    knowledge_base = relationship("KnowledgeBaseModel", back_populates="chunks")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "knowledge_base_id": self.knowledge_base_id,
            "content": self.content[:200] + ("..." if len(self.content) > 200 else ""),
            "source_type": self.source_type,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
            "has_dense": bool(self.dense_embedding),
            "has_sparse": bool(self.sparse_embedding),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
