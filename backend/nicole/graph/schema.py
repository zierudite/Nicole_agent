"""知识图谱 Schema 定义。

定义 Neo4j 中的节点标签、关系类型和属性结构。
参考 Yuxi 的图谱 Schema 设计。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EntityType(str, Enum):
    """实体节点类型。"""
    NOTE = "Note"
    CONCEPT = "Concept"
    TAG = "Tag"
    PERSON = "Person"
    PROJECT = "Project"
    DOCUMENT = "Document"
    ORGANIZATION = "Organization"


class RelationType(str, Enum):
    """关系类型。"""
    HAS_TAG = "HAS_TAG"              # Note -> Tag
    MENTIONS = "MENTIONS"            # Note -> Concept
    CREATED_BY = "CREATED_BY"        # Note -> Person
    BELONGS_TO = "BELONGS_TO"        # Note -> Project
    REFERENCES = "REFERENCES"        # Note -> Document
    NEXT = "NEXT"                    # Note -> Note (顺序)
    RELATED_TO = "RELATED_TO"        # Concept -> Concept
    IS_A = "IS_A"                    # Concept -> Concept (层级)
    PART_OF = "PART_OF"             # Concept -> Concept (组成)
    CO_OCCURS = "CO_OCCURS"         # 概念共现


@dataclass
class EntitySchema:
    """实体节点 Schema 定义。"""
    type: EntityType
    label: str                       # Neo4j 标签名
    properties: Dict[str, str]       # 属性名 -> 属性类型
    required_properties: List[str] = field(default_factory=list)
    indexed_properties: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "label": self.label,
            "properties": self.properties,
            "required": self.required_properties,
            "indexed": self.indexed_properties,
        }


@dataclass
class RelationSchema:
    """关系 Schema 定义。"""
    type: RelationType
    label: str
    source_types: List[EntityType]   # 源实体类型
    target_types: List[EntityType]   # 目标实体类型
    properties: Dict[str, str] = field(default_factory=dict)


class GraphSchema:
    """完整图 Schema。包含所有实体和关系定义。"""

    # 节点 Schema
    ENTITIES = {
        EntityType.NOTE: EntitySchema(
            type=EntityType.NOTE, label="Note",
            properties={"id": "str", "title": "str", "content": "str",
                       "created_at": "datetime", "updated_at": "datetime"},
            required_properties=["id", "title"],
            indexed_properties=["title"],
        ),
        EntityType.CONCEPT: EntitySchema(
            type=EntityType.CONCEPT, label="Concept",
            properties={"id": "str", "name": "str", "definition": "str"},
            required_properties=["id", "name"],
            indexed_properties=["name"],
        ),
        EntityType.TAG: EntitySchema(
            type=EntityType.TAG, label="Tag",
            properties={"id": "str", "name": "str", "color": "str"},
            required_properties=["id", "name"],
        ),
        EntityType.PERSON: EntitySchema(
            type=EntityType.PERSON, label="Person",
            properties={"id": "str", "name": "str", "email": "str"},
            required_properties=["id", "name"],
        ),
        EntityType.PROJECT: EntitySchema(
            type=EntityType.PROJECT, label="Project",
            properties={"id": "str", "name": "str", "description": "str"},
            required_properties=["id", "name"],
        ),
        EntityType.DOCUMENT: EntitySchema(
            type=EntityType.DOCUMENT, label="Document",
            properties={"id": "str", "name": "str", "type": "str", "path": "str"},
            required_properties=["id", "name"],
        ),
    }

    # 关系 Schema
    RELATIONS = {
        RelationType.HAS_TAG: RelationSchema(
            type=RelationType.HAS_TAG, label="HAS_TAG",
            source_types=[EntityType.NOTE],
            target_types=[EntityType.TAG],
        ),
        RelationType.MENTIONS: RelationSchema(
            type=RelationType.MENTIONS, label="MENTIONS",
            source_types=[EntityType.NOTE],
            target_types=[EntityType.CONCEPT],
            properties={"context": "str", "confidence": "float"},
        ),
        RelationType.CREATED_BY: RelationSchema(
            type=RelationType.CREATED_BY, label="CREATED_BY",
            source_types=[EntityType.NOTE, EntityType.PROJECT],
            target_types=[EntityType.PERSON],
        ),
        RelationType.BELONGS_TO: RelationSchema(
            type=RelationType.BELONGS_TO, label="BELONGS_TO",
            source_types=[EntityType.NOTE],
            target_types=[EntityType.PROJECT],
        ),
        RelationType.REFERENCES: RelationSchema(
            type=RelationType.REFERENCES, label="REFERENCES",
            source_types=[EntityType.NOTE],
            target_types=[EntityType.DOCUMENT],
        ),
        RelationType.NEXT: RelationSchema(
            type=RelationType.NEXT, label="NEXT",
            source_types=[EntityType.NOTE],
            target_types=[EntityType.NOTE],
        ),
        RelationType.RELATED_TO: RelationSchema(
            type=RelationType.RELATED_TO, label="RELATED_TO",
            source_types=[EntityType.CONCEPT],
            target_types=[EntityType.CONCEPT],
            properties={"weight": "float"},
        ),
        RelationType.IS_A: RelationSchema(
            type=RelationType.IS_A, label="IS_A",
            source_types=[EntityType.CONCEPT],
            target_types=[EntityType.CONCEPT],
        ),
    }

    @classmethod
    def get_entity_labels(cls) -> List[str]:
        return [e.label for e in cls.ENTITIES.values()]

    @classmethod
    def get_relation_types(cls) -> List[str]:
        return [r.label for r in cls.RELATIONS.values()]

    @classmethod
    def get_create_constraints_cypher(cls) -> List[str]:
        """生成创建唯一约束的 Cypher 语句。"""
        cyphers = []
        for entity in cls.ENTITIES.values():
            cyphers.append(
                f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{entity.label}) "
                f"REQUIRE n.id IS UNIQUE;"
            )
        return cyphers

    @classmethod
    def get_create_indexes_cypher(cls) -> List[str]:
        """生成创建索引的 Cypher 语句。"""
        cyphers = []
        for entity in cls.ENTITIES.values():
            for prop in entity.indexed_properties:
                cyphers.append(
                    f"CREATE INDEX IF NOT EXISTS FOR (n:{entity.label}) "
                    f"ON (n.{prop});"
                )
        return cyphers
