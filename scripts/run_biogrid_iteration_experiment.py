from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from pathlib import Path
import sys
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiment_datasets import load_dataset
from src.pmcdm import CloudServer1, CloudServer2, TerminalClient
from src.pmcdm.dh_louvain import DHLouvain
from src.pmcdm.metrics import communities_to_groups, modularity_density, nmi_score, partition_to_labels, reference_labels_slouvain


OUTPUT = ROOT / "output"
OUT_CSV = OUTPUT / "biogrid_5_iterations_experiment.csv"
OUT_IMG = OUTPUT / "chart_biogrid_5_iterations_triptych.png"

ITERATIONS = [1, 2, 3, 4, 5, 6]
RANDOM_STATE = 42
EPSILON = 1.0
DELTA = 1e-5
KEY_SIZE = 512
LAMBDA = 0.5

NETWORKS = [
    ("Plasmodium", "BIOGRID-ORGANISM-Plasmodium_falciparum_3D7-5.0.256.tab3.txt"),
    ("HIV-1", "BIOGRID-ORGANISM-Human_Immunodeficiency_Virus_1-5.0.256.tab3.txt"),
    ("E.coli", "BIOGRID-ORGANISM-Escherichia_coli_K12_MG1655-5.0.256.tab3.txt"),
    ("Xenopus", "BIOGRID-ORGANISM-Xenopus_laevis-5.0.256.tab3.txt"),
    ("MERS", "BIOGRID-ORGANISM-Middle-East_Respiratory_Syndrome-related_Coronavirus-5.0.256.tab3.txt"),
]

COLORS = ["#d62728", "#1f77b4", "#2ca02c", "#8c564b", "#ff33ff"]
MARKERS = ["*", "s", "o", "d", "x"]


@dataclass
class ExperimentRow:
    species: str
    member_file: str
    iteration: int
    modularity: float
    d_over_n: float
    nmi: float
    communities: int
    n_nodes: int
    n_layers: int
    dataset_summary: str


def _fieldnames() -> list[str]:
    return list(ExperimentRow.__dataclass_fields__.keys())


def _load_existing_rows() -> list[ExperimentRow]:
    if not OUT_CSV.exists():
        return []
    rows: list[ExperimentRow] = []
    with OUT_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for item in csv.DictReader(handle):
            rows.append(
                ExperimentRow(
                    species=item["species"],
                    member_file=item["member_file"],
                    iteration=int(item["iteration"]),
                    modularity=float(item["modularity"]),
                    d_over_n=float(item["d_over_n"]),
                    nmi=float(item["nmi"]),
                    communities=int(float(item["communities"])),
                    n_nodes=int(float(item["n_nodes"])),
                    n_layers=int(float(item["n_layers"])),
                    dataset_summary=item["dataset_summary"],
                )
            )
    return rows


def _append_row(row: ExperimentRow) -> None:
    exists = OUT_CSV.exists()
    with OUT_CSV.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_fieldnames())
        if not exists:
            writer.writeheader()
        writer.writerow(asdict(row))


def _load_bundle(member_file: str):
    return load_dataset(
        "biogrid",
        variant={
            "member": member_file,
            "top_layers": 3,
            "min_edges": 12,
            "max_nodes": 1000,
            "include_genetic": True,
            "auto_layers": True,
        },
    )


def _run_one(bundle, ref_labels: list[int], iteration: int) -> tuple[float, float, float, int]:
    cloud1 = CloudServer1(EPSILON, DELTA, KEY_SIZE)
    terminal = TerminalClient(cloud1.he)
    processed_layers = []
    for layer in bundle.layers:
        uploaded = terminal.encrypt_upload(layer)
        processed_layers.append(cloud1.perturb_layer(uploaded, mode="dp"))

    cloud2 = CloudServer2(cloud1, random_state=RANDOM_STATE)
    cloud2.detector = DHLouvain(random_state=RANDOM_STATE, max_iter=iteration)
    communities = cloud2.run_dh_louvain(processed_layers, lambd=LAMBDA)

    nodes = sorted(bundle.layers[0].nodes())
    pred = partition_to_labels(communities, nodes)
    nmi = nmi_score(
        pred,
        layers=bundle.layers,
        gt_labels=bundle.ground_truth,
        random_state=RANDOM_STATE,
        slouvain_ref_labels=ref_labels,
    )

    metric_graph = processed_layers[0]
    groups = list(communities_to_groups(communities).values())
    modularity = nx.algorithms.community.modularity(metric_graph, groups, weight="weight")
    d_over_n = modularity_density(metric_graph, communities)
    return modularity, d_over_n, nmi, len(set(communities.values()))


def _plot(rows: Iterable[ExperimentRow]) -> None:
    row_list = list(rows)
    if not row_list:
        return

    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.0))
    specs = [
        ("d_over_n", "Statistical values of D/n", None),
        ("modularity", "Statistical values of Q", None),
        ("nmi", "Statistical values of NMI", (0.0, 1.0)),
    ]

    for ax, (field, ylabel, ylim) in zip(axes, specs):
        for i, (label, _) in enumerate(NETWORKS):
            series = [row for row in row_list if row.species == label]
            series.sort(key=lambda item: item.iteration)
            if not series:
                continue
            ax.plot(
                [row.iteration for row in series],
                [getattr(row, field) for row in series],
                color=COLORS[i],
                marker=MARKERS[i],
                linewidth=1.8,
                markersize=6,
                label=label,
            )
        ax.set_xlabel("Number of iterations")
        ax.set_ylabel(ylabel, fontstyle="italic")
        ax.set_xticks(ITERATIONS)
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
    plt.savefig(OUT_IMG, dpi=240, bbox_inches="tight")
    plt.close()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    rows = _load_existing_rows()
    completed = {(row.species, row.iteration) for row in rows}
    print(f"[resume] 已完成 {len(completed)}/{len(NETWORKS) * len(ITERATIONS)} 个组合", flush=True)

    for label, member_file in NETWORKS:
        pending = [it for it in ITERATIONS if (label, it) not in completed]
        if not pending:
            print(f"[dataset] {label} 已完成，跳过", flush=True)
            continue

        print(f"[dataset] {label}", flush=True)
        bundle = _load_bundle(member_file)
        ref_labels = reference_labels_slouvain(bundle.layers, RANDOM_STATE)

        for iteration in pending:
            print(f"  iteration={iteration}", flush=True)
            modularity, d_over_n, nmi, communities = _run_one(bundle, ref_labels, iteration)
            row = ExperimentRow(
                species=label,
                member_file=member_file,
                iteration=iteration,
                modularity=modularity,
                d_over_n=d_over_n,
                nmi=nmi,
                communities=communities,
                n_nodes=bundle.layers[0].number_of_nodes(),
                n_layers=len(bundle.layers),
                dataset_summary=bundle.summary,
            )
            _append_row(row)
            rows.append(row)
            completed.add((label, iteration))
            print(f"    已保存 {label} iteration={iteration}", flush=True)

    rows.sort(key=lambda item: (item.species, item.iteration))
    _plot(rows)
    print(OUT_CSV)
    print(OUT_IMG)


if __name__ == "__main__":
    main()
