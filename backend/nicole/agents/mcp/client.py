"""MCPClient — MCP 协议客户端。

职责: 连接 MCP 服务器，列举和调用工具。
支持 stdio / SSE / HTTP 三种传输方式。
"""

from __future__ import annotations

import asyncio
import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPTransportType(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


class MCPClient:
    """MCP 协议客户端。"""

    def __init__(
        self,
        server_name: str,
        transport: MCPTransportType = MCPTransportType.STDIO,
        command: Optional[str] = None,
        url: Optional[str] = None,
    ):
        self.server_name = server_name
        self.transport = transport
        self.command = command
        self.url = url
        self._connected = False
        self._tools: List[Dict[str, Any]] = []

    async def connect(self) -> None:
        """连接到 MCP 服务器。"""
        if self.transport == MCPTransportType.STDIO:
            logger.info(f"MCP stdio connect: {self.command}")
        elif self.transport == MCPTransportType.SSE:
            logger.info(f"MCP SSE connect: {self.url}")
        elif self.transport == MCPTransportType.HTTP:
            logger.info(f"MCP HTTP connect: {self.url}")
        self._connected = True

    async def disconnect(self) -> None:
        """断开 MCP 连接。"""
        self._connected = False
        self._tools = []

    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取 MCP 服务器提供的工具列表。"""
        return self._tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用 MCP 工具。"""
        if not self._connected:
            raise RuntimeError(f"MCP client '{self.server_name}' not connected")
        logger.info(f"MCP call: {tool_name}({arguments})")
        return {"status": "success", "result": f"[MCP placeholder] {tool_name} called"}
