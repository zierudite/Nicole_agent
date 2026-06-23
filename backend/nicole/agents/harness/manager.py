"""AgentHarness — Agent 运行管理器。

职责: 统一管理 Agent 生命周期、错误重试、资源管控、状态持久化。
参考 Yuxi 的 Harness 设计 + agent-service-toolkit 的 Service 层 + LangGraph Checkpointer。
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph.state import CompiledStateGraph

from ..context import AgentContext, AgentConfig
from ..graph import build_plan_reflect_graph
from ..state import PlanReflectState, create_initial_state
from .event_bus import EventBus, EventType, RunEvent

logger = logging.getLogger(__name__)


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunContext:
    """单次 Agent 运行的上下文。"""

    def __init__(self, run_id: str, graph: CompiledStateGraph, config: Dict[str, Any]):
        self.run_id = run_id
        self.graph = graph
        self.config = config
        self.status = RunStatus.PENDING
        self.state: Optional[PlanReflectState] = None
        self.error: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None


class AgentHarness:
    """Agent 运行时管理器。

    核心职责:
    - 注册/运行/中断/恢复 Agent
    - 通过 LangGraph Checkpointer 实现状态持久化
    - 通过 EventBus 推送运行事件
    """

    def __init__(
        self,
        checkpointer: Optional[PostgresSaver] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.checkpointer = checkpointer
        self.event_bus = event_bus or EventBus()
        self._runs: Dict[str, RunContext] = {}

    async def create_run(
        self,
        agent_config: AgentConfig,
        user_input: str,
    ) -> str:
        """创建一个新的 Agent 运行实例。"""
        run_id = str(uuid.uuid4())
        graph = build_plan_reflect_graph(checkpointer=self.checkpointer)

        run_config = {
            "configurable": {
                "thread_id": run_id,
                "checkpointer": self.checkpointer,
            }
        }

        context = RunContext(run_id, graph, run_config)
        context.state = create_initial_state(user_input, run_id)
        self._runs[run_id] = context

        await self.event_bus.publish(RunEvent(
            run_id=run_id,
            event_type=EventType.RUN_STARTED,
            data={"agent_config": agent_config.model_dump()},
        ))

        logger.info(f"Run created: {run_id}")
        return run_id

    async def stream_run(
        self,
        run_id: str,
        input_state: Dict[str, Any],
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式执行 Agent 并推送事件。"""
        ctx = self._runs.get(run_id)
        if not ctx:
            raise ValueError(f"Run {run_id} not found")

        ctx.status = RunStatus.RUNNING
        ctx.started_at = datetime.utcnow()

        try:
            async for event in ctx.graph.astream_events(
                input_state,
                ctx.config,
                version="v2",
            ):
                event_type = event.get("event", "")
                if "on_chain_start" in event_type:
                    node_name = event.get("name", "unknown")
                    await self.event_bus.publish(RunEvent(
                        run_id=run_id,
                        event_type=EventType.NODE_STARTED,
                        data={"node": node_name},
                    ))
                elif "on_chain_end" in event_type:
                    node_name = event.get("name", "unknown")
                    await self.event_bus.publish(RunEvent(
                        run_id=run_id,
                        event_type=EventType.NODE_COMPLETED,
                        data={"node": node_name},
                    ))

                yield event

            ctx.status = RunStatus.COMPLETED
            ctx.completed_at = datetime.utcnow()
            await self.event_bus.publish(RunEvent(
                run_id=run_id,
                event_type=EventType.RUN_COMPLETED,
                data={"status": "completed"},
            ))

        except Exception as e:
            ctx.status = RunStatus.FAILED
            ctx.error = str(e)
            logger.exception(f"Run {run_id} failed")
            await self.event_bus.publish(RunEvent(
                run_id=run_id,
                event_type=EventType.RUN_FAILED,
                data={"error": str(e)},
            ))
            raise

    async def cancel_run(self, run_id: str) -> None:
        """取消正在运行的 Agent。"""
        ctx = self._runs.get(run_id)
        if ctx and ctx.status == RunStatus.RUNNING:
            ctx.status = RunStatus.CANCELLED
            await self.event_bus.publish(RunEvent(
                run_id=run_id,
                event_type=EventType.RUN_CANCELLED,
                data={},
            ))
            logger.info(f"Run cancelled: {run_id}")

    async def get_run_status(self, run_id: str) -> Optional[RunStatus]:
        """获取运行状态。"""
        ctx = self._runs.get(run_id)
        return ctx.status if ctx else None

    async def list_runs(
        self,
        status: Optional[RunStatus] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """列出运行记录。"""
        runs = []
        for run_id, ctx in self._runs.items():
            if status and ctx.status != status:
                continue
            runs.append({
                "run_id": run_id,
                "status": ctx.status.value,
                "started_at": ctx.started_at,
                "completed_at": ctx.completed_at,
                "error": ctx.error,
            })
        return sorted(runs, key=lambda x: x.get("started_at") or datetime.min, reverse=True)[:limit]
