from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT))

from src.experiment_datasets import load_dataset
from src.pmcdm import PMCDMExperiment
from src.pmcdm.metrics import weighted_modularity_density


OUTPUT = ROOT / "output"
ALGORITHMS = ["S-Louvain", "PD-Louvain", "R-Louvain", "DP-Louvain", "K-Louvain", "DH-Louvain"]
MU_VALUES = [round(i * 0.1, 2) for i in range(6)]
MU_TRIAL_SEEDS = [11, 23, 37]
LAMBDA_VALUES = [round(i * 0.1, 1) for i in range(11)]
LAMBDA_SEEDS = [13, 29, 43]


@dataclass
class MuAggregateRow:
    mu: float
    algorithm: str
    modularity: float
    module_density: float
    nmi: float
    privacy_rate: float
    communities: float


@dataclass
class LambdaAggregateRow:
    dataset: str
    lambd: float
    weighted_density: float
    modularity: float
    nmi: float
    communities: float


def _lfr_trial_dataset(mu: float, seed: int) -> tuple[list[nx.Graph], dict[int, int]]:
    candidates = [
        dict(n=80, tau1=2.5, tau2=1.5, mu=mu, average_degree=7, max_degree=16, min_community=10, max_community=24, max_iters=30000),
        dict(n=80, tau1=2.5, tau2=1.5, mu=mu, average_degree=7, max_degree=16, min_community=12, max_community=26, max_iters=40000),
        dict(n=70, tau1=2.5, tau2=1.5, mu=mu, average_degree=6, max_degree=14, min_community=8, max_community=22, max_iters=40000),
    ]
    base_graph = None
    for params in candidates:
        try:
            base_graph = nx.generators.community.LFR_benchmark_graph(seed=seed, **params)
            break
        except nx.ExceededMaxIterations:
            continue
    if base_graph is None:
        raise RuntimeError(f"LFR 生成失败: mu={mu}, seed={seed}")
    base_graph = nx.Graph(base_graph)
    base_graph.remove_edges_from(nx.selfloop_edges(base_graph))
    if not nx.is_connected(base_graph):
        largest_nodes = max(nx.connected_components(base_graph), key=len)
        base_graph = base_graph.subgraph(largest_nodes).copy()

    community_to_id: dict[frozenset[int], int] = {}
    ground_truth: dict[int, int] = {}
    for node, data in base_graph.nodes(data=True):
        community = frozenset(data["community"])
        if community not in community_to_id:
            community_to_id[community] = len(community_to_id)
        ground_truth[node] = community_to_id[community]

    layers = PMCDMExperiment.build_multiplex_from_base(base_graph, layers=3, seed=seed)
    return layers, ground_truth


def run_mu_sweep() -> list[MuAggregateRow]:
    rows: list[MuAggregateRow] = []
    for mu in MU_VALUES:
        print(f"[mu] running mu={mu}")
        by_algo: dict[str, list[dict[str, Any]]] = {algo: [] for algo in ALGORITHMS}
        for seed in MU_TRIAL_SEEDS:
            layers, gt = _lfr_trial_dataset(mu, seed)
            exp = PMCDMExperiment(epsilon=1.0, delta=1e-5, key_size=512, random_state=seed)
            result_rows = exp.run_benchmark(layers, gt, lambd=0.5, algorithms=ALGORITHMS)
            for row in result_rows:
                by_algo[row.algorithm].append(asdict(row))

        for algo in ALGORITHMS:
            group = by_algo[algo]
            rows.append(
                MuAggregateRow(
                    mu=mu,
                    algorithm=algo,
                    modularity=mean(item["modularity"] for item in group),
                    module_density=mean(item["module_density"] for item in group),
                    nmi=mean(item["nmi"] for item in group),
                    privacy_rate=mean(item["privacy_rate"] for item in group),
                    communities=mean(item["communities"] for item in group),
                )
            )
    return rows


def run_lambda_sweep() -> list[LambdaAggregateRow]:
    dataset_specs = [
        ("AUCS", "aucs", None),
        (
            "BioGRID Candida",
            "biogrid",
            {
                "member": "BIOGRID-ORGANISM-Candida_albicans_SC5314-5.0.256.tab3.txt",
                "top_layers": 3,
                "min_edges": 12,
                "max_nodes": 300,
                "include_genetic": True,
                "auto_layers": True,
            },
        ),
        (
            "BioGRID C.elegans",
            "biogrid",
            {
                "member": "BIOGRID-ORGANISM-Caenorhabditis_elegans-5.0.256.tab3.txt",
                "top_layers": 3,
                "min_edges": 12,
                "max_nodes": 300,
                "include_genetic": True,
                "auto_layers": True,
            },
        ),
    ]

    rows: list[LambdaAggregateRow] = []
    for label, dataset_name, variant in dataset_specs:
        print(f"[lambda] dataset={label}")
        bundle = load_dataset(dataset_name, variant=variant)
        for lambd in LAMBDA_VALUES:
            print(f"  lambda={lambd}")
            q_values: list[float] = []
            nmi_values: list[float] = []
            comm_values: list[float] = []
            wd_values: list[float] = []
            for seed in LAMBDA_SEEDS:
                exp = PMCDMExperiment(epsilon=1.0, delta=1e-5, key_size=512, random_state=seed)
                result = exp.run_benchmark(bundle.layers, bundle.ground_truth, lambd=lambd, algorithms=["DH-Louvain"])[0]
                q_values.append(result.modularity)
                nmi_values.append(result.nmi)
                comm_values.append(result.communities)
                from src.pmcdm.architecture import CloudServer1, CloudServer2

                cloud1 = CloudServer1(1.0, 1e-5, 512)
                cloud2 = CloudServer2(cloud1, random_state=seed)
                communities = cloud2.run_dh_louvain(bundle.layers, lambd=lambd)
                wd_values.append(weighted_modularity_density(bundle.layers, communities, lambd))

            rows.append(
                LambdaAggregateRow(
                    dataset=label,
                    lambd=lambd,
                    weighted_density=mean(wd_values),
                    modularity=mean(q_values),
                    nmi=mean(nmi_values),
                    communities=mean(comm_values),
                )
            )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _chart_mu(rows: list[MuAggregateRow], metric: str, ylabel: str, filename: str) -> None:
    plt.figure(figsize=(10.5, 5.6))
    for algo in ALGORITHMS:
        series = [row for row in rows if row.algorithm == algo]
        plt.plot([row.mu for row in series], [getattr(row, metric) for row in series], marker="o", linewidth=2, label=algo)
    plt.xlabel("Mixing Parameter μ")
    plt.ylabel(ylabel)
    plt.title(f"LFR Repeated Trials: {ylabel} vs μ")
    plt.grid(True, linestyle="--", alpha=0.35)
    plt.legend(ncol=3, fontsize=8)
    plt.tight_layout()
    plt.savefig(OUTPUT / filename, dpi=220, bbox_inches="tight")
    plt.close()


def _chart_lambda(rows: list[LambdaAggregateRow], metric: str, ylabel: str, filename: str) -> None:
    plt.figure(figsize=(10.2, 5.4))
    datasets = sorted({row.dataset for row in rows})
    for dataset in datasets:
        series = [row for row in rows if row.dataset == dataset]
        plt.plot([row.lambd for row in series], [getattr(row, metric) for row in series], marker="o", linewidth=2.2, label=dataset)
    plt.xlabel("Lambda λ")
    plt.ylabel(ylabel)
    plt.title(f"Repeated DH-Louvain Runs: {ylabel} vs λ")
    plt.grid(True, linestyle="--", alpha=0.35)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT / filename, dpi=220, bbox_inches="tight")
    plt.close()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    mu_rows = run_mu_sweep()
    lambda_rows = run_lambda_sweep()

    mu_dict_rows = [asdict(row) for row in mu_rows]
    lambda_dict_rows = [asdict(row) for row in lambda_rows]
    _write_csv(OUTPUT / "repeated_mu_sweep_lfr.csv", mu_dict_rows)
    _write_csv(OUTPUT / "repeated_lambda_sweep_real.csv", lambda_dict_rows)
    (OUTPUT / "repeated_mu_lambda_summary.json").write_text(
        json.dumps({"mu_sweep": mu_dict_rows, "lambda_sweep": lambda_dict_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _chart_mu(mu_rows, "module_density", "Module Density D", "chart_lfr_mu_module_density.png")
    _chart_mu(mu_rows, "modularity", "Modularity Q", "chart_lfr_mu_modularity.png")
    _chart_mu(mu_rows, "nmi", "NMI", "chart_lfr_mu_nmi.png")

    _chart_lambda(lambda_rows, "weighted_density", "Weighted Modularity Density", "chart_real_lambda_weighted_density.png")
    _chart_lambda(lambda_rows, "modularity", "Modularity Q", "chart_real_lambda_modularity.png")
    _chart_lambda(lambda_rows, "nmi", "NMI", "chart_real_lambda_nmi.png")
    _chart_lambda(lambda_rows, "communities", "Number of Communities", "chart_real_lambda_communities.png")


if __name__ == "__main__":
    main()
