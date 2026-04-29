from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiment_datasets import load_dataset
from src.pmcdm import CloudServer1, CloudServer2, TerminalClient
from src.pmcdm.metrics import communities_to_groups, modularity_density, nmi_score, partition_to_labels, reference_labels_slouvain
from src.pmcdm.dh_louvain import DHLouvain
from scripts.chart_style import SONGTI_SMALL_FIVE_PT, apply_songti_small5

OUTPUT = ROOT / "output"
MU_CSV = OUTPUT / "lfr_experiment_mu_n300_all_complete.csv"
ITER_CSV = OUTPUT / "biogrid_5_iterations_experiment.csv"
EA_SUMMARY_CSV = OUTPUT / "ea_before_after_summary.csv"
EA_JSON = OUTPUT / "ea_optimize_20260412_155834.json"

apply_songti_small5()

ALGO_ZH = {
    "S-Louvain": "标准方法",
    "PD-Louvain": "加密方法",
    "R-Louvain": "随机扰动方法",
    "DP-Louvain": "差分隐私方法",
    "K-Louvain": "K匿名方法",
    "DH-Louvain": "双隐私方法",
}

SPECIES_ZH = {
    "Gallus gallus": "鸡",
    "Bos taurus": "牛",
    "Candida albicans SC5314": "白色念珠菌SC5314",
    "Xenopus laevis": "非洲爪蟾",
    "Human Immunodeficiency Virus 1": "人类免疫缺陷病毒1型",
    "Rattus norvegicus": "大鼠",
    "Caenorhabditis elegans": "秀丽隐杆线虫",
    "Plasmodium": "恶性疟原虫3D7",
    "HIV-1": "人类免疫缺陷病毒1型",
    "E.coli": "大肠杆菌K12 MG1655",
    "Xenopus": "非洲爪蟾",
    "MERS": "中东呼吸综合征相关冠状病毒",
}

BIOGRID_TABLE = pd.DataFrame(
    [
        ("鸡", 0.2145, 0.6213, 0.9663),
        ("牛", 0.0000, 0.7739, 0.9848),
        ("白色念珠菌SC5314", 0.3621, 0.5641, 0.9647),
        ("非洲爪蟾", 0.3286, 0.7088, 0.9624),
        ("人类免疫缺陷病毒1型", 0.2137, 0.5130, 0.9647),
        ("大鼠", 0.2057, 0.3845, 0.9601),
        ("秀丽隐杆线虫", 0.5205, 0.6381, 0.9609),
    ],
    columns=["物种", "模块度Q", "归一化互信息NMI", "隐私率"],
)

LABEL_Q = r"$Q$"
LABEL_D = r"$D$"
LABEL_NMI = r"$NMI$"
LABEL_MU = r"$\mu$"
LABEL_LAMBDA = r"$\lambda$"
LABEL_PR = r"$p_r$"

KARATE = {
    "Q": [0.4245, 0.4254, 0.3701, 0.3909, 0.3060, 0.3611],
    "D": [0.2550, 0.2566, 0.1578, 0.1872, 0.0378, 0.1829],
    "NMI": [0.4900, 0.5878, 0.5869, 0.5005, 0.4400, 0.6877],
    "PR": [0.5000, 1.0000, 0.5000, 0.4594, 0.5000, 0.9594],
}
AUCS = {
    "Q": [0.7392, 0.7392, 0.6597, 0.6814, 0.1385, 0.6440],
    "D": [0.0542, 0.0542, 0.0522, 0.0487, -0.1137, 0.0430],
    "NMI": [0.7827, 0.7827, 0.7551, 0.7653, 0.7678, 0.6712],
    "PR": [0.5000, 1.0000, 0.5000, 0.4613, 0.5000, 0.9637],
}
ALGORITHMS = ["S-Louvain", "PD-Louvain", "R-Louvain", "DP-Louvain", "K-Louvain", "DH-Louvain"]


def _aggregate_layers(layers: list[nx.Graph]) -> nx.Graph:
    graph = nx.Graph()
    for layer in layers:
        graph.add_nodes_from(layer.nodes())
        for u, v, data in layer.edges(data=True):
            weight = float(data.get("weight", 1.0))
            if graph.has_edge(u, v):
                graph[u][v]["weight"] += weight
            else:
                graph.add_edge(u, v, weight=weight)
    return graph


def _save(path: Path) -> None:
    apply_songti_small5()
    plt.tight_layout()
    plt.savefig(path, dpi=240, bbox_inches="tight")
    plt.close()


def generate_biogrid_species_chart() -> None:
    plt.figure(figsize=(11.0, 5.6))
    plt.plot(BIOGRID_TABLE["物种"], BIOGRID_TABLE["模块度Q"], marker="o", linewidth=2.0, label=f"模块度 {LABEL_Q}")
    plt.plot(BIOGRID_TABLE["物种"], BIOGRID_TABLE["归一化互信息NMI"], marker="s", linewidth=2.0, label=f"归一化互信息 {LABEL_NMI}")
    plt.plot(BIOGRID_TABLE["物种"], BIOGRID_TABLE["隐私率"], marker="^", linewidth=2.0, label=f"隐私率 {LABEL_PR}")
    plt.xlabel("物种")
    plt.ylabel("指标值")
    plt.grid(True, linestyle="--", alpha=0.35)
    plt.legend()
    _save(OUTPUT / "chart_biogrid_dh_species_lines_cn.png")


def generate_iterations_chart() -> None:
    df = pd.read_csv(ITER_CSV)
    fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.2))
    specs = [
        ("d_over_n", rf"归一化模块密度 {LABEL_D}/$n$"),
        ("modularity", f"模块度 {LABEL_Q}"),
        ("nmi", f"归一化互信息 {LABEL_NMI}"),
    ]
    colors = ["#d62728", "#1f77b4", "#2ca02c", "#8c564b", "#ff33ff"]
    markers = ["*", "s", "o", "d", "x"]
    species_order = ["Plasmodium", "HIV-1", "E.coli", "Xenopus", "MERS"]
    for ax, (field, ylabel) in zip(axes, specs):
        for idx, species in enumerate(species_order):
            subset = df[df["species"] == species].sort_values("iteration")
            ax.plot(
                subset["iteration"],
                subset[field],
                color=colors[idx],
                marker=markers[idx],
                linewidth=1.8,
                markersize=6,
                label=SPECIES_ZH[species],
            )
        ax.set_xlabel("迭代次数")
        ax.set_ylabel(ylabel)
        ax.set_xticks(sorted(df["iteration"].unique()))
        if field == "modularity":
            ax.set_ylim(top=0.70)
        ax.tick_params(direction="in", length=3)
        for spine in ax.spines.values():
            spine.set_linewidth(1.0)
        ax.legend(loc="best", frameon=True, fancybox=False, edgecolor="black", fontsize=SONGTI_SMALL_FIVE_PT)
    axes[0].text(0.5, -0.25, "（a）", transform=axes[0].transAxes, ha="center", va="top", fontsize=SONGTI_SMALL_FIVE_PT)
    axes[1].text(0.5, -0.25, "（b）", transform=axes[1].transAxes, ha="center", va="top", fontsize=SONGTI_SMALL_FIVE_PT)
    axes[2].text(0.5, -0.25, "（c）", transform=axes[2].transAxes, ha="center", va="top", fontsize=SONGTI_SMALL_FIVE_PT)
    plt.tight_layout(w_pad=2.0)
    plt.savefig(OUTPUT / "chart_biogrid_5_iterations_triptych_cn.png", dpi=240, bbox_inches="tight")
    plt.close()


def generate_lfr_mu_charts() -> None:
    df = pd.read_csv(MU_CSV)
    configs = [
        ("modularity", "chart_lfr_mu_group_modularity_n300_all_cn.png", f"模块度 {LABEL_Q}"),
        ("module_density", "chart_lfr_mu_group_density_n300_all_cn.png", f"模块密度 {LABEL_D}"),
        ("nmi", "chart_lfr_mu_group_nmi_n300_all_cn.png", f"归一化互信息 {LABEL_NMI}"),
    ]
    for field, filename, ylabel in configs:
        plt.figure(figsize=(10.5, 5.6))
        for algo in ALGORITHMS:
            subset = df[df["algorithm"] == algo].groupby("mu", as_index=False)[field].mean().sort_values("mu")
            plt.plot(subset["mu"], subset[field], marker="o", linewidth=2.0, label=ALGO_ZH[algo])
        plt.xlabel(f"混合参数 {LABEL_MU}")
        plt.ylabel(ylabel)
        if field == "module_density":
            plt.ylim(top=0.5)
        plt.grid(True, linestyle="--", alpha=0.35)
        plt.legend(ncol=3, fontsize=SONGTI_SMALL_FIVE_PT)
        _save(OUTPUT / filename)


def generate_ea_history_chart() -> None:
    payload = json.loads(EA_JSON.read_text(encoding="utf-8"))
    xs = [row["generation"] for row in payload["history"]]
    best = [row["best_fitness"] for row in payload["history"]]
    mean = [row["mean_fitness"] for row in payload["history"]]
    plt.figure(figsize=(8.0, 4.8))
    plt.plot(xs, best, marker="o", linewidth=2.2, label="最优适应度")
    plt.plot(xs, mean, marker="s", linewidth=2.2, label="平均适应度")
    plt.xlabel("迭代代数")
    plt.ylabel("适应度")
    plt.grid(True, linestyle="--", alpha=0.35)
    plt.legend()
    _save(OUTPUT / "chart_ea_fitness_history_cn.png")


def generate_ea_before_after_chart() -> None:
    df = pd.read_csv(EA_SUMMARY_CSV)
    baseline = df[df["scheme"] == "基线参数"].iloc[0]
    optimized = df[df["scheme"] == "进化优化参数"].iloc[0]
    metrics = [
        ("mean_fitness", "适应度"),
        ("mean_modularity", f"模块度 {LABEL_Q}"),
        ("mean_module_density", f"模块密度 {LABEL_D}"),
        ("mean_nmi", LABEL_NMI),
        ("mean_privacy_rate", f"隐私率 {LABEL_PR}"),
    ]
    plt.figure(figsize=(9.2, 5.2))
    xs = range(len(metrics))
    width = 0.36
    plt.bar([x - width / 2 for x in xs], [baseline[key] for key, _ in metrics], width=width, label="基线参数")
    plt.bar([x + width / 2 for x in xs], [optimized[key] for key, _ in metrics], width=width, label="进化优化参数")
    plt.xticks(list(xs), [label for _, label in metrics])
    plt.ylabel("平均值")
    plt.grid(True, axis="y", linestyle="--", alpha=0.35)
    plt.legend()
    _save(OUTPUT / "chart_ea_before_after_compare_cn.png")


def generate_ranking_chart() -> None:
    df = pd.DataFrame(
        {
            "算法": [ALGO_ZH[item] for item in ALGORITHMS],
            "karate_q": KARATE["Q"],
            "karate_d": KARATE["D"],
            "karate_nmi": KARATE["NMI"],
            "karate_pr": KARATE["PR"],
            "aucs_q": AUCS["Q"],
            "aucs_d": AUCS["D"],
            "aucs_nmi": AUCS["NMI"],
            "aucs_pr": AUCS["PR"],
        }
    )
    detect_cols = ["karate_q", "karate_d", "karate_nmi", "aucs_q", "aucs_d", "aucs_nmi"]
    privacy_cols = ["karate_pr", "aucs_pr"]
    for col in detect_cols + privacy_cols:
        df[f"rank_{col}"] = df[col].rank(ascending=False, method="average")
    df["检测能力平均排名"] = df[[f"rank_{c}" for c in detect_cols]].mean(axis=1)
    df["隐私保护平均排名"] = df[[f"rank_{c}" for c in privacy_cols]].mean(axis=1)
    df = df.sort_values("检测能力平均排名")
    plt.figure(figsize=(10.5, 4.8))
    xs = range(len(df))
    width = 0.36
    plt.bar([x - width / 2 for x in xs], df["检测能力平均排名"], width=width, label="检测能力排名")
    plt.bar([x + width / 2 for x in xs], df["隐私保护平均排名"], width=width, label="隐私保护排名")
    plt.xticks(list(xs), df["算法"], rotation=0)
    plt.ylabel("平均排名（越小越好）")
    plt.grid(True, axis="y", linestyle="--", alpha=0.35)
    plt.legend()
    _save(OUTPUT / "chart_conclusion_algorithm_ranking_cn.png")


def _run_dh(bundle) -> dict:
    cloud1 = CloudServer1(1.0, 1e-5, 512)
    terminal = TerminalClient(cloud1.he)
    processed = []
    for layer in bundle.layers:
        uploaded = terminal.encrypt_upload(layer)
        processed.append(cloud1.perturb_layer(uploaded, mode="dp"))
    cloud2 = CloudServer2(cloud1, random_state=42)
    cloud2.detector = DHLouvain(random_state=42, max_iter=6)
    return cloud2.run_dh_louvain(processed, lambd=0.5)


def _draw_community_graph(graph: nx.Graph, communities: dict, title: str, path: Path) -> None:
    pos = nx.spring_layout(graph, seed=42, k=0.45, iterations=80)
    unique = sorted(set(communities.values()))
    color_map = {cid: plt.cm.Set3(i / max(1, len(unique) - 1 if len(unique) > 1 else 1)) for i, cid in enumerate(unique)}
    node_colors = [color_map[communities[node]] for node in graph.nodes()]
    plt.figure(figsize=(10.0, 8.0))
    nx.draw_networkx_edges(graph, pos, alpha=0.12, width=0.5)
    nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=55, alpha=0.88, linewidths=0.2, edgecolors="white")
    degrees = dict(graph.degree())
    top_nodes = {node for node, _ in sorted(degrees.items(), key=lambda item: (-item[1], str(item[0])))[:8]}
    labels = {node: str(node) for node in top_nodes}
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=7)
    plt.title(title)
    plt.axis("off")
    _save(path)


def _draw_multilayer_graph(layers: list[nx.Graph], communities: dict, title: str, path: Path) -> None:
    aggregate = _aggregate_layers(layers)
    base_pos = nx.spring_layout(aggregate, seed=42, k=1.15, iterations=160)
    unique = sorted(set(communities.values()))
    color_map = {cid: plt.cm.Set3(i / max(1, len(unique) - 1 if len(unique) > 1 else 1)) for i, cid in enumerate(unique)}
    fig = plt.figure(figsize=(11.5, 8.0))
    ax = fig.add_subplot(111, projection="3d")
    gap = 1.05
    layer_names = [layer.graph.get("layer", f"层{idx + 1}") for idx, layer in enumerate(layers)]
    for lid, layer in enumerate(layers):
        z = lid * gap
        for u, v in layer.edges():
            x1, y1 = base_pos[u]
            x2, y2 = base_pos[v]
            ax.plot([x1, x2], [y1, y2], [z, z], color="#8a8a8a", alpha=0.24, linewidth=1.25)
        xs, ys, zs, cs = [], [], [], []
        for node in layer.nodes():
            x, y = base_pos[node]
            xs.append(x)
            ys.append(y)
            zs.append(z)
            cs.append(color_map[communities[node]])
        ax.scatter(xs, ys, zs, c=cs, s=34, alpha=0.94, depthshade=True, edgecolors="white", linewidths=0.25)
        ax.text2D(0.02, 0.95 - lid * 0.065, f"第{lid + 1}层：{layer_names[lid]}", transform=ax.transAxes, fontsize=13)
    shared = set(layers[0].nodes())
    for lid in range(1, len(layers)):
        shared &= set(layers[lid].nodes())
    top_nodes = list(sorted(shared, key=lambda node: aggregate.degree(node), reverse=True)[:8])
    for node in top_nodes:
        x, y = base_pos[node]
        for lid in range(len(layers) - 1):
            ax.plot([x, x], [y, y], [lid * gap, (lid + 1) * gap], color="#4b6cb7", alpha=0.26, linewidth=1.35)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    ax.grid(False)
    ax.view_init(elev=22, azim=38)
    plt.savefig(path, dpi=240, bbox_inches="tight")
    plt.close(fig)


def generate_dataset_visuals() -> None:
    datasets = [
        ("karate", None, "空手道俱乐部", OUTPUT / "karate_dh_vis_cn.png"),
        ("aucs", None, "多层社交网络", OUTPUT / "aucs_dh_vis_cn.png"),
        ("biogrid", {"member": "BIOGRID-ORGANISM-Plasmodium_falciparum_3D7-5.0.256.tab3.txt", "top_layers": 3, "min_edges": 12, "max_nodes": 300, "include_genetic": True, "auto_layers": True}, "恶性疟原虫3D7", OUTPUT / "biogrid_plasmodium_vis_cn.png"),
        ("biogrid", {"member": "BIOGRID-ORGANISM-Human_Immunodeficiency_Virus_1-5.0.256.tab3.txt", "top_layers": 3, "min_edges": 12, "max_nodes": 300, "include_genetic": True, "auto_layers": True}, "人类免疫缺陷病毒1型", OUTPUT / "biogrid_hiv1_vis_cn.png"),
        ("biogrid", {"member": "BIOGRID-ORGANISM-Escherichia_coli_K12_MG1655-5.0.256.tab3.txt", "top_layers": 3, "min_edges": 12, "max_nodes": 300, "include_genetic": True, "auto_layers": True}, "大肠杆菌K12 MG1655", OUTPUT / "biogrid_ecoli_vis_cn.png"),
    ]
    for name, variant, title, path in datasets:
        bundle = load_dataset(name, variant=variant)
        communities = _run_dh(bundle)
        graph = _aggregate_layers(bundle.layers)
        _draw_community_graph(graph, communities, f"{title}数据集的社区可视化结果", path)
        if name == "biogrid":
            if "Plasmodium" in bundle.name:
                multilayer_path = OUTPUT / "biogrid_plasmodium_multilayer_cn.png"
            elif "Human Immunodeficiency Virus 1" in bundle.name:
                multilayer_path = OUTPUT / "biogrid_hiv1_multilayer_cn.png"
            else:
                multilayer_path = OUTPUT / "biogrid_ecoli_multilayer_cn.png"
            _draw_multilayer_graph(bundle.layers, communities, f"{title}数据集的多层网络可视化结果", multilayer_path)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    generate_biogrid_species_chart()
    generate_iterations_chart()
    generate_lfr_mu_charts()
    generate_ea_history_chart()
    generate_ea_before_after_chart()
    generate_ranking_chart()
    generate_dataset_visuals()


if __name__ == "__main__":
    main()
