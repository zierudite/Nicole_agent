"""SkillsLoader — Skills 热加载器。

职责: 从文件系统或仓库动态加载 Python 脚本作为 Skills。
参考 Yuxi 的 Skills 热插拔机制。
"""

from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SkillsLoader:
    """Skills 热加载器。从指定目录动态加载 Python 模块。"""

    def __init__(self, skills_dir: str = "data/skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._loaded: Dict[str, Any] = {}

    async def load(self, skill_names: List[str]) -> List[Any]:
        """加载指定的 Skills。"""
        loaded = []
        for name in skill_names:
            skill = await self._load_single(name)
            if skill:
                loaded.append(skill)
        return loaded

    async def _load_single(self, name: str) -> Optional[Any]:
        """加载单个 Skill。"""
        if name in self._loaded:
            return self._loaded[name]

        # 查找 .py 文件
        py_path = self.skills_dir / f"{name}.py"
        if not py_path.exists():
            logger.warning(f"Skill '{name}' not found at {py_path}")
            return None

        try:
            spec = importlib.util.spec_from_file_location(name, py_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self._loaded[name] = module
                logger.info(f"Skill loaded: {name}")
                return module
        except Exception as e:
            logger.error(f"Failed to load skill '{name}': {e}")
        return None

    async def reload(self, name: str) -> Optional[Any]:
        """重新加载 Skill。"""
        self._loaded.pop(name, None)
        return await self._load_single(name)

    def list_available(self) -> List[str]:
        """列出可用的 Skill 文件。"""
        return [f.stem for f in self.skills_dir.glob("*.py")]
