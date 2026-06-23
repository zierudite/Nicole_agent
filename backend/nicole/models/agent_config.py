"""Agent 配置数据库模型。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..storage.db import Base


class AgentConfigModel(Base):
    __tablename__ = "agent_configs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=True)

    # JSON 配置
    model_config: Mapped[dict] = mapped_column(
        JSONB, nullable=True, default=dict,
        comment="LLM model config: {model, temperature, max_tokens, ...}",
    )
    mcp_configs: Mapped[dict] = mapped_column(
        JSONB, nullable=True, default=list,
        comment="MCP server configs: [{name, transport, command, url}]",
    )
    skills: Mapped[dict] = mapped_column(
        JSONB, nullable=True, default=list,
        comment="Enabled skills: [skill_name, ...]",
    )
    knowledge_base_ids: Mapped[list] = mapped_column(
        ARRAY(UUID(as_uuid=False)), nullable=True, default=list
    )
    max_revisions: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "model_config": self.model_config,
            "mcp_configs": self.mcp_configs,
            "skills": self.skills,
            "knowledge_base_ids": self.knowledge_base_ids or [],
            "max_revisions": self.max_revisions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
