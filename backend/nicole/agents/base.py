from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from langgraph.graph.state import CompiledStateGraph
from langgraph.graph import StateGraph

from .state import PlanReflectState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """所有 Agent 的基类。

    参考 Yuxi 的 BaseAgent 设计 + agent-service-toolkit 的 Pydantic 化风格。
    每个 Agent 是一个独立的 LangGraph 节点，可被组合到 Plan-Reflection 主图中
    """

    agent_id: str
    name: str
    description: str
    system_prompt: str

    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str = "",
        system_prompt: str = "",
    ):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.system_prompt = system_prompt

    @abstractmethod
    async def run(self, state: PlanReflectState) -> PlanReflectState:
        """执行 Agent 节点逻辑，接收并返回状态。"""
        ...

    def build_sub_graph(self) -> Optional[CompiledStateGraph]:
        """如果 Agent 内部有子图，在此构建。默认返回 None。"""
        return None

    def get_tools(self) -> list:
        """返回该 Agent 可用的工具列表。"""
        return []


class AgentNode:
    """LangGraph 节点包装器，将 BaseAgent 适配为可调用节点。"""

    def __init__(self, agent: BaseAgent):
        self.agent = agent

    async def __call__(self, state: PlanReflectState) -> PlanReflectState:
        logger.info(f"Running agent node: {self.agent.name}")
        try:
            return await self.agent.run(state)
        except Exception as e:
            logger.exception(f"Agent {self.agent.name} failed: {e}")
            state["errors"].append(f"[{self.agent.name}] {str(e)}")
            return state
