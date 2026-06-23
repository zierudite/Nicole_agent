"""知识库相关 Pydantic Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求。"""
    name: str = Field(..., min_length=1, max_length=256)
    description: str = ""
    is_public: bool = False


class KnowledgeBaseResponse(BaseModel):
    """知识库响应。"""
    id: str
    name: str
    description: Optional[str] = None
    user_id: Optional[str] = None
    is_public: bool = False
    chunk_count: int = 0
    created_at: Optional[str] = None


class SearchRequest(BaseModel):
    """检索请求。"""
    query: str = Field(..., min_length=1, description="检索查询")
    knowledge_base_id: Optional[str] = Field(None, description="知识库 ID")
    top_k: int = Field(default=10, ge=1, le=100, description="返回条数")
    enable_rerank: bool = Field(default=True, description="是否重排序")
    dense_weight: float = Field(default=0.5, ge=0, le=1, description="dense vs sparse 权重")


class SearchResultItem(BaseModel):
    """单条检索结果。"""
    chunk_id: str
    content: str
    score: float
    source_type: str = ""
    metadata: Dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """检索响应。"""
    query: str
    results: List[SearchResultItem]
    total: int


class DocumentUploadResponse(BaseModel):
    """文档上传响应。"""
    file_id: str
    filename: str
    size: int
    status: str = "uploaded"
    parse_result: Optional[Dict] = None
