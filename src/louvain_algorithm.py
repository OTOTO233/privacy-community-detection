"""
莱顿（Louvain）社区检测算法实现
基于模块度优化的贪心算法
"""

import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Set
from collections import defaultdict


class LouvainDetector:
    """莱顿社区检测算法实现"""

    def __init__(self, random_state: int = 42):
        """
        初始化莱顿检测器

        Args:
            random_state: 随机种子
        """
        self.random_state = random_state
        self.graph = None
        self.communities = {}

    def detect(self, graph: nx.Graph) -> Dict[int, int]:
        """
        执行社区检测

        Args:
            graph: NetworkX 图对象

        Returns:
            节点到社区编号的映射字典
        """
        self.graph = graph
        np.random.seed(self.random_state)

        # 初始化：每个节点为一个社区
        communities = {node: node for node in graph.nodes()}
        modularity_history = []

        improved = True
        iteration = 0

        while improved and iteration < 100:
            iteration += 1
            improved = False
            new_communities = communities.copy()

            # 随机遍历节点
            nodes = list(graph.nodes())
            np.random.shuffle(nodes)

            for node in nodes:
                # 获取邻居社区及其权重
                neighbor_communities = self._get_neighbor_communities(
                    node, new_communities, graph
                )

                # 找到使模块度增加最多的社区
                best_community = new_communities[node]
                best_gain = 0

                for community in neighbor_communities:
                    gain = self._calculate_modularity_gain(
                        node, community, new_communities, graph
                    )
                    if gain > best_gain:
                        best_gain = gain
                        best_community = community

                # 更新节点所属社区
                if best_community != new_communities[node]:
                    new_communities[node] = best_community
                    improved = True

            communities = new_communities

            # 计算模块度
            modularity = self._calculate_modularity(communities, graph)
            modularity_history.append(modularity)

            # 合并社区（第二阶段）
            communities = self._merge_communities(communities, graph)

        self.communities = communities
        return communities

    def _get_neighbor_communities(
            self,
            node: int,
            communities: Dict[int, int],
            graph: nx.Graph
    ) -> Set[int]:
        """获取节点邻居所在的社区集合"""
        neighbor_communities = set()
        neighbor_communities.add(communities[node])

        for neighbor in graph.neighbors(node):
            neighbor_communities.add(communities[neighbor])

        return neighbor_communities

    def _calculate_modularity_gain(
            self,
            node: int,
            community: int,
            communities: Dict[int, int],
            graph: nx.Graph
    ) -> float:
        """计算节点移动到新社区的模块度增益"""
        # 计算节点度数
        node_degree = graph.degree(node)

        # 计算社区内的边权重
        edges_to_community = 0
        for neighbor in graph.neighbors(node):
            if communities[neighbor] == community:
                edge_weight = graph[node][neighbor].get('weight', 1)
                edges_to_community += edge_weight

        # 简化的模块度增益计算
        gain = edges_to_community

        return gain

    def _calculate_modularity(
            self,
            communities: Dict[int, int],
            graph: nx.Graph
    ) -> float:
        """计算图的模块度"""
        modularity = 0
        m = graph.number_of_edges()

        if m == 0:
            return 0

        # 按社区分组节点
        community_nodes = defaultdict(list)
        for node, comm in communities.items():
            community_nodes[comm].append(node)

        # 计算每个社区的贡献
        for community_id, nodes in community_nodes.items():
            # 社区内的边数
            subgraph = graph.subgraph(nodes)
            edges_in_community = subgraph.number_of_edges()

            # 社区的总度数
            total_degree = sum(graph.degree(node) for node in nodes)

            # 模块度公式
            modularity += (edges_in_community / m) - (total_degree / (2 * m)) ** 2

        return modularity

    def _merge_communities(
            self,
            communities: Dict[int, int],
            graph: nx.Graph
    ) -> Dict[int, int]:
        """将相同社区的节点进行重新标记"""
        unique_communities = {}
        mapping = {}

        for node, comm in communities.items():
            if comm not in mapping:
                mapping[comm] = len(mapping)
            unique_communities[node] = mapping[comm]

        return unique_communities

    def get_communities_dict(self) -> Dict[int, List[int]]:
        """获取社区字典（社区ID -> 节点列表）"""
        communities_dict = defaultdict(list)
        for node, comm in self.communities.items():
            communities_dict[comm].append(node)
        return dict(communities_dict)

    def get_statistics(self) -> Dict:
        """获取社区检测统计信息"""
        if not self.communities:
            return {}

        communities_dict = self.get_communities_dict()
        num_communities = len(communities_dict)
        modularity = self._calculate_modularity(self.communities, self.graph)

        community_sizes = [len(nodes) for nodes in communities_dict.values()]

        return {
            'num_communities': num_communities,
            'modularity': modularity,
            'avg_community_size': np.mean(community_sizes),
            'max_community_size': max(community_sizes),
            'min_community_size': min(community_sizes),
            'communities': communities_dict,
        }