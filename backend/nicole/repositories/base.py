"""BaseRepository — 数据访问基类。

提供通用的 CRUD 操作模板，继承自此类减少重复代码。
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BaseRepository:
    """数据访问基类。封装通用 CRUD 操作。"""

    def __init__(self, session_factory=None, table_name: str = ""):
        self.session_factory = session_factory
        self.table_name = table_name

    async def create(self, data: Dict[str, Any]) -> Optional[Dict]:
        """创建记录。"""
        if not self.session_factory:
            return {**data, "id": str(uuid.uuid4())}

        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        if "created_at" not in data:
            data["created_at"] = datetime.now(timezone.utc)

        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())

        async with self.session_factory() as session:
            result = await session.execute(
                text(f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) RETURNING *"),
                data,
            )
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else data

    async def get(self, record_id: str) -> Optional[Dict]:
        """按 ID 获取记录。"""
        if not self.session_factory:
            return None

        async with self.session_factory() as session:
            result = await session.execute(
                text(f"SELECT * FROM {self.table_name} WHERE id = :id"),
                {"id": record_id},
            )
            row = result.mappings().first()
            return dict(row) if row else None

    async def update(self, record_id: str, updates: Dict[str, Any]) -> Optional[Dict]:
        """更新记录。"""
        if not self.session_factory:
            return None

        updates["updated_at"] = datetime.now(timezone.utc)
        set_clause = ", ".join(f"{k} = :{k}" for k in updates.keys())
        params = {**updates, "id": record_id}

        async with self.session_factory() as session:
            result = await session.execute(
                text(f"UPDATE {self.table_name} SET {set_clause} WHERE id = :id RETURNING *"),
                params,
            )
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else None

    async def delete(self, record_id: str) -> bool:
        """删除记录（软删除）。"""
        if not self.session_factory:
            return False

        async with self.session_factory() as session:
            result = await session.execute(
                text(f"DELETE FROM {self.table_name} WHERE id = :id RETURNING id"),
                {"id": record_id},
            )
            await session.commit()
            return result.rowcount > 0

    async def list_all(
        self, limit: int = 100, offset: int = 0, order_by: str = "created_at DESC",
    ) -> List[Dict]:
        """列出所有记录。"""
        if not self.session_factory:
            return []

        async with self.session_factory() as session:
            result = await session.execute(
                text(f"SELECT * FROM {self.table_name} ORDER BY {order_by} LIMIT :limit OFFSET :offset"),
                {"limit": limit, "offset": offset},
            )
            return [dict(row) for row in result.mappings().fetchall()]

    async def count(self, filters: Optional[Dict] = None) -> int:
        """计数。"""
        if not self.session_factory:
            return 0

        where = ""
        params = {}
        if filters:
            conditions = [f"{k} = :{k}" for k in filters]
            where = "WHERE " + " AND ".join(conditions)
            params = filters

        async with self.session_factory() as session:
            result = await session.execute(
                text(f"SELECT COUNT(*) FROM {self.table_name} {where}"),
                params,
            )
            return result.scalar() or 0
