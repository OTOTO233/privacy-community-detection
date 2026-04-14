"""Run the first-version evolutionary parameter optimizer on AUCS."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import json

from src import EvolutionaryOptimizer, EvolutionaryOptimizerConfig, format_history
from src.evolutionary_optimizer import serialize_evolution_result


def _fmt(value: float | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.4f}"


def main() -> None:
    config = EvolutionaryOptimizerConfig(
        dataset_name="aucs",
        algorithm="DH-Louvain",
        population_size=12,
        generations=8,
        random_state=42,
    )
    optimizer = EvolutionaryOptimizer(config)
    result = optimizer.optimize()
    baseline = optimizer._evaluate_candidate({"epsilon": 1.0, "lambd": 0.5})
    out_dir = ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    dump_path = out_dir / "ea_optimize_cli_latest.json"
    payload = serialize_evolution_result(result, baseline=baseline)
    dump_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入: {dump_path}")

    best = result.best
    print(result.dataset_summary)
    print(f"算法: {result.algorithm}")
    print(f"总评估次数: {result.evaluations}")
    print("-" * 95)
    print("最优参数:")
    for key, value in best.params.items():
        print(f"  {key}: {value}")
    print("-" * 95)
    print(
        f"fitness={best.fitness:.4f} | "
        f"Q={_fmt(best.modularity)} | "
        f"D={_fmt(best.module_density)} | "
        f"NMI={_fmt(best.nmi)} | "
        f"pr={_fmt(best.privacy_rate)} | "
        f"社区数={best.communities} | "
        f"运行时间={best.runtime_seconds:.4f}s"
    )
    print("-" * 95)
    print(format_history(result.history))


if __name__ == "__main__":
    main()
