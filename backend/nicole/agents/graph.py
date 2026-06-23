"""Plan-Reflection 主状态图构建器。

基于 LangGraph StateGraph 构建 8 节点 Plan → Execute → Reflect 循环。
参考 Yuxi 的 Agent graph 构造模式 + agent-service-toolkit 的 LangGraph 最佳实践。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Literal

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.postgres import PostgresSaver

from .state import PlanReflectState
from .base import AgentNode
from .buildin.orchestrator import OrchestratorAgent
from .buildin.planner import PlannerAgent
from .buildin.executor import ExecutorAgent
from .buildin.reflector import ReflectorAgent
from .buildin.synthesizer import SynthesizerAgent
from .buildin.rag_agent import RAGAgent
from .buildin.graph_agent import GraphAgent
from .buildin.steward import KnowledgeStewardAgent

logger = logging.getLogger(__name__)


def route_by_intent(state: PlanReflectState) -> Literal["rag_agent", "graph_agent", "executor"]:
    """根据 Planner 分析的意图路由到不同的执行 Agent。"""
    intent = state.get("user_intent", "general")
    if intent == "retrieval":
        return "rag_agent"
    elif intent == "graph_query":
        return "graph_agent"
    return "executor"


def should_revise(state: PlanReflectState) -> Literal["executor", "synthesizer"]:
    """根据 Reflector 的评估决定：修正还是综合输出。"""
    if (
        state.get("needs_revision", False)
        and state.get("revision_cycles", 0) < state.get("max_revisions", 3)
    ):
        logger.info(
            f"Revision needed (cycle {state['revision_cycles']}/{state['max_revisions']})"
        )
        return "executor"
    return "synthesizer"


def build_plan_reflect_graph(
    checkpointer: PostgresSaver | None = None,
) -> StateGraph:
    """构建完整的 Plan-Reflection 状态图。

    节点流程:
        orchestrator → planner → (rag_agent | graph_agent | executor)
            → executor → reflector → ( revise → executor | synthesize → synthesizer)
            → knowledge_steward → END
    """
    builder = StateGraph(PlanReflectState)

    # 实例化所有 Agent
    orchestrator = AgentNode(OrchestratorAgent())
    planner = AgentNode(PlannerAgent())
    rag_agent = AgentNode(RAGAgent())
    graph_agent = AgentNode(GraphAgent())
    executor = AgentNode(ExecutorAgent())
    reflector = AgentNode(ReflectorAgent())
    synthesizer = AgentNode(SynthesizerAgent())
    steward = AgentNode(KnowledgeStewardAgent())

    # 注册节点
    builder.add_node("orchestrator", orchestrator)
    builder.add_node("planner", planner)
    builder.add_node("rag_agent", rag_agent)
    builder.add_node("graph_agent", graph_agent)
    builder.add_node("executor", executor)
    builder.add_node("reflector", reflector)
    builder.add_node("synthesizer", synthesizer)
    builder.add_node("knowledge_steward", steward)

    # 设置入口
    builder.set_entry_point("orchestrator")

    # 定义边
    builder.add_edge("orchestrator", "planner")
    builder.add_conditional_edges("planner", route_by_intent, {
        "rag_agent": "rag_agent",
        "graph_agent": "graph_agent",
        "executor": "executor",
    })
    builder.add_edge("rag_agent", "executor")
    builder.add_edge("graph_agent", "executor")
    builder.add_edge("executor", "reflector")
    builder.add_conditional_edges("reflector", should_revise, {
        "revise": "executor",
        "synthesize": "synthesizer",
    })
    builder.add_edge("synthesizer", "knowledge_steward")
    builder.add_edge("knowledge_steward", END)

    # 编译
    graph = builder.compile(checkpointer=checkpointer)
    return graph
