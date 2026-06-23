"""ToolRegistry — 工具注册表。

职责: 统一管理所有可用工具（内置 + MCP + Skills），提供注册和查找功能。
参考 agent-service-toolkit 的工具注册 + Yuxi 的 toolkit 设计。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """工具基类。"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行工具逻辑。"""
        ...

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description}


class ToolRegistry:
    """工具注册表。管理所有可用工具的增删查。"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册一个工具。"""
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> None:
        """注销一个工具。"""
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[BaseTool]:
        """按名称获取工具。"""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """列出所有已注册工具。"""
        return list(self._tools.values())

    def has_tool(self, name: str) -> bool:
        """检查工具是否存在。"""
        return name in self._tools

    def register_builtin(self) -> None:
        """注册所有内置工具。"""
        from .builtin_tools import (
            FileReadTool, FileWriteTool, WebSearchTool,
            PythonExecTool, NoteQueryTool, KnowledgeSearchTool,
        )
        for tool_cls in [
            FileReadTool, FileWriteTool, WebSearchTool,
            PythonExecTool, NoteQueryTool, KnowledgeSearchTool,
        ]:
            self.register(tool_cls())
        logger.info("Built-in tools registered")
