from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
MU_CSV = OUTPUT / "lfr_experiment_mu_n300_all_complete.csv"
LAMBDA_CSV = OUTPUT / "lfr_experiment_lambda_n300_all_complete.csv"


ALGORITHMS = ["S-Louvain", "PD-Louvain", "R-Louvain", "DP-Louvain", "K-Louvain", "DH-Louvain"]

KARATE = {
    "Q": [0.4245, 0.4254, 0.3701, 0.3909, 0.3060, 0.3611],
    "NMI": [0.4900, 0.5878, 0.5869, 0.5005, 0.4400, 0.6877],
    "pr": [0.5000, 1.0000, 0.5000, 0.4594, 0.5000, 0.9594],
}

AUCS = {
    "Q": [0.7392, 0.7392, 0.6597, 0.6814, 0.1385, 0.6440],
    "D": [0.0542, 0.0542, 0.0522, 0.0487, -0.1137, 0.0430],
    "NMI": [0.7827, 0.7827, 0.7551, 0.7653, 0.7678, 0.6712],
    "pr": [0.5000, 1.0000, 0.5000, 0.4613, 0.5000, 0.9637],
}

KARATE_D = [0.2550, 0.2566, 0.1578, 0.1872, 0.0378, 0.1829]

BIOGRID_SPECIES = [
    "Gallus",
    "Bos",
    "Candida",
    "Xenopus",
    "HIV-1",
    "Rattus",
    "C.elegans",
]
BIOGRID_Q = [0.2145, 0.0000, 0.3621, 0.3286, 0.2137, 0.2057, 0.5205]
BIOGRID_NMI = [0.6213, 0.7739, 0.5641, 0.7088, 0.5130, 0.3845, 0.6381]
BIOGRID_PR = [0.9663, 0.9848, 0.9647, 0.9624, 0.9647, 0.9601, 0.9609]

LAMBDA_X = [0.2, 0.4, 0.6, 0.8]
LAMBDA_Y = [0.2094, 0.2853, 0.3612, 0.4371]


def _save_line_chart(path: Path, title: str, xlabel: str, ylabel: str) -> None:
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, linestyle="--", alpha=0.35)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def metric_compare_chart(metric: str, ylabel: str, filename: str) -> None:
    plt.figure(figsize=(10, 5))
    plt.plot(ALGORITHMS, KARATE[metric], marker="o", linewidth=2.2, label="Karate")
    plt.plot(ALGORITHMS, AUCS[metric], marker="s", linewidth=2.2, label="AUCS")
    plt.legend()
    _save_line_chart(OUTPUT / filename, f"{metric} Across Algorithms", "Algorithm", ylabel)


def biogrid_chart() -> None:
    plt.figure(figsize=(11, 5.5))
    plt.plot(BIOGRID_SPECIES, BIOGRID_Q, marker="o", linewidth=2.0, label="Q")
    plt.plot(BIOGRID_SPECIES, BIOGRID_NMI, marker="s", linewidth=2.0, label="NMI")
    plt.plot(BIOGRID_SPECIES, BIOGRID_PR, marker="^", linewidth=2.0, label="pr")
    plt.legend()
    _save_line_chart(
        OUTPUT / "chart_biogrid_dh_species_lines.png",
        "DH-Louvain Metrics on BioGRID Species",
        "Species",
        "Metric Value",
    )


def lambda_chart() -> None:
    plt.figure(figsize=(8, 4.8))
    plt.plot(LAMBDA_X, LAMBDA_Y, marker="o", linewidth=2.4, color="#2c7fb8")
    _save_line_chart(
        OUTPUT / "chart_aucs_lambda_multiresolution.png",
        "AUCS Multiresolution Trend",
        "Lambda",
        "Weighted Modularity Density",
    )


def ea_history_chart() -> None:
    path = OUTPUT / "ea_optimize_20260412_155834.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    xs = [item["generation"] for item in data["history"]]
    best = [item["best_fitness"] for item in data["history"]]
    mean = [item["mean_fitness"] for item in data["history"]]
    plt.figure(figsize=(8, 4.8))
    plt.plot(xs, best, marker="o", linewidth=2.2, label="Best Fitness")
    plt.plot(xs, mean, marker="s", linewidth=2.2, label="Mean Fitness")
    plt.legend()
    _save_line_chart(
        OUTPUT / "chart_ea_fitness_history.png",
        "Evolutionary Optimization History",
        "Generation",
        "Fitness",
    )


def conclusion_ranking_chart() -> None:
    import pandas as pd

    df = pd.DataFrame(
        {
            "algorithm": ALGORITHMS,
            "karate_q": KARATE["Q"],
            "karate_d": KARATE_D,
            "karate_nmi": KARATE["NMI"],
            "karate_pr": KARATE["pr"],
            "aucs_q": AUCS["Q"],
            "aucs_d": AUCS["D"],
            "aucs_nmi": AUCS["NMI"],
            "aucs_pr": AUCS["pr"],
        }
    )
    detect_cols = ["karate_q", "karate_d", "karate_nmi", "aucs_q", "aucs_d", "aucs_nmi"]
    privacy_cols = ["karate_pr", "aucs_pr"]
    for col in detect_cols + privacy_cols:
        df[f"rank_{col}"] = df[col].rank(ascending=False, method="average")

    df["community_rank"] = df[[f"rank_{c}" for c in detect_cols]].mean(axis=1)
    df["privacy_rank"] = df[[f"rank_{c}" for c in privacy_cols]].mean(axis=1)
    df = df.sort_values("community_rank")

    plt.figure(figsize=(10.5, 4.8))
    xs = range(len(df))
    width = 0.36
    plt.bar([x - width / 2 for x in xs], df["community_rank"], width=width, label="Community Detection Rank")
    plt.bar([x + width / 2 for x in xs], df["privacy_rank"], width=width, label="Privacy Protection Rank")
    plt.xticks(list(xs), df["algorithm"], rotation=0)
    plt.ylabel("Average Rank (Lower is Better)")
    plt.title("Overall Ranking Across Benchmark Metrics")
    plt.grid(True, axis="y", linestyle="--", alpha=0.35)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT / "chart_conclusion_algorithm_ranking.png", dpi=220, bbox_inches="tight")
    plt.close()


def _plot_lfr(df: pd.DataFrame, x_key: str, y_key: str, filename: str, title: str, xlabel: str, ylabel: str) -> None:
    plt.figure(figsize=(10.5, 5.6))
    for algo in ALGORITHMS:
        series = (
            df[df["algorithm"] == algo]
            .groupby(x_key, as_index=False)[y_key]
            .mean()
            .sort_values(x_key)
        )
        if series.empty:
            continue
        plt.plot(series[x_key], series[y_key], marker="o", linewidth=2.0, label=algo)
    plt.legend(ncol=3, fontsize=8)
    _save_line_chart(OUTPUT / filename, title, xlabel, ylabel)


def lfr_parameter_charts() -> None:
    if MU_CSV.exists():
        mu_df = pd.read_csv(MU_CSV)
        _plot_lfr(
            mu_df,
            "mu",
            "module_density",
            "chart_lfr_mu_group_density_n300_all.png",
            "LFR N=300: D vs μ",
            "Mixing Parameter μ",
            "Module Density D",
        )
        _plot_lfr(
            mu_df,
            "mu",
            "modularity",
            "chart_lfr_mu_group_modularity_n300_all.png",
            "LFR N=300: Q vs μ",
            "Mixing Parameter μ",
            "Modularity Q",
        )
        _plot_lfr(
            mu_df,
            "mu",
            "nmi",
            "chart_lfr_mu_group_nmi_n300_all.png",
            "LFR N=300: NMI vs μ",
            "Mixing Parameter μ",
            "NMI",
        )

    if LAMBDA_CSV.exists():
        lambda_df = pd.read_csv(LAMBDA_CSV)
        _plot_lfr(
            lambda_df,
            "lambd",
            "module_density",
            "chart_lfr_lambda_group_density_n300_all.png",
            "LFR N=300: D vs λ",
            "Lambda λ",
            "Module Density D",
        )
        _plot_lfr(
            lambda_df,
            "lambd",
            "modularity",
            "chart_lfr_lambda_group_modularity_n300_all.png",
            "LFR N=300: Q vs λ",
            "Lambda λ",
            "Modularity Q",
        )
        _plot_lfr(
            lambda_df,
            "lambd",
            "nmi",
            "chart_lfr_lambda_group_nmi_n300_all.png",
            "LFR N=300: NMI vs λ",
            "Lambda λ",
            "NMI",
        )
        _plot_lfr(
            lambda_df,
            "lambd",
            "privacy_rate",
            "chart_lfr_lambda_group_privacy_n300_all.png",
            "LFR N=300: pr vs λ",
            "Lambda λ",
            "Privacy Rate pr",
        )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    metric_compare_chart("Q", "Modularity Q", "chart_compare_q_lines.png")
    metric_compare_chart("NMI", "NMI", "chart_compare_nmi_lines.png")
    metric_compare_chart("pr", "Privacy Rate pr", "chart_compare_privacy_lines.png")
    biogrid_chart()
    lambda_chart()
    ea_history_chart()
    lfr_parameter_charts()
    conclusion_ranking_chart()


if __name__ == "__main__":
    main()
