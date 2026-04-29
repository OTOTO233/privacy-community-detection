from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
CSV_PATH = OUTPUT / "biogrid_5_lambda_sweep_20260413_194919.csv"
OUT_PATH = OUTPUT / "chart_biogrid_5_lambda_triptych.png"

LABEL_Q = r"$Q$"
LABEL_D = r"$D$"
LABEL_NMI = r"$NMI$"
LABEL_LAMBDA = r"$\lambda$"

COLORS = ["#d62728", "#1f77b4", "#2ca02c", "#8c564b", "#ff33ff"]
MARKERS = ["*", "s", "o", "d", "x"]


def main() -> None:
    df = pd.read_csv(CSV_PATH)
    species = list(df["species_label"].drop_duplicates())

    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.0))
    metric_specs = [
        ("module_density", rf"Statistical values of {LABEL_D}", None),
        ("modularity", rf"Statistical values of {LABEL_Q}", None),
        ("nmi", rf"Statistical values of {LABEL_NMI}", (0.0, 1.0)),
    ]

    for ax, (metric, ylabel, ylim) in zip(axes, metric_specs):
        for i, label in enumerate(species):
            sub = df[df["species_label"] == label].sort_values("lambda")
            ax.plot(
                sub["lambda"],
                sub[metric],
                color=COLORS[i % len(COLORS)],
                marker=MARKERS[i % len(MARKERS)],
                linewidth=1.8,
                markersize=6,
                label=label,
            )
        ax.set_xlabel(LABEL_LAMBDA)
        ax.set_ylabel(ylabel)
        ax.set_xlim(df["lambda"].min(), df["lambda"].max())
        if ylim is not None:
            ax.set_ylim(*ylim)
        ax.tick_params(direction="in", length=3)
        for spine in ax.spines.values():
            spine.set_linewidth(1.0)
        ax.legend(loc="best", frameon=True, fancybox=False, edgecolor="black", fontsize=9)

    axes[0].text(0.5, -0.28, "(a)", transform=axes[0].transAxes, ha="center", va="top")
    axes[1].text(0.5, -0.28, "(b)", transform=axes[1].transAxes, ha="center", va="top")
    axes[2].text(0.5, -0.28, "(c)", transform=axes[2].transAxes, ha="center", va="top")

    plt.tight_layout(w_pad=2.2)
    plt.savefig(OUT_PATH, dpi=240, bbox_inches="tight")
    plt.close()
    print(OUT_PATH)


if __name__ == "__main__":
    main()
