"""DH-Louvain algorithm for multiplex networks."""

from typing import Dict, List
import random

import networkx as nx

from .metrics import communities_to_groups, weighted_modularity_density
from .s_louvain import SLouvain


class DHLouvain:
    """Two-phase greedy DH-Louvain on multiplex graphs."""

    def __init__(self, random_state: int = 42, max_iter: int = 20):
        self.random_state = random_state
        self.max_iter = max_iter
        self.communities: Dict[int, int] = {}

    def detect(self, layer_graphs: List[nx.Graph], lambd: float = 0.5) -> Dict[int, int]:
        rng = random.Random(self.random_state)
        nodes = list(layer_graphs[0].nodes())
        communities = SLouvain(random_state=self.random_state).detect(layer_graphs)
        if not communities:
            communities = {n: i for i, n in enumerate(nodes)}
        current_score = weighted_modularity_density(layer_graphs, communities, lambd)

        improved = True
        outer = 0
        while improved and outer < self.max_iter:
            outer += 1
            improved = False

            node_changed = True
            inner = 0
            while node_changed and inner < self.max_iter * 4:
                inner += 1
                node_changed = False
                iter_nodes = nodes[:]
                rng.shuffle(iter_nodes)
                for node in iter_nodes:
                    current = communities[node]
                    candidate_cids = {communities[nb] for g in layer_graphs for nb in g.neighbors(node)}
                    candidate_cids.add(current)
                    best_gain = 0.0
                    best_cid = current
                    for cid in candidate_cids:
                        if cid == current:
                            continue
                        trial = communities.copy()
                        trial[node] = cid
                        trial = self._reindex(trial)
                        gain = weighted_modularity_density(layer_graphs, trial, lambd) - current_score
                        if gain > best_gain:
                            best_gain = gain
                            best_cid = cid
                    if best_cid != current:
                        communities[node] = best_cid
                        communities = self._reindex(communities)
                        current_score += best_gain
                        node_changed = True
                        improved = True

            groups = list(communities_to_groups(communities).keys())
            best_merge_gain = 0.0
            best_merge = None
            for i in range(len(groups)):
                for j in range(i + 1, len(groups)):
                    ci = groups[i]
                    cj = groups[j]
                    trial = communities.copy()
                    for node, cid in communities.items():
                        if cid == cj:
                            trial[node] = ci
                    trial = self._reindex(trial)
                    gain = weighted_modularity_density(layer_graphs, trial, lambd) - current_score
                    if gain > best_merge_gain:
                        best_merge_gain = gain
                        best_merge = trial

            if best_merge is not None:
                communities = best_merge
                current_score += best_merge_gain
                improved = True

        self.communities = communities
        return communities

    @staticmethod
    def _reindex(communities: Dict[int, int]) -> Dict[int, int]:
        mapping: Dict[int, int] = {}
        new_map: Dict[int, int] = {}
        for node, cid in communities.items():
            if cid not in mapping:
                mapping[cid] = len(mapping)
            new_map[node] = mapping[cid]
        return new_map
