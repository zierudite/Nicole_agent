"""CypherQueryBuilder — Cypher 查询构建器。

构建常用图谱查询: 概念关联、最短路径、社区发现、相似度搜索等。
参考 Yuxi 的图谱查询模式。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .schema import EntityType, RelationType


@dataclass
class CypherQuery:
    """封装一条 Cypher 查询及其参数。"""
    cypher: str
    params: Dict[str, Any]


class CypherQueryBuilder:
    """Cypher 查询构建器。提供常用查询模板。"""

    # ── 实体查询 ──

    @staticmethod
    def find_entity_by_name(
        name: str, entity_type: Optional[EntityType] = None,
    ) -> CypherQuery:
        """按名称查找实体 (fuzzy)。"""
        label = f":{entity_type.value}" if entity_type else ""
        return CypherQuery(
            cypher=f"MATCH (n{label}) WHERE n.name CONTAINS $name RETURN n {{ .* }} AS entity",
            params={"name": name},
        )

    @staticmethod
    def find_entities_by_name_batch(
        names: List[str], entity_type: Optional[EntityType] = None,
    ) -> CypherQuery:
        """批量按名称查找实体。"""
        label = f":{entity_type.value}" if entity_type else ""
        return CypherQuery(
            cypher=f"MATCH (n{label}) WHERE n.name IN $names RETURN n {{ .* }} AS entity",
            params={"names": names},
        )

    # ── 关联查询 ──

    @staticmethod
    def get_ego_network(
        entity_id: str, depth: int = 2, max_nodes: int = 100,
    ) -> CypherQuery:
        """获取实体的自我中心网络 (ego-network)。"""
        return CypherQuery(
            cypher=f"""
                MATCH path = (n {{id: $id}})-[*1..{depth}]-(connected)
                WITH n, connected, relationships(path) AS rels
                RETURN n {{ .* }} AS source,
                       collect(DISTINCT {{entity: connected {{ .* }},
                                         relations: [r IN rels | {{type: type(r), props: r {{ .* }} }}]}}) AS neighbors
                LIMIT $limit
            """,
            params={"id": entity_id, "limit": max_nodes},
        )

    @staticmethod
    def get_shortest_path(
        source_id: str, target_id: str, max_depth: int = 6,
    ) -> CypherQuery:
        """查找两个实体间的最短路径。"""
        return CypherQuery(
            cypher=f"""
                MATCH path = shortestPath(
                    (a {{id: $source_id}})-[*..{max_depth}]-(b {{id: $target_id}})
                )
                RETURN [n IN nodes(path) | n {{ .* }}] AS nodes,
                       [r IN relationships(path) | {{type: type(r), props: r {{ .* }} }}] AS relations
            """,
            params={"source_id": source_id, "target_id": target_id},
        )

    @staticmethod
    def get_entity_connections(
        entity_id: str, relation_types: Optional[List[RelationType]] = None,
    ) -> CypherQuery:
        """获取实体所有连接（含关系类型过滤）。"""
        rel_filter = ""
        if relation_types:
            types = "|".join(r.value for r in relation_types)
            rel_filter = f":[r:{types}]"
        return CypherQuery(
            cypher=f"""
                MATCH (n {{id: $id}})-{rel_filter}-(connected)
                RETURN connected {{ .* }} AS entity,
                       type(r) AS relation_type,
                       r {{ .* }} AS relation_props
            """,
            params={"id": entity_id},
        )

    # ── 概念关系查询 ──

    @staticmethod
    def find_related_concepts(
        concept_name: str, min_weight: float = 0.5,
    ) -> CypherQuery:
        """查找与某概念关联的概念 (RELATED_TO)。"""
        return CypherQuery(
            cypher="""
                MATCH (c:Concept {name: $name})-[r:RELATED_TO]-(related:Concept)
                WHERE r.weight >= $min_weight
                RETURN related.name AS concept, r.weight AS weight
                ORDER BY r.weight DESC
            """,
            params={"name": concept_name, "min_weight": min_weight},
        )

    @staticmethod
    def get_concept_hierarchy(root_name: str) -> CypherQuery:
        """获取概念的 IS_A 层级树。"""
        return CypherQuery(
            cypher="""
                MATCH path = (root:Concept {name: $name})-[:IS_A*0..]->(sub:Concept)
                RETURN [n IN nodes(path) | n.name] AS hierarchy
            """,
            params={"name": root_name},
        )

    # ── 笔记关联查询 ──

    @staticmethod
    def get_notes_for_concept(
        concept_name: str, limit: int = 20,
    ) -> CypherQuery:
        """获取提及某概念的所有笔记。"""
        return CypherQuery(
            cypher="""
                MATCH (c:Concept {name: $name})<-[:MENTIONS]-(n:Note)
                RETURN n {{ .* }} AS note
                ORDER BY n.updated_at DESC
                LIMIT $limit
            """,
            params={"name": concept_name, "limit": limit},
        )

    @staticmethod
    def get_notes_by_tag(tag_name: str, limit: int = 20) -> CypherQuery:
        """获取带有某标签的所有笔记。"""
        return CypherQuery(
            cypher="""
                MATCH (t:Tag {name: $name})<-[:HAS_TAG]-(n:Note)
                RETURN n {{ .* }} AS note
                ORDER BY n.updated_at DESC
                LIMIT $limit
            """,
            params={"name": tag_name, "limit": limit},
        )

    @staticmethod
    def get_related_notes_by_concept(
        note_id: str, max_concepts: int = 5, max_notes: int = 10,
    ) -> CypherQuery:
        """通过共同概念查找相关笔记。"""
        return CypherQuery(
            cypher=f"""
                MATCH (n:Note {{id: $id}})-[:MENTIONS]->(c:Concept)
                WITH n, collect(c) AS concepts
                MATCH (related:Note)-[:MENTIONS]->(c2:Concept)
                WHERE related.id <> $id AND c2 IN concepts
                WITH related, count(DISTINCT c2) AS common_concepts
                RETURN related {{ .* }} AS note, common_concepts
                ORDER BY common_concepts DESC
                LIMIT $limit
            """,
            params={"id": note_id, "limit": max_notes},
        )

    # ── 聚合与统计 ──

    @staticmethod
    def get_most_mentioned_concepts(limit: int = 20) -> CypherQuery:
        """获取被提及最多的概念。"""
        return CypherQuery(
            cypher="""
                MATCH (c:Concept)<-[:MENTIONS]-()
                RETURN c.name AS concept, COUNT(*) AS mention_count
                ORDER BY mention_count DESC
                LIMIT $limit
            """,
            params={"limit": limit},
        )

    @staticmethod
    def get_entity_count_by_type() -> CypherQuery:
        """统计各类型实体的数量。"""
        return CypherQuery(
            cypher="""
                MATCH (n)
                RETURN labels(n) AS type, COUNT(*) AS count
                ORDER BY count DESC
            """,
            params={},
        )

    @staticmethod
    def search_entities(keyword: str, limit: int = 20) -> CypherQuery:
        """全局实体搜索 (按名称/标题模糊匹配)。"""
        return CypherQuery(
            cypher="""
                MATCH (n)
                WHERE n.name CONTAINS $keyword OR n.title CONTAINS $keyword
                RETURN labels(n)[0] AS type, n {{ .* }} AS entity
                LIMIT $limit
            """,
            params={"keyword": keyword, "limit": limit},
        )
