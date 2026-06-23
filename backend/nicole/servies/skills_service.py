"""SkillsService — Skills 管理服务。

管理 Skills 的注册、加载和执行。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..agents.skills.repository import SkillsRepository, SkillMetadata
from ..agents.skills.loader import SkillsLoader

logger = logging.getLogger(__name__)


class SkillsService:
    """Skills 管理服务。"""

    def __init__(
        self,
        repository: Optional[SkillsRepository] = None,
        loader: Optional[SkillsLoader] = None,
    ):
        self.repository = repository or SkillsRepository()
        self.loader = loader or SkillsLoader()

    async def install_skill(
        self, name: str, code: str,
        description: str = "", version: str = "1.0.0",
    ) -> SkillMetadata:
        """安装一个新 Skill。"""
        # 保存代码文件
        skill_dir = self.loader.skills_dir
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / f"{name}.py").write_text(code, encoding="utf-8")

        # 注册元数据
        meta = SkillMetadata(
            name=name,
            version=version,
            description=description,
        )
        self.repository.register(meta)
        logger.info(f"Skill installed: {name} v{version}")
        return meta

    async def uninstall_skill(self, name: str) -> bool:
        """卸载 Skill。"""
        # 删除代码文件
        py_path = self.loader.skills_dir / f"{name}.py"
        if py_path.exists():
            py_path.unlink()
        self.repository.unregister(name)
        # 清除缓存
        self.loader._loaded.pop(name, None)
        logger.info(f"Skill uninstalled: {name}")
        return True

    async def load_skill(self, name: str) -> Optional[Any]:
        """加载 Skill 模块。"""
        return await self.loader.load([name])

    async def reload_skill(self, name: str) -> Optional[Any]:
        """重新加载 Skill。"""
        return await self.loader.reload(name)

    async def list_skills(self) -> List[SkillMetadata]:
        """列出所有已安装的 Skills。"""
        return self.repository.list_all()

    async def search_skills(self, keyword: str) -> List[SkillMetadata]:
        """搜索 Skills。"""
        return self.repository.search(keyword)

    def list_available_files(self) -> List[str]:
        """列出可用但未注册的 Skill 文件。"""
        installed = {s.name for s in self.repository.list_all()}
        all_files = set(self.loader.list_available())
        return list(all_files - installed)
