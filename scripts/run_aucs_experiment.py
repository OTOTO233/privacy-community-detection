"""Run the benchmark table on the processed AUCS dataset only."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiment_datasets import load_aucs_dataset
from src.pmcdm import PMCDMExperiment


def _fmt(value: float) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.4f}"


def main() -> None:
    dataset = load_aucs_dataset()
    experiment = PMCDMExperiment(
        epsilon=1.0,
        delta=1e-5,
        key_size=512,
        random_state=42,
    )
    rows = experiment.run_benchmark(dataset.layers, dataset.ground_truth, lambd=0.5)

    print(dataset.summary)
    print("-" * 95)
    print(f"{'算法':<12}{'Q(模块度)':<14}{'D(模块密度)':<16}{'NMI':<12}{'pr(隐私率)':<14}{'社区数':<10}")
    print("-" * 95)
    for row in rows:
        print(
            f"{row.algorithm:<12}"
            f"{_fmt(row.modularity):<14}"
            f"{_fmt(row.module_density):<16}"
            f"{_fmt(row.nmi):<12}"
            f"{_fmt(row.privacy_rate):<14}"
            f"{row.communities:<10d}"
        )


if __name__ == "__main__":
    main()
