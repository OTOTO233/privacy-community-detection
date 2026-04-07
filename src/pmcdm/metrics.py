"""Metrics for PMCDM experiments."""

from typing import Dict, List

import networkx as nx


def partition_to_labels(communities: Dict[int, int], nodes: List[int]) -> List[int]:
    return [communities[n] for n in nodes]


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
