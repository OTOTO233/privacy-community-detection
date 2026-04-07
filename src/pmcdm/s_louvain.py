"""Baseline S-Louvain detector on an aggregated multiplex graph."""

from typing import Dict, List

import networkx as nx


class SLouvain:
    """Run standard Louvain on the weighted sum of all layers."""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.communities: Dict[int, int] = {}

    def detect(self, layer_graphs: List[nx.Graph]) -> Dict[int, int]:
        aggregate = self._aggregate_layers(layer_graphs)
        groups = nx.algorithms.community.louvain_communities(
            aggregate,
            weight="weight",
            seed=self.random_state,
        )

        communities: Dict[int, int] = {}
        for cid, nodes in enumerate(groups):
            for node in nodes:
                communities[node] = cid

        self.communities = communities
        return communities

    @staticmethod
    def _aggregate_layers(layer_graphs: List[nx.Graph]) -> nx.Graph:
        aggregate = nx.Graph()
        if not layer_graphs:
            return aggregate

        aggregate.add_nodes_from(layer_graphs[0].nodes(data=True))
        for graph in layer_graphs:
            for u, v, data in graph.edges(data=True):
                weight = float(data.get("weight", 1.0))
                if aggregate.has_edge(u, v):
                    aggregate[u][v]["weight"] += weight
                else:
                    aggregate.add_edge(u, v, weight=weight)
        return aggregate
