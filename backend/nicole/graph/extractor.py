"""EntityRelationExtractor — 实体与关系抽取器。

使用 LLM 从文本中抽取实体和关系，更新知识图谱。
参考 Yuxi 的图谱构建 + LightRAG 的实体抽取思路。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from .schema import EntityType, RelationType

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """你是一个知识图谱实体关系抽取专家。
从以下文本中抽取实体和关系。

实体类型: Note(笔记), Concept(概念), Tag(标签), Person(人物), Project(项目)
关系类型: MENTIONS(提及), RELATED_TO(相关), IS_A(属于), PART_OF(组成部分)

文本:
{text}

请返回 JSON 格式:
{{
  "entities": [
    {{"name": "实体名称", "type": "Concept|Tag|Person|Project", "definition": "简要定义"}}
  ],
  "relations": [
    {{"source": "源实体名", "target": "目标实体名", "relation": "MENTIONS|RELATED_TO|IS_A|PART_OF", "weight": 0.8}}
  ]
}}
"""


class EntityRelationExtractor:
    """从文本中抽取实体和关系。"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def extract(
        self,
        text: str,
        existing_entities: Optional[List[str]] = None,
    ) -> Tuple[List[Dict], List[Dict]]:
        """从文本中抽取实体和关系。

        Returns:
            (entities, relations) 元组
        """
        if not text or len(text.strip()) < 5:
            return [], []

        if self.llm_client:
            return await self._extract_with_llm(text)
        else:
            return self._extract_with_rules(text, existing_entities)

    async def _extract_with_llm(
        self, text: str,
    ) -> Tuple[List[Dict], List[Dict]]:
        """使用 LLM 抽取 (高精度)。"""
        try:
            prompt = EXTRACTION_PROMPT.format(text=text[:3000])
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            content = response.get("content", "{}")
            # 清理可能的 Markdown 代码块包裹
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                content = content.rsplit("```", 1)[0]
            data = json.loads(content)
            entities = data.get("entities", [])
            relations = data.get("relations", [])

            logger.info(f"LLM extracted {len(entities)} entities, {len(relations)} relations")
            return entities, relations

        except json.JSONDecodeError as e:
            logger.warning(f"LLM response parse failed: {e}")
            return [], []
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return [], []

    def _extract_with_rules(
        self, text: str,
        existing_entities: Optional[List[str]] = None,
    ) -> Tuple[List[Dict], List[Dict]]:
        """基于规则的实体抽取 (轻量快速)。"""
        import re

        entities = []
        existing = set(existing_entities or [])

        # 1. 提取大写/引号内的词组 (可能的概念)
        pattern = r"[""\u201c]([^"\u201d]{2,50})[""\u201d]"
        matches = re.findall(pattern, text)
        for name in matches:
            if name not in existing and len(name) >= 2:
                entities.append({
                    "name": name.strip(),
                    "type": "Concept",
                    "definition": "",
                })
                existing.add(name)

        # 2. 专业术语模式 (括号内英文)
        pattern = r"[\u4e00-\u9fff]{2,10}\([A-Za-z]{2,30}\)"
        matches = re.findall(pattern, text)
        for match in matches:
            if match not in existing:
                entities.append({
                    "name": match.strip(),
                    "type": "Concept",
                    "definition": "",
                })
                existing.add(match)

        logger.info(f"Rule-based extracted {len(entities)} entities")
        return entities, []

    async def extract_and_link(
        self,
        text: str,
        note_id: str,
        repository,
        max_entities: int = 20,
    ) -> Dict:
        """抽取实体并直接链接到知识图谱。"""
        entities, relations = await self.extract(text)

        # 1. 创建或查找实体
        created_count = 0
        for ent in entities[:max_entities]:
            existing = await repository.find_entities(
                EntityType.CONCEPT,
                property_filter={"name": ent["name"]},
                limit=1,
            )
            if not existing:
                await repository.create_entity(
                    EntityType.CONCEPT,
                    {"id": f"concept_{hash(ent['name'])}",
                     "name": ent["name"],
                     "definition": ent.get("definition", "")},
                )
                created_count += 1

            # 2. 创建 MENTIONS 关系
            if note_id:
                target_id = existing[0].get("id") if existing else f"concept_{hash(ent['name'])}"
                await repository.create_relation(
                    RelationType.MENTIONS,
                    note_id,
                    target_id,
                    properties={"context": text[:200], "confidence": 0.7},
                )

        return {"extracted": len(entities), "created": created_count}
