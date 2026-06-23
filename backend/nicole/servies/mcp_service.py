"""MCPService — MCP 工具管理服务。

管理 MCP 服务器的注册、配置和工具的加载。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPService:
    """MCP 工具管理服务。"""

    def __init__(self, mcp_manager=None, mcp_config_repo=None):
        self.mcp_manager = mcp_manager
        self.repo = mcp_config_repo

    async def register_server(
        self, name: str, transport: str,
        command: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Dict:
        """注册一个 MCP 服务器配置。"""
        config = {
            "name": name,
            "transport": transport,
            "command": command,
            "url": url,
        }
        if self.repo:
            created = await self.repo.create(config)
        else:
            created = config
        logger.info(f"MCP server registered: {name} ({transport})")
        return created

    async def unregister_server(self, name: str) -> bool:
        """注销 MCP 服务器。"""
        if self.repo:
            return await self.repo.delete_by_name(name)
        return True

    async def list_servers(self) -> List[Dict]:
        """列出所有已注册的 MCP 服务器。"""
        if self.repo:
            return await self.repo.list_all()
        return []

    async def get_available_tools(self) -> List[Dict]:
        """获取所有 MCP 服务器提供的工具列表。"""
        if not self.mcp_manager:
            return []
        configs = await self.list_servers()
        return await self.mcp_manager.load_mcp_tools(configs)

    async def call_tool(self, server_name: str, tool_name: str, args: Dict) -> Any:
        """调用指定 MCP 服务器的工具。"""
        if not self.mcp_manager:
            raise RuntimeError("MCP manager not configured")
        client = self.mcp_manager._clients.get(server_name)
        if not client:
            raise ValueError(f"MCP server '{server_name}' not connected")
        return await client.call_tool(tool_name, args)
