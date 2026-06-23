"""ConversationRepository — 对话数据访问。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .base import BaseRepository


class ConversationRepository(BaseRepository):
    """对话仓储。"""

    def __init__(self, session_factory=None):
        super().__init__(session_factory, table_name="conversations")

    async def list_by_user(
        self, user_id: str, limit: int = 20,
    ) -> List[Dict]:
        """列出用户的对话。"""
        if not self.session_factory:
            return []

        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT c.*,
                           (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) AS message_count,
                           (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) AS last_message
                    FROM conversations c
                    WHERE c.user_id = :user_id AND c.is_active = TRUE
                    ORDER BY c.updated_at DESC
                    LIMIT :limit
                """),
                {"user_id": user_id, "limit": limit},
            )
            return [dict(row) for row in result.mappings().fetchall()]

    async def add_message(self, message: Dict) -> Optional[Dict]:
        """添加消息到对话。"""
        if not self.session_factory:
            return message

        async with self.session_factory() as session:
            # 插入消息
            columns = ", ".join(message.keys())
            placeholders = ", ".join(f":{k}" for k in message.keys())
            await session.execute(
                text(f"INSERT INTO messages ({columns}) VALUES ({placeholders})"),
                message,
            )
            # 更新对话的 updated_at
            await session.execute(
                text("UPDATE conversations SET updated_at = NOW() WHERE id = :id"),
                {"id": message.get("conversation_id")},
            )
            await session.commit()
            return message

    async def get_messages(
        self, conversation_id: str, limit: int = 50,
    ) -> List[Dict]:
        """获取对话消息列表。"""
        if not self.session_factory:
            return []

        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM messages
                    WHERE conversation_id = :conv_id
                    ORDER BY created_at ASC
                    LIMIT :limit
                """),
                {"conv_id": conversation_id, "limit": limit},
            )
            return [dict(row) for row in result.mappings().fetchall()]

    async def delete(self, conversation_id: str) -> bool:
        """删除对话及其消息。"""
        if not self.session_factory:
            return False

        async with self.session_factory() as session:
            # 删除消息
            await session.execute(
                text("DELETE FROM messages WHERE conversation_id = :id"),
                {"id": conversation_id},
            )
            # 软删除对话
            await session.execute(
                text("UPDATE conversations SET is_active = FALSE WHERE id = :id"),
                {"id": conversation_id},
            )
            await session.commit()
            return True
