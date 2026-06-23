"""MCPMiddleware — MCP 工具注入中间件。

职责: 将配置的 MCP 工具注入到 Agent 运行时中。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..context import AgentContext
from ..state import PlanReflectState

logger = logging.getLogger(__name__)


@dataclass
class MCPMiddleware:
    """MCP 中间件。将外部 MCP 工具挂载到 Agent 运行上下文。"""

    enabled: bool = True

    async def load_tools(
        self,
        configs: List[Dict[str, Any]],
        context: AgentContext,
    ) -> List[Any]:
        """加载所有配置的 MCP 工具。"""
        if not self.enabled or not configs:
            return []
        tools = []
        for cfg in configs:
            if context.mcp_manager:
                loaded = await context.mcp_manager.load_mcp_tools([cfg])
                tools.extend(loaded)
        logger.info(f"MCP middleware loaded {len(tools)} tools")
        return tools
