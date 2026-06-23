"""AgentConfigRepository — Agent 配置数据访问。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .base import BaseRepository


class AgentConfigRepository(BaseRepository):
    """Agent 配置仓储。"""

    def __init__(self, session_factory=None):
        super().__init__(session_factory, table_name="agent_configs")

    async def list_by_user(self, user_id: str) -> List[Dict]:
        """列出用户的 Agent 配置。"""
        if not self.session_factory:
            return []

        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM agent_configs
                    WHERE user_id = :user_id
                    ORDER BY updated_at DESC
                """),
                {"user_id": user_id},
            )
            return [dict(row) for row in result.mappings().fetchall()]

    async def get_default(self) -> Optional[Dict]:
        """获取默认 Agent 配置。"""
        if not self.session_factory:
            return None

        async with self.session_factory() as session:
            result = await session.execute(
                text("SELECT * FROM agent_configs ORDER BY created_at ASC LIMIT 1"),
            )
            row = result.mappings().first()
            return dict(row) if row else None
