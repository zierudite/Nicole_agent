"""UserRepository — 用户数据访问。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .base import BaseRepository


class UserRepository(BaseRepository):
    """用户仓储。"""

    def __init__(self, session_factory=None):
        super().__init__(session_factory, table_name="users")

    async def get_by_username(self, username: str) -> Optional[Dict]:
        """按用户名查找用户。"""
        if not self.session_factory:
            return None
        async with self.session_factory() as session:
            result = await session.execute(
                text("SELECT * FROM users WHERE username = :username"),
                {"username": username},
            )
            row = result.mappings().first()
            return dict(row) if row else None

    async def get_by_email(self, email: str) -> Optional[Dict]:
        """按邮箱查找用户。"""
        if not self.session_factory:
            return None
        async with self.session_factory() as session:
            result = await session.execute(
                text("SELECT * FROM users WHERE email = :email"),
                {"email": email},
            )
            row = result.mappings().first()
            return dict(row) if row else None

    async def update_last_login(self, user_id: str) -> None:
        """更新最后登录时间。"""
        if not self.session_factory:
            return
        async with self.session_factory() as session:
            await session.execute(
                text("UPDATE users SET updated_at = NOW() WHERE id = :id"),
                {"id": user_id},
            )
            await session.commit()

    async def get_active_count(self) -> int:
        """获取活跃用户数。"""
        return await self.count({"is_active": True})
