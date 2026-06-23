"""ChatService — 对话服务。

管理对话会话、消息历史、调用 Agent Harness 进行推理。
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChatService:
    """对话服务。"""

    def __init__(self, conversation_repo=None, agent_harness=None):
        self.conversation_repo = conversation_repo
        self.agent_harness = agent_harness

    async def create_conversation(
        self, user_id: str, title: str = "", agent_config_id: Optional[str] = None,
    ) -> Dict:
        """创建新对话。"""
        conv = await self.conversation_repo.create({
            "user_id": user_id,
            "title": title or "新对话",
            "agent_config_id": agent_config_id,
        })
        logger.info(f"Conversation created: {conv.get('id')}")
        return conv

    async def send_message(
        self, conversation_id: str, user_id: str, content: str,
    ) -> AsyncIterator[Dict]:
        """发送消息并流式获取回复。"""
        if not self.agent_harness:
            logger.error("agent_harness not configured")
            return

        # 1. 保存用户消息
        await self.conversation_repo.add_message({
            "conversation_id": conversation_id,
            "role": "user",
            "content": content,
        })

        # 2. 创建 Agent 运行
        run_id = await self.agent_harness.create_run(
            user_input=content,
            agent_config=None,
        )

        # 3. 流式获取 Agent 回复
        async for event in self.agent_harness.stream_run(run_id, {}):
            yield event

    async def get_conversation_history(
        self, conversation_id: str, limit: int = 50,
    ) -> List[Dict]:
        """获取对话历史。"""
        return await self.conversation_repo.get_messages(
            conversation_id, limit=limit
        )

    async def list_conversations(
        self, user_id: str, limit: int = 20,
    ) -> List[Dict]:
        """列出用户的对话列表。"""
        return await self.conversation_repo.list_by_user(user_id, limit=limit)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话。"""
        return await self.conversation_repo.delete(conversation_id)
