"""知识图谱相关 Pydantic Schema。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EntityResponse(BaseModel):
    """实体响应。"""
    id: str
    name: str
    type: str
    properties: Dict = Field(default_factory=dict)


class RelationResponse(BaseModel):
    """关系响应。"""
    source_id: str
    target_id: str
    type: str
    properties: Dict = Field(default_factory=dict)


class GraphQueryRequest(BaseModel):
    """图谱查询请求。"""
    keyword: str = Field("", description="搜索关键词")
    entity_id: Optional[str] = Field(None, description="实体 ID")
    entity_name: Optional[str] = Field(None, description="实体名")
    depth: int = Field(default=2, ge=1, le=5, description="查询深度")
    source_id: Optional[str] = Field(None, description="起点 ID")
    target_id: Optional[str] = Field(None, description="终点 ID")


class GraphVisualizationResponse(BaseModel):
    """图谱可视化数据（vis-network 格式）。"""
    nodes: List[Dict] = Field(default_factory=list, description="[{id, label, group, ...}]")
    edges: List[Dict] = Field(default_factory=list, description="[{from, to, label, ...}]")


class EgoNetworkResponse(BaseModel):
    """自我中心网络响应。"""
    entity: EntityResponse
    neighbors: List[Dict] = Field(default_factory=list)
    statistics: Dict = Field(default_factory=dict)
