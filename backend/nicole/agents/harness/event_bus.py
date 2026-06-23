"""EventBus — 事件总线。

职责: 发送 Agent 运行事件到前端（SSE）和其他消费者。
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOKEN_USAGE = "token_usage"
    INTERRUPT = "interrupt"
    MESSAGE = "message"


@dataclass
class RunEvent:
    run_id: str
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None


class EventBus:
    """基于内存的简单事件总线。生产环境可替换为 Redis Pub/Sub。"""

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._history: List[RunEvent] = []
        self._max_history = 1000

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """订阅特定类型的事件。"""
        self._subscribers.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """取消订阅。"""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb != callback
            ]

    async def publish(self, event: RunEvent) -> None:
        """发布事件到所有订阅者。"""
        # 记录历史
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # 通知订阅者
        callbacks = self._subscribers.get(event.event_type, [])
        for cb in callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(event)
                else:
                    cb(event)
            except Exception as e:
                logger.error(f"Event callback failed: {e}")

    async def get_events(
        self,
        run_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[RunEvent]:
        """获取历史事件。"""
        events = self._history
        if run_id:
            events = [e for e in events if e.run_id == run_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def to_sse(self, event: RunEvent) -> str:
        """将事件格式化为 SSE (Server-Sent Events) 格式。"""
        data = json.dumps({
            "run_id": event.run_id,
            "event": event.event_type.value,
            "data": event.data,
        }, ensure_ascii=False)
        return f"event: {event.event_type.value}\ndata: {data}\n\n"
