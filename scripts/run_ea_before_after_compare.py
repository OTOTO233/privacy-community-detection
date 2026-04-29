from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.chart_style import apply_songti_small5
from src import EvolutionaryOptimizer, EvolutionaryOptimizerConfig


OUTPUT = ROOT / "output"
SEEDS = [11, 17, 23, 29, 31, 37, 41, 43, 47, 53]
LABEL_Q = r"$Q$"
LABEL_D = r"$D$"
LABEL_NMI = r"$NMI$"
LABEL_PR = r"$p_r$"


@dataclass
class CompareRow:
    scheme: str
    trial_seed: int
    epsilon: float
    lambd: float
    fitness: float
    modularity: float
    module_density: float
    nmi: float
    privacy_rate: float
    communities: int
    runtime_seconds: float


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _load_best_params() -> tuple[float, float]:
    candidates = sorted(OUTPUT.glob("ea_optimize_*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError("未找到进化算法优化结果 JSON")
    payload = json.loads(candidates[0].read_text(encoding="utf-8"))
    best = payload["best"]["params"]
    return float(best["epsilon"]), float(best["lambd"])


def _evaluate(scheme: str, epsilon: float, lambd: float, seed: int) -> CompareRow:
    config = EvolutionaryOptimizerConfig(
        dataset_name="karate",
        algorithm="DH-Louvain",
        population_size=12,
        generations=1,
        random_state=seed,
    )
    optimizer = EvolutionaryOptimizer(config)
    evaluated = optimizer._evaluate_candidate({"epsilon": epsilon, "lambd": lambd})
    return CompareRow(
        scheme=scheme,
        trial_seed=seed,
        epsilon=epsilon,
        lambd=lambd,
        fitness=evaluated.fitness,
        modularity=evaluated.modularity,
        module_density=evaluated.module_density,
        nmi=0.0 if evaluated.nmi is None else evaluated.nmi,
        privacy_rate=evaluated.privacy_rate,
        communities=evaluated.communities,
        runtime_seconds=evaluated.runtime_seconds,
    )


def _plot(summary: list[dict[str, float]]) -> None:
    metrics = ["fitness", "modularity", "module_density", "nmi", "privacy_rate"]
    baseline = [item for item in summary if item["scheme"] == "基线参数"][0]
    optimized = [item for item in summary if item["scheme"] == "进化优化参数"][0]

    apply_songti_small5()
    plt.figure(figsize=(9.2, 5.2))
    xs = range(len(metrics))
    width = 0.36
    plt.bar([x - width / 2 for x in xs], [baseline[f"mean_{m}"] for m in metrics], width=width, label="基线参数")
    plt.bar([x + width / 2 for x in xs], [optimized[f"mean_{m}"] for m in metrics], width=width, label="进化优化参数")
    plt.xticks(list(xs), ["适应度", f"模块度 {LABEL_Q}", f"模块密度 {LABEL_D}", LABEL_NMI, f"隐私率 {LABEL_PR}"])
    plt.ylabel("平均值")
    plt.title("进化算法优化前后平均指标对比")
    plt.grid(True, axis="y", linestyle="--", alpha=0.35)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT / "chart_ea_before_after_compare.png", dpi=220, bbox_inches="tight")
    plt.close()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    best_epsilon, best_lambd = _load_best_params()

    rows: list[CompareRow] = []
    for seed in SEEDS:
        rows.append(_evaluate("基线参数", 1.0, 0.5, seed))
        rows.append(_evaluate("进化优化参数", best_epsilon, best_lambd, seed))

    detail_rows = [asdict(row) for row in rows]
    _write_csv(OUTPUT / "ea_before_after_trials.csv", detail_rows)

    summary: list[dict[str, float]] = []
    for scheme in ["基线参数", "进化优化参数"]:
        group = [row for row in rows if row.scheme == scheme]
        summary.append(
            {
                "scheme": scheme,
                "trials": len(group),
                "epsilon": group[0].epsilon,
                "lambd": group[0].lambd,
                "mean_fitness": mean(row.fitness for row in group),
                "best_fitness": max(row.fitness for row in group),
                "mean_modularity": mean(row.modularity for row in group),
                "best_modularity": max(row.modularity for row in group),
                "mean_module_density": mean(row.module_density for row in group),
                "best_module_density": max(row.module_density for row in group),
                "mean_nmi": mean(row.nmi for row in group),
                "best_nmi": max(row.nmi for row in group),
                "mean_privacy_rate": mean(row.privacy_rate for row in group),
                "best_privacy_rate": max(row.privacy_rate for row in group),
                "mean_communities": mean(row.communities for row in group),
                "best_communities": max(row.communities for row in group),
                "mean_runtime_seconds": mean(row.runtime_seconds for row in group),
            }
        )

    _write_csv(OUTPUT / "ea_before_after_summary.csv", summary)
    _plot(summary)


if __name__ == "__main__":
    main()
