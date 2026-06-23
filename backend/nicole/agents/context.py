from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Agent 运行时配置。"""
    agent_id: str
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    max_revisions: int = 3
    knowledge_base_ids: List[str] = []
    mcp_configs: List[Dict[str, Any]] = []
    skills: List[str] = []
    system_prompt: Optional[str] = None


@dataclass
class AgentContext:
    """Agent 运行上下文。

    持有 Agent 运行所需的全部外部依赖：
    数据库会话、LLM 客户端、向量检索器、图谱客户端、MCP 管理器等。
    参考 Yuxi 的 BaseContext 设计。
    """

    config: AgentConfig
    llm_client: Any = None
    embedding_client: Any = None
    db_session: Any = None
    neo4j_driver: Any = None
    redis_client: Any = None
    knowledge_retriever: Any = None
    mcp_manager: Any = None
    skills_loader: Any = None
    event_bus: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
