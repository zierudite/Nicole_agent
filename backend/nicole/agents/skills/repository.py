"""SkillsRepository — Skills 仓库。

职责: 管理 Skills 的元数据、版本和远程安装。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Skill 元数据。"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    created_at: str = ""
    dependencies: List[str] = field(default_factory=list)


class SkillsRepository:
    """Skills 仓库。管理 Skills 的元数据和版本信息。"""

    def __init__(self, repo_path: str = "data/skills"):
        self.repo_path = Path(repo_path)
        self.repo_path.mkdir(parents=True, exist_ok=True)
        self._index_path = self.repo_path / "index.json"
        self._index: Dict[str, SkillMetadata] = {}
        self._load_index()

    def _load_index(self) -> None:
        """从磁盘加载 Skills 索引。"""
        if self._index_path.exists():
            try:
                data = json.loads(self._index_path.read_text())
                for name, meta in data.items():
                    self._index[name] = SkillMetadata(**meta)
            except Exception as e:
                logger.error(f"Failed to load skills index: {e}")

    def _save_index(self) -> None:
        """保存 Skills 索引到磁盘。"""
        data = {name: vars(meta) for name, meta in self._index.items()}
        self._index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def register(self, metadata: SkillMetadata) -> None:
        """注册一个 Skill 到仓库。"""
        self._index[metadata.name] = metadata
        self._save_index()
        logger.info(f"Skill registered: {metadata.name} v{metadata.version}")

    def unregister(self, name: str) -> None:
        """从仓库中移除 Skill。"""
        self._index.pop(name, None)
        self._save_index()

    def get(self, name: str) -> Optional[SkillMetadata]:
        """获取 Skill 元数据。"""
        return self._index.get(name)

    def list_all(self) -> List[SkillMetadata]:
        """列出所有已注册 Skills。"""
        return list(self._index.values())

    def search(self, keyword: str) -> List[SkillMetadata]:
        """搜索 Skills。"""
        keyword = keyword.lower()
        return [
            meta for meta in self._index.values()
            if keyword in meta.name.lower() or keyword in meta.description.lower()
        ]
