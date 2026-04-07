"""Benchmark and multiresolution experiment runners."""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import random

import networkx as nx
from sklearn.metrics import normalized_mutual_info_score

from .architecture import CloudServer1, CloudServer2, TerminalClient
from .metrics import communities_to_groups, modularity_density, partition_to_labels, weighted_modularity_density
from .s_louvain import SLouvain


@dataclass
class ExperimentResult:
    algorithm: str
    modularity: float
    module_density: float
    nmi: float
    privacy_rate: float
    communities: int


class PMCDMExperiment:
    """End-to-end PMCDM experiment with Louvain variants."""

    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5, key_size: int = 512, random_state: int = 42):
        self.epsilon = epsilon
        self.delta = delta
        self.key_size = key_size
        self.random_state = random_state

    @staticmethod
    def build_multiplex_from_base(base_graph: nx.Graph, layers: int = 3, seed: int = 42) -> List[nx.Graph]:
        # 对只有单层结构的数据集，复制出多层并在权重上做轻微扰动，模拟多层网络。
        rng = random.Random(seed)
        layer_graphs: List[nx.Graph] = []
        for lid in range(layers):
            g = base_graph.copy()
            for u, v in g.edges():
                g[u][v]["weight"] = 1.0 + (lid * 0.2) + rng.random() * 0.3
            layer_graphs.append(g)
        return layer_graphs

    def _run_variant(
        self,
        name: str,
        original_layers: List[nx.Graph],
        gt_labels: Optional[Dict[int, int]],
        lambd: float,
    ) -> ExperimentResult:
        # 不同算法名其实对应的是“是否加密、是否扰动、用哪种社区检测器”三种组合。
        perturbation_mode = {
            "S-Louvain": "none",
            "PD-Louvain": "none",
            "R-Louvain": "random",
            "DP-Louvain": "dp",
            "K-Louvain": "k-anon",
            "DH-Louvain": "dp",
        }[name]
        use_he = name in {"PD-Louvain", "DH-Louvain"}
        use_dh_framework = name in {"PD-Louvain", "DH-Louvain"}

        cloud1 = CloudServer1(self.epsilon, self.delta, self.key_size)
        terminal = TerminalClient(cloud1.he)

        layer_inputs: List[nx.Graph] = []
        for layer in original_layers:
            # 终端上传阶段可以选择是否对边权做同态加密模拟。
            uploaded = terminal.encrypt_upload(layer) if use_he else layer.copy()
            perturbed = cloud1.perturb_layer(uploaded, mode=perturbation_mode)
            layer_inputs.append(perturbed)

        if use_dh_framework:
            cloud2 = CloudServer2(cloud1, random_state=self.random_state)
            communities = cloud2.run_dh_louvain(layer_inputs, lambd=lambd)
        else:
            communities = SLouvain(random_state=self.random_state).detect(layer_inputs)

        nodes = sorted(original_layers[0].nodes())
        pred = partition_to_labels(communities, nodes)
        # 真实标签不是所有数据集都有，所以 NMI 在真实标签缺失时记为 nan。
        nmi = float("nan")
        if gt_labels is not None:
            gt = partition_to_labels(gt_labels, nodes)
            nmi = normalized_mutual_info_score(gt, pred)

        metric_graph = layer_inputs[0]
        groups = list(communities_to_groups(communities).values())
        modularity = nx.algorithms.community.modularity(metric_graph, groups, weight="weight")
        d_score = modularity_density(metric_graph, communities)

        # pr 是项目里定义的综合隐私率，既考虑边保留情况，也考虑是否使用 HE。
        pe = cloud1.preserved_edges / max(1, cloud1.total_edges)
        pw = 1.0 if use_he else 0.0
        privacy_rate = (pe + pw) / 2.0

        return ExperimentResult(
            algorithm=name,
            modularity=modularity,
            module_density=d_score,
            nmi=nmi,
            privacy_rate=privacy_rate,
            communities=len(set(communities.values())),
        )

    def run_benchmark(
        self,
        original_layers: List[nx.Graph],
        gt_labels: Optional[Dict[int, int]],
        lambd: float = 0.5,
        algorithms: List[str] | None = None,
    ) -> List[ExperimentResult]:
        # 默认一次跑 6 个算法变体，便于中期报告直接做横向对比。
        algo_list = algorithms or [
            "S-Louvain",
            "PD-Louvain",
            "R-Louvain",
            "DP-Louvain",
            "K-Louvain",
            "DH-Louvain",
        ]
        return [self._run_variant(algo, original_layers, gt_labels, lambd=lambd) for algo in algo_list]

    def run_multiresolution(
        self,
        original_layers: List[nx.Graph],
        lambdas: List[float],
    ) -> List[Tuple[float, float, int]]:
        cloud1 = CloudServer1(self.epsilon, self.delta, self.key_size)
        cloud2 = CloudServer2(cloud1, random_state=self.random_state)
        out: List[Tuple[float, float, int]] = []
        for lambd in lambdas:
            communities = cloud2.run_dh_louvain(original_layers, lambd=lambd)
            score = weighted_modularity_density(original_layers, communities, lambd=lambd)
            out.append((lambd, score, len(set(communities.values()))))
        return out
