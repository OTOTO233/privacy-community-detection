"""LFR 参数实验。

组 1：固定 N=300, q=3, gamma=2, beta≈1, <k>=10, maxk=40，仅改变 μ。
组 2：固定上述 LFR 参数与 μ=0.25，仅改变 DH-Louvain 的 λ。

说明：
- 文献表中 beta=1，但 NetworkX 的 LFR 生成器要求 tau2 > 1，因此这里取 1.05 作为近似。
- 为了保留“所有算法对比”，μ 组输出全部 6 个算法；λ 组也输出全部 6 个算法，
  但只有 PD-Louvain / DH-Louvain 会随 λ 实际变化，其它算法曲线基本为平线。
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiment_datasets import load_dataset
from src.pmcdm import PMCDMExperiment
from scripts.chart_style import SONGTI_SMALL_FIVE_PT, apply_songti_small5

OUTPUT = ROOT / "output"
ALGORITHMS = ["S-Louvain", "PD-Louvain", "R-Louvain", "DP-Louvain", "K-Louvain", "DH-Louvain"]
MU_VALUES = [round(i * 0.05, 2) for i in range(11)]
LAMBDA_VALUES = [round(i * 0.1, 1) for i in range(11)]
MU_CSV = OUTPUT / "lfr_experiment_mu_n300_all.csv"
LAMBDA_CSV = OUTPUT / "lfr_experiment_lambda_n300_all.csv"


def _variant(mu: float) -> dict[str, Any]:
    return {
        "n": 300,
        "tau1": 2.0,
        "tau2": 1.05,
        "mu": mu,
        "average_degree": 10,
        "max_degree": 40,
        "min_community": 20,
        "max_community": 50,
        "max_iters": 50000,
        "multiplex_layers": 3,
    }


def _load_lfr(mu: float):
    tries = [
        _variant(mu),
        {**_variant(mu), "max_iters": 80000},
        {**_variant(mu), "max_iters": 120000, "seed": 11},
        {**_variant(mu), "max_iters": 120000, "seed": 23},
    ]
    last = None
    for item in tries:
        try:
            return load_dataset("lfr", variant=item)
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise RuntimeError(f"LFR 生成失败: mu={mu}") from last


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _plot(rows: list[dict[str, Any]], x_key: str, y_key: str, filename: str, title: str, xlabel: str, ylabel: str) -> None:
    apply_songti_small5()
    plt.figure(figsize=(10.5, 5.6))
    for algo in ALGORITHMS:
        series = [row for row in rows if row["algorithm"] == algo]
        if not series:
            continue
        plt.plot([row[x_key] for row in series], [row[y_key] for row in series], marker="o", linewidth=2.0, label=algo)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, linestyle="--", alpha=0.35)
    plt.legend(ncol=3, fontsize=SONGTI_SMALL_FIVE_PT)
    plt.tight_layout()
    plt.savefig(OUTPUT / filename, dpi=220, bbox_inches="tight")
    plt.close()


def run_mu_group() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for mu in MU_VALUES:
        print(f"[mu-group] mu={mu}", flush=True)
        dataset = _load_lfr(mu)
        exp = PMCDMExperiment(epsilon=1.0, delta=1e-5, key_size=512, random_state=42)
        results = exp.run_benchmark(dataset.layers, dataset.ground_truth, lambd=0.5, algorithms=ALGORITHMS)
        for row in results:
            item = asdict(row)
            item["mu"] = mu
            item["fixed_lambd"] = 0.5
            item["dataset_summary"] = dataset.summary
            rows.append(item)
        _write_csv(MU_CSV, rows)
    return rows


def run_lambda_group() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    dataset = _load_lfr(0.25)
    for lambd in LAMBDA_VALUES:
        print(f"[lambda-group] lambd={lambd}", flush=True)
        exp = PMCDMExperiment(epsilon=1.0, delta=1e-5, key_size=512, random_state=42)
        results = exp.run_benchmark(dataset.layers, dataset.ground_truth, lambd=lambd, algorithms=ALGORITHMS)
        for row in results:
            item = asdict(row)
            item["lambd"] = lambd
            item["fixed_mu"] = 0.25
            item["dataset_summary"] = dataset.summary
            rows.append(item)
        _write_csv(LAMBDA_CSV, rows)
    return rows


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    mu_rows = run_mu_group()
    lambda_rows = run_lambda_group()

    _write_csv(MU_CSV, mu_rows)
    _write_csv(LAMBDA_CSV, lambda_rows)
    (OUTPUT / "lfr_parameter_study_summary.json").write_text(
        json.dumps(
            {
                "settings": {
                    "N": 300,
                    "q": 3,
                    "gamma_tau1": 2.0,
                    "beta_tau2": 1.05,
                    "average_degree": 10,
                    "max_degree": 40,
                },
                "mu_group": mu_rows,
                "lambda_group": lambda_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    _plot(
        mu_rows,
        "mu",
        "module_density",
        "chart_lfr_mu_group_density.png",
        "LFR Group 1: D vs μ",
        "Mixing Parameter μ",
        "Module Density D",
    )
    _plot(
        mu_rows,
        "mu",
        "modularity",
        "chart_lfr_mu_group_modularity.png",
        "LFR Group 1: Q vs μ",
        "Mixing Parameter μ",
        "Modularity Q",
    )
    _plot(
        mu_rows,
        "mu",
        "nmi",
        "chart_lfr_mu_group_nmi.png",
        "LFR Group 1: NMI vs μ",
        "Mixing Parameter μ",
        "NMI",
    )
    _plot(
        lambda_rows,
        "lambd",
        "module_density",
        "chart_lfr_lambda_group_density.png",
        "LFR Group 2: D vs λ",
        "Lambda λ",
        "Module Density D",
    )
    _plot(
        lambda_rows,
        "lambd",
        "modularity",
        "chart_lfr_lambda_group_modularity.png",
        "LFR Group 2: Q vs λ",
        "Lambda λ",
        "Modularity Q",
    )
    _plot(
        lambda_rows,
        "lambd",
        "nmi",
        "chart_lfr_lambda_group_nmi.png",
        "LFR Group 2: NMI vs λ",
        "Lambda λ",
        "NMI",
    )
    _plot(
        lambda_rows,
        "lambd",
        "privacy_rate",
        "chart_lfr_lambda_group_privacy.png",
        "LFR Group 2: pr vs λ",
        "Lambda λ",
        "Privacy Rate pr",
    )


if __name__ == "__main__":
    main()
