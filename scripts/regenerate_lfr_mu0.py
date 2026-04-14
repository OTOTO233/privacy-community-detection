from __future__ import annotations

import csv
import sys
from dataclasses import asdict
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pmcdm import PMCDMExperiment


OUTPUT = ROOT / "output"
ALGORITHMS = ["S-Louvain", "PD-Louvain", "R-Louvain", "DP-Louvain", "K-Louvain", "DH-Louvain"]

# 这组参数保留了用户要求的 N=300、avg_degree=10、max_degree=40、q=3，
# 同时在 mu=0 时能生成完整 300 节点且真实社区数 > 1 的 LFR 基准图。
MU0_VARIANT = {
    "n": 300,
    "tau1": 2.0,
    "tau2": 1.5,
    "mu": 0.0,
    "average_degree": 10,
    "max_degree": 40,
    "min_community": 20,
    "max_community": 50,
    "max_iters": 5000,
    "seed": 11,
    "multiplex_layers": 3,
}


def _ground_truth_from_lfr(graph: nx.Graph) -> dict[int, int]:
    community_to_id: dict[frozenset[int], int] = {}
    ground_truth: dict[int, int] = {}
    for node, data in graph.nodes(data=True):
        community = frozenset(data["community"])
        if community not in community_to_id:
            community_to_id[community] = len(community_to_id)
        ground_truth[node] = community_to_id[community]
    return ground_truth


def _build_valid_mu0_graph() -> tuple[nx.Graph, dict[int, int], str]:
    nx_kwargs = {k: v for k, v in MU0_VARIANT.items() if k != "multiplex_layers"}
    base_graph = nx.generators.community.LFR_benchmark_graph(**nx_kwargs)
    base_graph = nx.Graph(base_graph)
    base_graph.remove_edges_from(nx.selfloop_edges(base_graph))

    ground_truth = _ground_truth_from_lfr(base_graph)
    if base_graph.number_of_nodes() != 300:
        raise RuntimeError("μ=0 重生成失败：节点数不是 300")
    if len(set(ground_truth.values())) <= 1:
        raise RuntimeError("μ=0 重生成失败：真实社区数不大于 1")

    summary = (
        "LFR Custom | 层数 q=3 | 节点="
        f"{base_graph.number_of_nodes()} | 边={base_graph.number_of_edges()} "
        f"| 社区数={len(set(ground_truth.values()))} | mu=0.0 avg_deg=10 maxk=40"
    )
    return base_graph, ground_truth, summary


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _replace_mu0_rows(regenerated_rows: list[dict]) -> None:
    target = OUTPUT / "lfr_experiment_mu_n300_all_complete.csv"
    if not target.exists():
        return

    with target.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    kept = [row for row in rows if float(row["mu"]) != 0.0]
    merged = regenerated_rows + kept
    merged.sort(key=lambda item: (float(item["mu"]), item["algorithm"]))
    _write_csv(target, merged)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    base_graph, ground_truth, summary = _build_valid_mu0_graph()
    print("summary=", summary, flush=True)
    print("connected=", nx.is_connected(base_graph), flush=True)
    print("components=", nx.number_connected_components(base_graph), flush=True)

    layers = PMCDMExperiment.build_multiplex_from_base(
        base_graph,
        layers=MU0_VARIANT["multiplex_layers"],
        seed=MU0_VARIANT["seed"],
    )
    exp = PMCDMExperiment(epsilon=1.0, delta=1e-5, key_size=512, random_state=42)
    results = exp.run_benchmark(layers, ground_truth, lambd=0.5, algorithms=ALGORITHMS)

    rows: list[dict] = []
    for row in results:
        item = asdict(row)
        item["mu"] = 0.0
        item["fixed_lambd"] = 0.5
        item["dataset_summary"] = summary
        rows.append(item)

    out_path = OUTPUT / "lfr_mu0_regenerated_n300.csv"
    _write_csv(out_path, rows)
    _replace_mu0_rows(rows)
    print(out_path)


if __name__ == "__main__":
    main()
