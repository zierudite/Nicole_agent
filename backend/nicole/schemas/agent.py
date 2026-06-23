"""Agent 配置相关 Pydantic Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentConfigCreate(BaseModel):
    """创建 Agent 配置请求。"""
    name: str = Field(..., min_length=1, max_length=256)
    description: str = ""
    system_prompt: Optional[str] = None
    model_config: Dict = Field(
        default_factory=lambda: {"model": "gpt-4o", "temperature": 0.7, "max_tokens": 4096}
    )
    mcp_configs: List[Dict] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    knowledge_base_ids: List[str] = Field(default_factory=list)
    max_revisions: int = Field(default=3, ge=1, le=10)


class AgentConfigResponse(BaseModel):
    """Agent 配置响应。"""
    id: str
    user_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_config: Optional[Dict] = None
    max_revisions: int = 3
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AgentRunRequest(BaseModel):
    """Agent 运行请求。"""
    config_id: str = Field(..., description="Agent 配置 ID")
    user_input: str = Field(..., min_length=1, description="用户输入")
    stream: bool = Field(default=True, description="是否流式响应")


class AgentRunResponse(BaseModel):
    """Agent 运行响应。"""
    run_id: str
    status: str = "running"
    config_id: str
