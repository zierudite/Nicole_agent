"""对话相关 Pydantic Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """对话请求。"""
    conversation_id: Optional[str] = Field(None, description="对话 ID，为空则创建新对话")
    content: str = Field(..., description="消息内容")
    stream: bool = Field(default=True, description="是否流式响应")


class ChatResponse(BaseModel):
    """对话响应。"""
    conversation_id: str
    message_id: str
    role: str = "assistant"
    content: str
    citations: List[Dict[str, str]] = Field(default_factory=list)
    token_count: Optional[int] = None


class MessageResponse(BaseModel):
    """消息响应。"""
    id: str
    conversation_id: str
    role: str
    content: Optional[str] = None
    tool_calls: Optional[Dict] = None
    token_count: Optional[int] = None
    created_at: Optional[str] = None


class ConversationResponse(BaseModel):
    """对话列表响应。"""
    id: str
    title: Optional[str] = None
    message_count: int = 0
    last_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConversationCreateRequest(BaseModel):
    """创建对话请求。"""
    title: str = "新对话"
    agent_config_id: Optional[str] = None
