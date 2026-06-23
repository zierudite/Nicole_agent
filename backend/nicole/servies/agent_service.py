"""AgentService — Agent 配置与运行服务。

管理 Agent 配置的 CRUD，以及触发 Agent 运行。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..agents.context import AgentConfig
from ..agents.harness import AgentHarness

logger = logging.getLogger(__name__)


class AgentService:
    """Agent 服务。管理 Agent 配置和执行。"""

    def __init__(self, agent_config_repo=None, harness: Optional[AgentHarness] = None):
        self.repo = agent_config_repo
        self.harness = harness

    async def create_config(self, user_id: str, config: AgentConfig) -> Dict:
        """创建 Agent 配置。"""
        config_dict = config.model_dump()
        config_dict["user_id"] = user_id
        created = await self.repo.create(config_dict)
        logger.info(f"Agent config created: {created.get('id')}")
        return created

    async def get_config(self, config_id: str) -> Optional[Dict]:
        """获取 Agent 配置。"""
        return await self.repo.get(config_id)

    async def list_configs(self, user_id: str) -> List[Dict]:
        """列出用户的 Agent 配置。"""
        return await self.repo.list_by_user(user_id)

    async def update_config(self, config_id: str, updates: Dict) -> Optional[Dict]:
        """更新 Agent 配置。"""
        return await self.repo.update(config_id, updates)

    async def delete_config(self, config_id: str) -> bool:
        """删除 Agent 配置。"""
        return await self.repo.delete(config_id)

    async def run_agent(
        self, config_id: str, user_input: str,
    ):
        """执行 Agent 运行。"""
        if not self.harness:
            raise RuntimeError("Harness not configured")
        config = await self.repo.get(config_id)
        if not config:
            raise ValueError(f"Agent config {config_id} not found")

        run_id = await self.harness.create_run(
            agent_config=AgentConfig(**config),
            user_input=user_input,
        )
        return run_id
