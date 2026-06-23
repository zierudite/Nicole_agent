"""GraphService — 知识图谱服务。

封装图谱的查询、推理、可视化数据生成等业务逻辑。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..graph.repository import GraphRepository
from ..graph.reasoner import GraphReasoner
from ..graph.extractor import EntityRelationExtractor
from ..graph.query_builder import CypherQueryBuilder
from ..graph.schema import EntityType, RelationType

logger = logging.getLogger(__name__)


class GraphService:
    """知识图谱服务。"""

    def __init__(
        self,
        repository: Optional[GraphRepository] = None,
        reasoner: Optional[GraphReasoner] = None,
        extractor: Optional[EntityRelationExtractor] = None,
    ):
        self.repository = repository
        self.reasoner = reasoner or GraphReasoner()
        self.extractor = extractor or EntityRelationExtractor()

    async def search_entities(
        self, keyword: str, limit: int = 20,
    ) -> List[Dict]:
        """搜索实体。"""
        query = CypherQueryBuilder.search_entities(keyword, limit)
        if self.repository:
            async with self.repository.driver.session() as session:
                result = await session.run(query.cypher, **query.params)
                return [record.data() async for record in result]
        return []

    async def get_entity_detail(self, entity_id: str) -> Dict:
        """获取实体详情及其关联。"""
        entity = None
        for et in EntityType:
            entity = await self.repository.get_entity(et, entity_id)
            if entity:
                break

        relations = await self.repository.get_entity_relations(entity_id)

        return {
            "entity": entity or {},
            "relations": relations,
            "relation_count": len(relations),
        }

    async def get_ego_network(
        self, entity_id: str, depth: int = 2,
    ) -> Dict:
        """获取自我中心网络数据（供前端可视化）。"""
        data = await self.repository.get_entity_relations(entity_id, depth=depth)

        # 转换为前端 vis-network 格式
        nodes = []
        edges = []
        seen_nodes = set()

        source = data.get("source", {})
        sid = source.get("id", entity_id)
        nodes.append({"id": sid, "label": source.get("name", sid), "group": "center"})
        seen_nodes.add(sid)

        for neighbor in data.get("neighbors", []):
            ent = neighbor.get("entity", {})
            nid = ent.get("id", "")
            if nid not in seen_nodes:
                nodes.append({"id": nid, "label": ent.get("name", nid)})
                seen_nodes.add(nid)
            for rel in neighbor.get("relations", []):
                edges.append({
                    "from": sid,
                    "to": nid,
                    "label": rel.get("type", ""),
                })

        return {"nodes": nodes, "edges": edges}

    async def find_path(
        self, source_id: str, target_id: str, max_depth: int = 6,
    ) -> List[Dict]:
        """查找两个实体间的最短路径。"""
        return await self.reasoner.find_paths(
            source_id, target_id, self.repository, max_depth,
        )

    async def extract_from_text(
        self, text: str, note_id: Optional[str] = None,
    ) -> Dict:
        """从文本中抽取实体关系并入库。"""
        return await self.extractor.extract_and_link(
            text, note_id, self.repository,
        )

    async def analyze_entity(
        self, entity_id: str,
    ) -> Dict:
        """分析实体的图谱特征。"""
        return await self.reasoner.analyze_ego_network(
            entity_id, self.repository,
        )

    async def recommend_related(
        self, entity_id: str, top_k: int = 10,
    ) -> List[Dict]:
        """推荐相关实体。"""
        return await self.reasoner.recommend_related_entities(
            entity_id, self.repository, top_k,
        )

    async def get_statistics(self) -> Dict:
        """获取图谱统计信息。"""
        if not self.repository:
            return {}
        query = CypherQueryBuilder.get_entity_count_by_type()
        async with self.repository.driver.session() as session:
            result = await session.run(query.cypher)
            counts = {r["type"][0] if isinstance(r["type"], list) else r["type"]: r["count"]
                      async for r in result}
        return {"entity_counts": counts, "total": sum(counts.values())}
