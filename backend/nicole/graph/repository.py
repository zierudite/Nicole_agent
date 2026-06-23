"""GraphRepository — Neo4j DAO (数据访问对象)。

封装所有 Neo4j 的 CRUD 操作和批量导入。
参考 Yuxi 的图数据访问层设计。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncSession, AsyncDriver

from .schema import EntityType, RelationType, GraphSchema

logger = logging.getLogger(__name__)


class GraphRepository:
    """Neo4j 数据访问层。"""

    def __init__(self, driver: AsyncDriver):
        self.driver = driver
        self._initialized = False

    async def initialize(self) -> None:
        """初始化: 创建约束和索引。"""
        if self._initialized:
            return
        try:
            async with self.driver.session() as session:
                for cypher in GraphSchema.get_create_constraints_cypher():
                    await session.run(cypher)
                for cypher in GraphSchema.get_create_indexes_cypher():
                    await session.run(cypher)
            self._initialized = True
            logger.info("Neo4j schema initialized (constraints + indexes)")
        except Exception as e:
            logger.warning(f"Neo4j init failed: {e}")

    # ── 实体操作 ──

    async def create_entity(
        self,
        entity_type: EntityType,
        properties: Dict[str, Any],
    ) -> Optional[Dict]:
        """创建实体节点。"""
        label = entity_type.value
        props = {k: v for k, v in properties.items() if v is not None}
        cypher = (
            f"CREATE (n:{label} $props) "
            f"RETURN n {{ .* }} AS entity"
        )
        async with self.driver.session() as session:
            result = await session.run(cypher, props=props)
            record = await result.single()
            return record.get("entity") if record else None

    async def get_entity(
        self, entity_type: EntityType, entity_id: str
    ) -> Optional[Dict]:
        """按 ID 获取实体。"""
        label = entity_type.value
        async with self.driver.session() as session:
            result = await session.run(
                f"MATCH (n:{label} {{id: $id}}) RETURN n {{ .* }} AS entity",
                id=entity_id,
            )
            record = await result.single()
            return record.get("entity") if record else None

    async def find_entities(
        self,
        entity_type: Optional[EntityType] = None,
        property_filter: Optional[Dict] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Dict]:
        """按条件查找实体。"""
        match_clause = f"MATCH (n:{entity_type.value})" if entity_type else "MATCH (n)"
        where_clause = ""
        params = {"limit": limit, "skip": skip}
        if property_filter:
            conditions = []
            for i, (k, v) in enumerate(property_filter.items()):
                param = f"val{i}"
                conditions.append(f"n.{k} = ${param}")
                params[param] = v
            where_clause = "WHERE " + " AND ".join(conditions)

        cypher = (
            f"{match_clause} {where_clause} "
            f"RETURN n {{ .* }} AS entity "
            f"SKIP $skip LIMIT $limit"
        )
        async with self.driver.session() as session:
            result = await session.run(cypher, **params)
            return [record.get("entity") async for record in result]

    async def update_entity(
        self,
        entity_type: EntityType,
        entity_id: str,
        properties: Dict[str, Any],
    ) -> Optional[Dict]:
        """更新实体属性。"""
        label = entity_type.value
        set_clause = ", ".join(f"n.{k} = ${k}" for k in properties)
        params = {"id": entity_id, **properties}

        cypher = (
            f"MATCH (n:{label} {{id: $id}}) "
            f"SET {set_clause} "
            f"RETURN n {{ .* }} AS entity"
        )
        async with self.driver.session() as session:
            result = await session.run(cypher, **params)
            record = await result.single()
            return record.get("entity") if record else None

    async def delete_entity(
        self, entity_type: EntityType, entity_id: str
    ) -> bool:
        """删除实体及其所有关系。"""
        label = entity_type.value
        cypher = (
            f"MATCH (n:{label} {{id: $id}}) "
            f"DETACH DELETE n "
            f"RETURN COUNT(n) AS deleted"
        )
        async with self.driver.session() as session:
            result = await session.run(cypher, id=entity_id)
            record = await result.single()
            return record.get("deleted", 0) > 0 if record else False

    # ── 关系操作 ──

    async def create_relation(
        self,
        relation_type: RelationType,
        source_id: str,
        target_id: str,
        properties: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """在两个实体间创建关系。"""
        rel_label = relation_type.value
        props = properties or {}
        prop_str = " $props" if props else ""

        cypher = (
            f"MATCH (a {{id: $source_id}}), (b {{id: $target_id}}) "
            f"CREATE (a)-[r:{rel_label}{prop_str}]->(b) "
            f"RETURN r {{ .* }} AS relation"
        )
        async with self.driver.session() as session:
            result = await session.run(
                cypher, source_id=source_id, target_id=target_id, props=props,
            )
            record = await result.single()
            return record.get("relation") if record else None

    async def get_entity_relations(
        self,
        entity_id: str,
        relation_types: Optional[List[RelationType]] = None,
        direction: str = "both",
        depth: int = 1,
        limit: int = 100,
    ) -> List[Dict]:
        """获取实体的关联关系。"""
        rel_filter = ""
        if relation_types:
            types = "|" + "|".join(r.value for r in relation_types)
            rel_filter = f"[r:{types}]"
        else:
            rel_filter = "[r]"

        if direction == "out":
            pattern = f"(n {{id: $id}})-{rel_filter}->(related)"
        elif direction == "in":
            pattern = f"(n {{id: $id}})<-{rel_filter}-(related)"
        else:
            pattern = f"(n {{id: $id}})-{rel_filter}-(related)"

        cypher = (
            f"MATCH {pattern} "
            f"RETURN n {{ .* }} AS source, "
            f"       type(r) AS relation_type, "
            f"       r {{ .* }} AS relation_props, "
            f"       related {{ .* }} AS target "
            f"LIMIT $limit"
        )
        async with self.driver.session() as session:
            result = await session.run(cypher, id=entity_id, limit=limit)
            return [record.data() async for record in result]

    async def delete_relation(
        self,
        relation_type: RelationType,
        source_id: str,
        target_id: str,
    ) -> bool:
        """删除指定关系。"""
        cypher = (
            f"MATCH (a {{id: $source_id}})"
            f"-[r:{relation_type.value}]->"
            f"(b {{id: $target_id}}) "
            f"DELETE r RETURN COUNT(r) AS deleted"
        )
        async with self.driver.session() as session:
            result = await session.run(
                cypher, source_id=source_id, target_id=target_id
            )
            record = await result.single()
            return record.get("deleted", 0) > 0 if record else False

    # ── 批量操作 ──

    async def batch_create_entities(
        self, entities: List[Dict],
    ) -> int:
        """批量创建实体 (UNWIND)。"""
        if not entities:
            return 0
        label = entities[0].get("type", "Concept")
        cypher = (
            f"UNWIND $entities AS entity "
            f"CREATE (n:{label}) SET n = entity "
            f"RETURN COUNT(n) AS created"
        )
        async with self.driver.session() as session:
            result = await session.run(
                cypher,
                entities=[{k: v for k, v in e.items() if k != "type"} for e in entities],
            )
            record = await result.single()
            count = record.get("created", 0) if record else 0
            logger.info(f"Batch created {count} entities")
            return count

    async def batch_create_relations(
        self, relations: List[Dict],
    ) -> int:
        """批量创建关系 (UNWIND)。"""
        if not relations:
            return 0
        rel_type = relations[0].get("type", "RELATED_TO")
        cypher = (
            f"UNWIND $relations AS rel "
            f"MATCH (a {{id: rel.source_id}}), (b {{id: rel.target_id}}) "
            f"CREATE (a)-[r:{rel_type}]->(b) "
            f"SET r = rel.properties "
            f"RETURN COUNT(r) AS created"
        )
        async with self.driver.session() as session:
            result = await session.run(cypher, relations=relations)
            record = await result.single()
            count = record.get("created", 0) if record else 0
            logger.info(f"Batch created {count} relations")
            return count

    async def close(self) -> None:
        """关闭驱动。"""
        await self.driver.close()
