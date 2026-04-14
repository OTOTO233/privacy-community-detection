from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
import sys
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pmcdm import PMCDMExperiment


OUTPUT = ROOT / "output"
ALGORITHMS = ["S-Louvain", "PD-Louvain", "R-Louvain", "DP-Louvain", "K-Louvain", "DH-Louvain"]
LAMBDA_ALGORITHMS = ["DH-Louvain"]
MU_VALUES = [round(i * 0.05, 2) for i in range(11)]
LAMBDA_VALUES = [round(i * 0.1, 1) for i in range(11)]
TRIAL_SEEDS = [11, 17, 23, 29, 31, 37, 41, 43, 47, 53]


@dataclass
class TrialRow:
    group: str
    control_value: float
    trial_seed: int
    algorithm: str
    modularity: float
    module_density: float
    nmi: float
    privacy_rate: float
    communities: int


@dataclass
class AggregateRow:
    group: str
    control_value: float
    algorithm: str
    trials: int
    mean_modularity: float
    best_modularity: float
    mean_module_density: float
    best_module_density: float
    mean_nmi: float
    best_nmi: float
    mean_privacy_rate: float
    best_privacy_rate: float
    mean_communities: float
    best_communities: int


def _lfr_params(mu: float, seed: int) -> list[dict[str, Any]]:
    base = {
        "n": 300,
        "tau1": 2.0,
        "tau2": 1.5,
        "mu": mu,
        "average_degree": 10,
        "max_degree": 40,
        "min_community": 20,
        "max_community": 50,
        "seed": seed,
    }
    return [
        {**base, "max_iters": 5000},
        {**base, "max_iters": 10000},
        {**base, "max_iters": 20000},
    ]


def _build_lfr_bundle(mu: float, seed: int) -> tuple[list[nx.Graph], dict[int, int], str]:
    base_graph = None
    last_error: Exception | None = None
    for params in _lfr_params(mu, seed):
        try:
            graph = nx.generators.community.LFR_benchmark_graph(**params)
            base_graph = nx.Graph(graph)
            base_graph.remove_edges_from(nx.selfloop_edges(base_graph))
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if base_graph is None:
        raise RuntimeError(f"LFR 生成失败: mu={mu}, seed={seed}") from last_error

    community_to_id: dict[frozenset[int], int] = {}
    ground_truth: dict[int, int] = {}
    for node, data in base_graph.nodes(data=True):
        community = frozenset(data["community"])
        if community not in community_to_id:
            community_to_id[community] = len(community_to_id)
        ground_truth[node] = community_to_id[community]

    layers = PMCDMExperiment.build_multiplex_from_base(base_graph, layers=3, seed=seed)
    summary = (
        f"LFR Repeat N300 | 节点={base_graph.number_of_nodes()} | 边={base_graph.number_of_edges()} "
        f"| 社区数={len(set(ground_truth.values()))} | mu={mu} | seed={seed}"
    )
    return layers, ground_truth, summary


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _aggregate(rows: list[TrialRow], group: str) -> list[AggregateRow]:
    grouped: dict[tuple[float, str], list[TrialRow]] = {}
    for row in rows:
        key = (row.control_value, row.algorithm)
        grouped.setdefault(key, []).append(row)

    output: list[AggregateRow] = []
    for (control_value, algorithm), items in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1])):
        output.append(
            AggregateRow(
                group=group,
                control_value=control_value,
                algorithm=algorithm,
                trials=len(items),
                mean_modularity=mean(item.modularity for item in items),
                best_modularity=max(item.modularity for item in items),
                mean_module_density=mean(item.module_density for item in items),
                best_module_density=max(item.module_density for item in items),
                mean_nmi=mean(item.nmi for item in items),
                best_nmi=max(item.nmi for item in items),
                mean_privacy_rate=mean(item.privacy_rate for item in items),
                best_privacy_rate=max(item.privacy_rate for item in items),
                mean_communities=mean(item.communities for item in items),
                best_communities=max(item.communities for item in items),
            )
        )
    return output


def _plot(aggregate_rows: list[AggregateRow], x_values: list[float], x_key: str, y_attr: str, filename: str, title: str, xlabel: str, ylabel: str) -> None:
    plt.figure(figsize=(10.5, 5.6))
    algo_list = ALGORITHMS if aggregate_rows and aggregate_rows[0].group == "mu" else LAMBDA_ALGORITHMS
    for algo in algo_list:
        series = [row for row in aggregate_rows if row.algorithm == algo]
        series.sort(key=lambda item: item.control_value)
        if not series:
            continue
        plt.plot(
            [row.control_value for row in series],
            [getattr(row, y_attr) for row in series],
            marker="o",
            linewidth=2.0,
            label=algo,
        )
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(x_values)
    plt.grid(True, linestyle="--", alpha=0.35)
    plt.legend(ncol=3, fontsize=8)
    plt.tight_layout()
    plt.savefig(OUTPUT / filename, dpi=220, bbox_inches="tight")
    plt.close()


def run_mu_group() -> tuple[list[TrialRow], list[AggregateRow]]:
    trial_rows: list[TrialRow] = []
    for mu in MU_VALUES:
        print(f"[repeat-mu] mu={mu}", flush=True)
        for seed in TRIAL_SEEDS:
            layers, ground_truth, summary = _build_lfr_bundle(mu, seed)
            print(f"  seed={seed} | {summary}", flush=True)
            exp = PMCDMExperiment(epsilon=1.0, delta=1e-5, key_size=512, random_state=seed)
            results = exp.run_benchmark(layers, ground_truth, lambd=0.5, algorithms=ALGORITHMS)
            for row in results:
                trial_rows.append(
                    TrialRow(
                        group="mu",
                        control_value=mu,
                        trial_seed=seed,
                        algorithm=row.algorithm,
                        modularity=row.modularity,
                        module_density=row.module_density,
                        nmi=row.nmi,
                        privacy_rate=row.privacy_rate,
                        communities=row.communities,
                    )
                )
    return trial_rows, _aggregate(trial_rows, "mu")


def run_lambda_group() -> tuple[list[TrialRow], list[AggregateRow]]:
    trial_rows: list[TrialRow] = []
    cached_bundles = {seed: _build_lfr_bundle(0.25, seed) for seed in TRIAL_SEEDS}
    for lambd in LAMBDA_VALUES:
        print(f"[repeat-lambda] lambda={lambd}", flush=True)
        for seed in TRIAL_SEEDS:
            layers, ground_truth, summary = cached_bundles[seed]
            print(f"  seed={seed} | {summary}", flush=True)
            exp = PMCDMExperiment(epsilon=1.0, delta=1e-5, key_size=512, random_state=seed)
            results = exp.run_benchmark(layers, ground_truth, lambd=lambd, algorithms=LAMBDA_ALGORITHMS)
            for row in results:
                trial_rows.append(
                    TrialRow(
                        group="lambda",
                        control_value=lambd,
                        trial_seed=seed,
                        algorithm=row.algorithm,
                        modularity=row.modularity,
                        module_density=row.module_density,
                        nmi=row.nmi,
                        privacy_rate=row.privacy_rate,
                        communities=row.communities,
                    )
                )
    return trial_rows, _aggregate(trial_rows, "lambda")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    mu_trials, mu_agg = run_mu_group()
    lambda_trials, lambda_agg = run_lambda_group()

    _write_csv(OUTPUT / "repeated_lfr_mu_n300_trials.csv", [asdict(row) for row in mu_trials])
    _write_csv(OUTPUT / "repeated_lfr_mu_n300_mean_best.csv", [asdict(row) for row in mu_agg])
    _write_csv(OUTPUT / "repeated_lfr_lambda_n300_trials.csv", [asdict(row) for row in lambda_trials])
    _write_csv(OUTPUT / "repeated_lfr_lambda_n300_mean_best.csv", [asdict(row) for row in lambda_agg])

    _plot(
        mu_agg,
        MU_VALUES,
        "mu",
        "mean_modularity",
        "chart_repeated_lfr_mu_mean_modularity_n300.png",
        "Repeated LFR N=300: Mean Q vs μ",
        "Mixing Parameter μ",
        "Mean Modularity Q",
    )
    _plot(
        mu_agg,
        MU_VALUES,
        "mu",
        "mean_module_density",
        "chart_repeated_lfr_mu_mean_density_n300.png",
        "Repeated LFR N=300: Mean D vs μ",
        "Mixing Parameter μ",
        "Mean Module Density D",
    )
    _plot(
        mu_agg,
        MU_VALUES,
        "mu",
        "mean_nmi",
        "chart_repeated_lfr_mu_mean_nmi_n300.png",
        "Repeated LFR N=300: Mean NMI vs μ",
        "Mixing Parameter μ",
        "Mean NMI",
    )
    _plot(
        lambda_agg,
        LAMBDA_VALUES,
        "lambda",
        "mean_modularity",
        "chart_repeated_lfr_lambda_mean_modularity_n300.png",
        "Repeated LFR N=300: Mean Q vs λ",
        "Lambda λ",
        "Mean Modularity Q",
    )
    _plot(
        lambda_agg,
        LAMBDA_VALUES,
        "lambda",
        "mean_nmi",
        "chart_repeated_lfr_lambda_mean_nmi_n300.png",
        "Repeated LFR N=300: Mean NMI vs λ",
        "Lambda λ",
        "Mean NMI",
    )
    _plot(
        lambda_agg,
        LAMBDA_VALUES,
        "lambda",
        "mean_privacy_rate",
        "chart_repeated_lfr_lambda_mean_privacy_n300.png",
        "Repeated LFR N=300: Mean pr vs λ",
        "Lambda λ",
        "Mean Privacy Rate pr",
    )


if __name__ == "__main__":
    main()
