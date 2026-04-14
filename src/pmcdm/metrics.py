"""Metrics for PMCDM experiments."""

from typing import Any, Dict, List, Optional

import networkx as nx
from sklearn.metrics import normalized_mutual_info_score

from .s_louvain import SLouvain


def partition_to_labels(communities: Dict[Any, int], nodes: List[Any]) -> List[int]:
    return [communities[n] for n in nodes]


def reference_labels_slouvain(layers: List[nx.Graph], random_state: int) -> List[int]:
    """在原始无隐私扰动的多层网络上运行 S-Louvain，作为无真标签数据集的参考社区划分。"""
    communities = SLouvain(random_state=random_state).detect([g.copy() for g in layers])
    nodes = sorted(layers[0].nodes())
    return partition_to_labels(communities, nodes)


def nmi_score(
    pred: List[int],
    *,
    layers: List[nx.Graph],
    gt_labels: Optional[Dict[Any, int]],
    random_state: int,
    slouvain_ref_labels: Optional[List[int]] = None,
) -> float:
    """NMI：若有真实标签则与标签比；否则与 S-Louvain 在原始网络上的划分比（可用缓存避免重复跑 S-Louvain）。"""
    nodes = sorted(layers[0].nodes())
    if gt_labels is not None:
        ref = partition_to_labels(gt_labels, nodes)
    elif slouvain_ref_labels is not None:
        ref = slouvain_ref_labels
    else:
        ref = reference_labels_slouvain(layers, random_state)
    return float(normalized_mutual_info_score(ref, pred))


def communities_to_groups(communities: Dict[int, int]) -> Dict[int, List[int]]:
    groups: Dict[int, List[int]] = {}
    for node, cid in communities.items():
        groups.setdefault(cid, []).append(node)
    return groups


def modularity_density(graph: nx.Graph, communities: Dict[int, int]) -> float:
    groups = communities_to_groups(communities)
    score = 0.0
    for nodes in groups.values():
        node_set = set(nodes)
        nc = len(nodes)
        if nc == 0:
            continue
        kin = 0.0
        kout = 0.0
        for u in nodes:
            for v, attr in graph[u].items():
                w = float(attr.get("weight", 1.0))
                if v in node_set:
                    kin += w
                else:
                    kout += w
        score += (kin - kout) / nc
    return score / max(1, graph.number_of_nodes())


def weighted_modularity_density(
    layer_graphs: List[nx.Graph],
    communities: Dict[int, int],
    lambd: float,
) -> float:
    groups = list(communities_to_groups(communities).values())
    total = 0.0
    for graph in layer_graphs:
        modularity_score = nx.algorithms.community.modularity(graph, groups, weight="weight")
        density_score = modularity_density(graph, communities)
        total += lambd * modularity_score + (1.0 - lambd) * density_score
    return total / max(1, len(layer_graphs))
