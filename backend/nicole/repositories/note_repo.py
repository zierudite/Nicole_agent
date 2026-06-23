"""NoteRepository — 笔记数据访问。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .base import BaseRepository


class NoteRepository(BaseRepository):
    """笔记仓储。"""

    def __init__(self, session_factory=None):
        super().__init__(session_factory, table_name="notes")

    async def list_by_user(
        self, user_id: str, limit: int = 50, offset: int = 0,
        include_archived: bool = False,
    ) -> List[Dict]:
        """列出用户的笔记。"""
        if not self.session_factory:
            return []

        archived_filter = "" if include_archived else "AND is_archived = FALSE"

        async with self.session_factory() as session:
            result = await session.execute(
                text(f"""
                    SELECT * FROM notes
                    WHERE user_id = :user_id {archived_filter}
                    ORDER BY is_pinned DESC, updated_at DESC
                    LIMIT :limit OFFSET :offset
                """),
                {"user_id": user_id, "limit": limit, "offset": offset},
            )
            return [dict(row) for row in result.mappings().fetchall()]

    async def search(
        self, user_id: str, keyword: str, limit: int = 20,
    ) -> List[Dict]:
        """搜索笔记标题和内容。"""
        if not self.session_factory:
            return []

        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM notes
                    WHERE user_id = :user_id
                    AND (title ILIKE :keyword OR content ILIKE :keyword)
                    AND is_archived = FALSE
                    ORDER BY updated_at DESC
                    LIMIT :limit
                """),
                {"user_id": user_id, "keyword": f"%{keyword}%", "limit": limit},
            )
            return [dict(row) for row in result.mappings().fetchall()]

    async def get_by_tag(self, user_id: str, tag: str, limit: int = 20) -> List[Dict]:
        """按标签获取笔记。"""
        if not self.session_factory:
            return []

        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM notes
                    WHERE user_id = :user_id
                    AND :tag = ANY(tags)
                    AND is_archived = FALSE
                    ORDER BY updated_at DESC
                    LIMIT :limit
                """),
                {"user_id": user_id, "tag": tag, "limit": limit},
            )
            return [dict(row) for row in result.mappings().fetchall()]

    async def toggle_pin(self, note_id: str) -> Optional[Dict]:
        """切换笔记置顶状态。"""
        return await self.update(note_id, {"is_pinned": True})

    async def archive(self, note_id: str) -> Optional[Dict]:
        """归档笔记。"""
        return await self.update(note_id, {"is_archived": True})

    async def restore(self, note_id: str) -> Optional[Dict]:
        """恢复笔记。"""
        return await self.update(note_id, {"is_archived": False})

    async def get_children(self, parent_id: str) -> List[Dict]:
        """获取子笔记列表。"""
        if not self.session_factory:
            return []

        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM notes
                    WHERE parent_id = :parent_id
                    ORDER BY sort_order, created_at
                """),
                {"parent_id": parent_id},
            )
            return [dict(row) for row in result.mappings().fetchall()]
