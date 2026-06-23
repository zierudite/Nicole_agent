"""MCPToolManager — MCP 工具管理器。

职责: 管理 MCP 连接，加载 MCP 工具，包装为 LangChain BaseTool。
参考 Yuxi 的 MCP 服务 + agent-service-toolkit 的 MCP 集成。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from .client import MCPClient, MCPTransportType

logger = logging.getLogger(__name__)


class MCPToolManager:
    """MCP 工具管理器。管理多个 MCP 服务器连接。"""

    def __init__(self):
        self._clients: Dict[str, MCPClient] = {}

    async def load_mcp_tools(
        self,
        configs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """从配置加载 MCP 工具。"""
        tools = []
        for cfg in configs:
            server_name = cfg.get("name", "default")
            transport = MCPTransportType(cfg.get("transport", "stdio"))
            command = cfg.get("command")
            url = cfg.get("url")

            client = MCPClient(server_name, transport, command=command, url=url)
            self._clients[server_name] = client

            try:
                await client.connect()
                server_tools = await client.list_tools()
                tools.extend(server_tools)
            except Exception as e:
                logger.warning(f"MCP server '{server_name}' connect failed: {e}")

        logger.info(f"MCP manager loaded {len(tools)} tools from {len(configs)} servers")
        return tools

    async def disconnect_all(self) -> None:
        """断开所有 MCP 连接。"""
        for name, client in self._clients.items():
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"MCP disconnect '{name}' failed: {e}")
        self._clients.clear()
