# -*- coding: utf-8 -*-
import json
import os
import networkx as nx
from typing import List, Dict, Any

class KnowledgeGraphManager:
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.graph_file = os.path.join(project_dir, "knowledge_graph.json")
        self.graph = nx.DiGraph()
        self._load()

    def _load(self):
        if os.path.exists(self.graph_file):
            try:
                with open(self.graph_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"无法加载图谱，将创建新图谱: {e}")
                self.graph = nx.DiGraph()

    def _save(self):
        try:
            data = nx.node_link_data(self.graph)
            with open(self.graph_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"保存图谱失败: {e}")

    def add_triples(self, triples: List[Dict[str, str]]):
        """
        添加三元组。格式：
        [
            {"source": "萧炎", "relation": "拥有", "target": "异火", "type": "character"}
        ]
        """
        for t in triples:
            source = t.get("source")
            relation = t.get("relation")
            target = t.get("target")
            node_type = t.get("type", "unknown")
            
            if not source or not target or not relation:
                continue
                
            if not self.graph.has_node(source):
                self.graph.add_node(source, type=node_type)
            if not self.graph.has_node(target):
                self.graph.add_node(target, type=node_type)
                
            self.graph.add_edge(source, target, relation=relation)
            
        self._save()

    def get_subgraph_context(self, entities: List[str], max_depth: int = 1) -> str:
        """
        根据核心实体列表，召回 N 跳范围内的关系描述
        """
        if not entities:
            return ""
            
        visited_edges = set()
        relations = []
        
        for entity in entities:
            if not self.graph.has_node(entity):
                continue
                
            # 使用 BFS 查找 N 跳内的边
            edges = nx.bfs_edges(self.graph, entity, depth_limit=max_depth)
            for u, v in edges:
                if (u, v) not in visited_edges:
                    visited_edges.add((u, v))
                    rel = self.graph.edges[u, v].get("relation", "关联")
                    relations.append(f"[{u}] {rel} [{v}]")
                    
            # 无向图还需要查找指向该节点的前驱
            # 简化起见，我们直接遍历整个图寻找涉及这些实体的边
            # 对于大型图这种遍历较慢，但在我们的场景下足够快
        
        # 为了更完整的 1跳 提取，我们可以直接扫描所有边
        all_relations = []
        for u, v, data in self.graph.edges(data=True):
            if u in entities or v in entities:
                rel = data.get("relation", "关联")
                all_relations.append(f"{u} {rel} {v}")
                
        # 去重
        all_relations = list(set(all_relations))
        
        if not all_relations:
            return ""
            
        return "【图谱记忆（相关实体状态）】\n" + "\n".join(all_relations)

    def get_frontend_data(self) -> Dict[str, Any]:
        """
        输出前端 react-force-graph 需要的数据格式
        """
        nodes = []
        for node, data in self.graph.nodes(data=True):
            nodes.append({"id": node, "group": data.get("type", "unknown")})
            
        links = []
        for u, v, data in self.graph.edges(data=True):
            links.append({"source": u, "target": v, "label": data.get("relation", "")})
            
        return {"nodes": nodes, "links": links}
