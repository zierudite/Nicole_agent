from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class PlanReflectState(TypedDict):
    """Plan-Reflection 模式的全局状态定义。

    贯穿整个 Agent 运行生命周期的所有状态字段。
    从用户输入 -> 计划 -> 执行 -> 反思 -> 修正 -> 综合 -> 知识沉淀。
    """

    # ── 用户输入与上下文 ──
    user_input: str
    conversation_history: List[Dict[str, str]]
    user_intent: Optional[str]

    # ── 计划阶段 ──
    plan: Optional[str]
    plan_steps: List[str]
    current_step: int

    # ── 执行阶段（多 Agent 结果收集） ──
    agent_results: Dict[str, Any]
    rag_context: Optional[str]
    graph_context: Optional[str]
    tool_results: List[Dict[str, Any]]

    # ── 反思阶段 ──
    reflection: Optional[str]
    quality_score: Optional[float]
    needs_revision: bool
    revision_cycles: int
    max_revisions: int

    # ── 综合输出 ──
    synthesized_answer: str
    citations: List[Dict[str, str]]
    knowledge_updates: List[Dict[str, Any]]

    # ── 运行元数据 ──
    trace_id: str
    errors: List[str]


def create_initial_state(user_input: str, trace_id: str) -> PlanReflectState:
    """创建初始状态。"""
    return {
        "user_input": user_input,
        "conversation_history": [],
        "user_intent": None,
        "plan": None,
        "plan_steps": [],
        "current_step": 0,
        "agent_results": {},
        "rag_context": None,
        "graph_context": None,
        "tool_results": [],
        "reflection": None,
        "quality_score": None,
        "needs_revision": False,
        "revision_cycles": 0,
        "max_revisions": 3,
        "synthesized_answer": "",
        "citations": [],
        "knowledge_updates": [],
        "trace_id": trace_id,
        "errors": [],
    }
