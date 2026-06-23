"""GraphReasoner — 图谱推理引擎。

在从 Neo4j 获取的图谱数据上执行推理分析。
使用 NetworkX 进行图算法分析 (PageRank、社区发现、最短路径等)。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GraphReasoner:
    """图谱推理引擎。支持多种图算法分析。"""

    async def analyze_ego_network(
        self,
        node_id: str,
        repository,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """分析某个节点的自我中心网络。"""
        try:
            import networkx as nx
        except ImportError:
            logger.warning("networkx not installed, skipping graph analysis")
            return {"error": "networkx not available"}

        try:
            data = await repository.get_entity_relations(node_id, depth=depth)
            G = nx.Graph()

            source = data.get("source", {})
            G.add_node(source.get("id", node_id), **source)

            for neighbor in data.get("neighbors", []):
                ent = neighbor.get("entity", {})
                nid = ent.get("id", "")
                G.add_node(nid, **ent)
                for rel in neighbor.get("relations", []):
                    G.add_edge(node_id, nid, **rel.get("props", {}))

            return {
                "node_count": G.number_of_nodes(),
                "edge_count": G.number_of_edges(),
                "pagerank": self._compute_pagerank(G, top_k=10),
                "communities": self._detect_communities(G),
                "central_nodes": self._central_nodes(G, top_k=5),
            }

        except Exception as e:
            logger.warning(f"Ego network analysis failed: {e}")
            return {"error": str(e)}

    async def find_paths(
        self,
        source_id: str,
        target_id: str,
        repository,
        max_depth: int = 6,
    ) -> List[Dict]:
        """查找两个节点间的最短路径。"""
        query = await repository.get_shortest_path(source_id, target_id, max_depth)
        nodes = query.get("nodes", [])
        relations = query.get("relations", [])

        if not nodes:
            return []

        path = []
        for i, node in enumerate(nodes):
            step = {"node": node}
            if i < len(relations):
                step["relation"] = relations[i]
            path.append(step)
        return path

    async def recommend_related_entities(
        self,
        entity_id: str,
        repository,
        top_k: int = 10,
    ) -> List[Dict]:
        """推荐与指定实体相关的其他实体 (基于共现和 Pagerank)。"""
        try:
            import networkx as nx
        except ImportError:
            return []

        data = await repository.get_entity_relations(entity_id, depth=2)
        G = nx.Graph()
        central_id = entity_id

        # 构建图
        for neighbor in data:
            G.add_node(central_id)
            G.add_node(neighbor["id"])
            G.add_edge(central_id, neighbor["id"])

        if G.number_of_nodes() < 2:
            return []

        # Personalized PageRank
        try:
            personalization = {n: 1.0 if n == central_id else 0.0 for n in G.nodes()}
            pr = nx.pagerank(G, personalization=personalization, alpha=0.85)
            sorted_nodes = sorted(
                [(n, s) for n, s in pr.items() if n != central_id],
                key=lambda x: x[1], reverse=True,
            )
            return [
                {"entity_id": nid, "score": round(score, 4)}
                for nid, score in sorted_nodes[:top_k]
            ]
        except Exception as e:
            logger.warning(f"PageRank recommendation failed: {e}")
            return []

    @staticmethod
    def _compute_pagerank(G, top_k: int = 10) -> List[Dict]:
        """计算 PageRank 值。"""
        try:
            import networkx as nx
            pr = nx.pagerank(G, alpha=0.85)
            sorted_pr = sorted(pr.items(), key=lambda x: x[1], reverse=True)
            return [
                {"node": nid, "score": round(score, 4)}
                for nid, score in sorted_pr[:top_k]
            ]
        except Exception:
            return []

    @staticmethod
    def _detect_communities(G) -> List[List[str]]:
        """检测社区结构。"""
        try:
            import networkx as nx
            from networkx.algorithms.community import greedy_modularity_communities

            communities = list(greedy_modularity_communities(G))
            return [sorted(list(c)) for c in communities[:5]]
        except Exception:
            return []

    @staticmethod
    def _central_nodes(G, top_k: int = 5) -> List[Dict]:
        """计算中心性最高的节点。"""
        try:
            import networkx as nx
            dc = nx.degree_centrality(G)
            bc = nx.betweenness_centrality(G, k=min(top_k * 2, G.number_of_nodes()))
            cc = nx.closeness_centrality(G)

            combined = {}
            for n in G.nodes():
                combined[n] = {
                    "degree": round(dc.get(n, 0), 4),
                    "betweenness": round(bc.get(n, 0), 4),
                    "closeness": round(cc.get(n, 0), 4),
                }

            sorted_nodes = sorted(
                combined.items(),
                key=lambda x: x[1]["degree"] + x[1]["betweenness"],
                reverse=True,
            )
            return [
                {"node": nid, **metrics}
                for nid, metrics in sorted_nodes[:top_k]
            ]
        except Exception:
            return []
