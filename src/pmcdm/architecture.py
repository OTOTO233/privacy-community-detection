"""Terminal-Cloud1-Cloud2 architecture simulation."""

from typing import Dict, List, Literal, Tuple
import random

import networkx as nx
import numpy as np

from ..differential_privacy import DifferentialPrivacy
from ..homomorphic_encryption import HomomorphicEncryption
from .dh_louvain import DHLouvain
from .metrics import communities_to_groups


class TerminalClient:
    """Terminal-side encryption and upload simulation."""

    def __init__(self, he: HomomorphicEncryption):
        self.he = he

    def encrypt_upload(self, graph: nx.Graph) -> nx.Graph:
        # 这里不改变图结构，只是在边属性里附加一个 enc_weight 字段来模拟密文上传。
        g = graph.copy()
        for _, _, data in g.edges(data=True):
            w = float(data.get("weight", 1.0))
            data["enc_weight"] = self.he.encrypt(w)
        return g


class CloudServer1:
    """Data servers: DP topology perturbation + HE stats."""

    def __init__(self, epsilon: float, delta: float, key_size: int, spurious_rate: float = 0.1):
        self.dp = DifferentialPrivacy(epsilon=epsilon, delta=delta)
        self.he = HomomorphicEncryption(key_size=key_size)
        self.spurious_rate = spurious_rate
        self.preserved_edges = 0.0
        self.total_edges = 0

    def perturb_layer(
        self,
        graph: nx.Graph,
        mode: Literal["none", "random", "dp", "k-anon"] = "none",
        k: int = 3,
    ) -> nx.Graph:
        # Cloud1 的职责是“拿到原始层图后，按指定隐私模式做结构扰动”。
        g = graph.copy()
        original_edges = set(tuple(sorted(e)) for e in g.edges())
        self.total_edges += len(original_edges)

        if mode == "none":
            self.preserved_edges += len(original_edges)
            return g

        if mode == "random":
            g = self._add_random_edges(g)
        elif mode == "dp":
            g = self._privatize_topology_with_dp(g)
        elif mode == "k-anon":
            g = self._k_anonymous_edge_perturbation(g, k=k)
        else:
            raise ValueError(f"Unsupported perturbation mode: {mode}")

        perturbed_edges = set(tuple(sorted(e)) for e in g.edges())
        self.preserved_edges += len(original_edges & perturbed_edges)
        return g

    def _add_random_edges(self, graph: nx.Graph) -> nx.Graph:
        # random 模式只额外加伪边，不删除原有边，属于最简单的扰动基线。
        g = graph.copy()
        edges = set(tuple(sorted(e)) for e in g.edges())
        nodes = list(g.nodes())
        target_spurious = max(1, int(self.spurious_rate * len(edges)))
        attempts = 0
        added = 0
        max_attempts = len(nodes) * len(nodes)
        while added < target_spurious and attempts < max_attempts:
            attempts += 1
            u, v = random.sample(nodes, 2)
            pair = tuple(sorted((u, v)))
            if pair not in edges:
                g.add_edge(u, v, weight=1.0)
                edges.add(pair)
                added += 1
        return g

    def _privatize_topology_with_dp(self, graph: nx.Graph) -> nx.Graph:
        # dp 模式会把真实边和采样出的非边放在一起，用带噪分数重新筛选。
        nodes = list(graph.nodes())
        g = nx.Graph()
        g.add_nodes_from(graph.nodes(data=True))
        rng = random.Random(42)

        original_edges = [tuple(sorted((u, v))) for u, v in graph.edges()]
        original_edge_set = set(original_edges)
        all_pairs = [
            (nodes[i], nodes[j])
            for i in range(len(nodes))
            for j in range(i + 1, len(nodes))
        ]
        non_edges = [pair for pair in all_pairs if pair not in original_edge_set]
        sampled_non_edges = rng.sample(
            non_edges,
            k=min(len(non_edges), max(1, int(self.spurious_rate * len(original_edges)))),
        )

        candidate_pairs = []
        for u, v in original_edges:
            noisy_score = float(self.dp.laplace_mechanism(np.array([1.0]), sensitivity=1.0)[0])
            candidate_pairs.append((noisy_score, u, v, True))
        for u, v in sampled_non_edges:
            noisy_score = float(self.dp.laplace_mechanism(np.array([0.0]), sensitivity=1.0)[0])
            candidate_pairs.append((noisy_score, u, v, False))

        target_edges = len(original_edges)
        candidate_pairs.sort(reverse=True, key=lambda item: item[0])
        for _, u, v, existed in candidate_pairs[:target_edges]:
            weight = graph[u][v].get("weight", 1.0) if existed else 1.0
            g.add_edge(u, v, weight=float(weight))
        return g

    def _k_anonymous_edge_perturbation(self, graph: nx.Graph, k: int) -> nx.Graph:
        # k-anon 模式通过补边把低度节点的度尽量抬高到目标水平。
        g = graph.copy()
        if k <= 1:
            return g

        nodes = list(g.nodes())
        rng = random.Random(42)
        target_degree = max(k, int(sum(dict(g.degree()).values()) / max(1, len(nodes))))

        for node in nodes:
            while g.degree(node) < target_degree:
                candidates = [other for other in nodes if other != node and not g.has_edge(node, other)]
                if not candidates:
                    break
                other = rng.choice(candidates)
                g.add_edge(node, other, weight=1.0)

        return g

    def encrypted_comm_stats(
        self,
        layer_graphs: List[nx.Graph],
        communities: Dict[int, int],
    ) -> List[Tuple[object, object, object]]:
        # 这个函数输出的是“社区内部/外部连接强度”的加密统计预览。
        groups = communities_to_groups(communities)
        stats: List[Tuple[object, object, object]] = []
        for graph in layer_graphs:
            for nodes in groups.values():
                node_set = set(nodes)
                kin = 0.0
                kout = 0.0
                for u in nodes:
                    for v, attr in graph[u].items():
                        w = float(attr.get("weight", 1.0))
                        if v in node_set:
                            kin += w
                        else:
                            kout += w
                stats.append(
                    (
                        self.he.encrypt(kin),
                        self.he.encrypt(kout),
                        self.he.encrypt(float(len(nodes))),
                    )
                )
        return stats


class CloudServer2:
    """Trusted server decrypts and optimizes objective."""

    def __init__(self, cloud1: CloudServer1, random_state: int = 42):
        self.cloud1 = cloud1
        self.detector = DHLouvain(random_state=random_state)

    def run_dh_louvain(self, layer_graphs: List[nx.Graph], lambd: float) -> Dict[int, int]:
        # Cloud2 被视为可信端，真正执行 DH-Louvain 优化。
        return self.detector.detect(layer_graphs, lambd=lambd)

    def decrypt_stats_preview(
        self,
        encrypted_stats: List[Tuple[object, object, object]],
        limit: int = 5,
    ) -> List[Tuple[float, float, float]]:
        preview: List[Tuple[float, float, float]] = []
        for kin, kout, nc in encrypted_stats[:limit]:
            preview.append(
                (
                    self.cloud1.he.decrypt(kin),
                    self.cloud1.he.decrypt(kout),
                    self.cloud1.he.decrypt(nc),
                )
            )
        return preview
