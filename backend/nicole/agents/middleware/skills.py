"""SkillsMiddleware — Skills 注入中间件。

职责: 将用户配置的 Skills 加载到 Agent 运行上下文。
参考 Yuxi 的 Skills 热插拔机制。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..context import AgentContext
from ..state import PlanReflectState

logger = logging.getLogger(__name__)


@dataclass
class SkillsMiddleware:
    """Skills 中间件。注入热加载的 Skills 到 Agent。"""

    enabled: bool = True

    async def load_skills(
        self,
        skill_names: List[str],
        context: AgentContext,
    ) -> List[Any]:
        """从 Skills 加载器获取指定 Skills。"""
        if not self.enabled or not skill_names:
            return []
        if context.skills_loader:
            skills = await context.skills_loader.load(skill_names)
            logger.info(f"Skills middleware loaded {len(skills)} skills: {skill_names}")
            return skills
        return []
