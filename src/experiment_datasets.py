"""Dataset loaders for CLI experiments."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Dict, List
import zipfile
import csv
from collections import Counter, defaultdict

import networkx as nx
import pandas as pd

from .pmcdm import PMCDMExperiment


@dataclass
class DatasetBundle:
    # 所有数据集最终都被整理成这个统一结构，主实验代码不需要关心它来自真实数据还是生成器。
    name: str
    layers: List[nx.Graph]
    ground_truth: Dict[int, int]
    summary: str


LFR_PRESETS = {
    "small_easy": {
        "label": "LFR Small Easy",
        "params": {
            "n": 40,
            "tau1": 2.5,
            "tau2": 1.5,
            "mu": 0.1,
            "average_degree": 6,
            "min_community": 10,
            "max_community": 20,
            "max_iters": 10000,
        },
    },
    "small_noisier": {
        "label": "LFR Small Noisier",
        "params": {
            "n": 40,
            "tau1": 2.5,
            "tau2": 1.5,
            "mu": 0.2,
            "average_degree": 6,
            "min_community": 10,
            "max_community": 20,
            "max_iters": 10000,
        },
    },
    "medium_noisier": {
        "label": "LFR Medium Noisier",
        "params": {
            "n": 60,
            "tau1": 2.5,
            "tau2": 1.5,
            "mu": 0.2,
            "average_degree": 6,
            "min_community": 10,
            "max_community": 20,
            "max_iters": 10000,
        },
    },
    # # 与论文实验表对齐：N=500，γ=2，⟨k⟩=10，maxk=40，q=3；μ 由实验扫描。
    # # 注：文献 β=1，NetworkX 要求 tau2>1，此处取 1.5 以保证可生成。
    # "bench500": {
    #     "label": "LFR N500（论文表：gamma=2, avg_k=10, maxk=40, q=3）",
    #     "params": {
    #         "n": 500,
    #         "tau1": 2.0,
    #         "tau2": 1.5,
    #         "mu": 0.25,
    #         "average_degree": 10,
    #         "max_degree": 40,
    #         "min_community": 20,
    #         "max_community": 50,
    #         "max_iters": 15000,
    #         "multiplex_layers": 3,
    #     },
    # },
}


def list_datasets() -> List[str]:
    return ["karate", "aucs", "lfr", "mlfr", "biogrid"]


def load_dataset(name: str, variant: Any = None) -> DatasetBundle:
    # 这里相当于一个总入口：根据用户选择分发到不同的数据集装载器。
    normalized = name.strip().lower()
    if normalized == "karate":
        return load_karate_dataset()
    if normalized == "aucs":
        return load_aucs_dataset()
    if normalized == "lfr":
        return load_lfr_dataset(variant=variant)
    if normalized == "mlfr":
        return load_mlfr_dataset(variant=variant)
    if normalized == "biogrid":
        return load_biogrid_dataset(variant=variant)
    raise ValueError(f"不支持的数据集: {name}")


def load_karate_dataset() -> DatasetBundle:
    base_graph = nx.karate_club_graph()
    ground_truth = {
        node: 0 if data.get("club") == "Mr. Hi" else 1
        for node, data in base_graph.nodes(data=True)
    }
    layers = PMCDMExperiment.build_multiplex_from_base(base_graph, layers=3, seed=42)
    summary = f"Karate Club | 层数={len(layers)} | 节点={base_graph.number_of_nodes()} | 边={base_graph.number_of_edges()}"
    return DatasetBundle(
        name="Karate Club",
        layers=layers,
        ground_truth=ground_truth,
        summary=summary,
    )


def load_aucs_dataset() -> DatasetBundle:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "processed" / "aucs"
    layer_dir = data_dir / "layers"
    nodes_path = data_dir / "nodes.csv"

    if not nodes_path.exists():
        raise FileNotFoundError(
            "未找到 AUCS 处理后数据，请先运行 data 转换脚本生成 data/processed/aucs。"
        )

    # AUCS 自带节点属性表，因此可以直接把 group 字段当作真实标签。
    nodes = pd.read_csv(nodes_path)
    nodes["group"] = nodes["group"].fillna("NA")
    group_names = sorted(nodes["group"].unique())
    group_to_id = {group: idx for idx, group in enumerate(group_names)}
    ground_truth = {int(row.node_id): group_to_id[row.group] for row in nodes.itertuples()}

    node_ids = [int(node_id) for node_id in nodes["node_id"].tolist()]
    layer_names = ["coauthor", "facebook", "leisure", "lunch", "work"]
    layers: List[nx.Graph] = []
    edge_summaries: List[str] = []

    for layer_name in layer_names:
        layer_path = layer_dir / f"{layer_name}_undirected.txt"
        if not layer_path.exists():
            raise FileNotFoundError(f"未找到 AUCS 层文件: {layer_path}")
        edges = pd.read_csv(layer_path, sep=r"\s+", header=None)
        # 每个关系文件对应 AUCS 的一个层，如 lunch / work / facebook。
        graph = nx.Graph(layer=layer_name)
        graph.add_nodes_from(node_ids)
        for row in edges.itertuples(index=False):
            graph.add_edge(int(row[0]), int(row[1]), weight=float(row[2]))
        layers.append(graph)
        edge_summaries.append(f"{layer_name}={graph.number_of_edges()}")

    summary = f"AUCS | 层数={len(layers)} | 节点={len(node_ids)} | " + " ".join(edge_summaries)
    return DatasetBundle(
        name="AUCS",
        layers=layers,
        ground_truth=ground_truth,
        summary=summary,
    )


def list_lfr_presets() -> List[str]:
    return list(LFR_PRESETS.keys())


def _validate_lfr_params(params: Dict[str, Any]) -> Dict[str, Any]:
    # 这里只做“显然不合理”的参数校验，真正是否可生成还要交给 NetworkX 的 LFR 实现。
    multiplex_layers = int(params.get("multiplex_layers", 3))
    if multiplex_layers < 1 or multiplex_layers > 32:
        raise ValueError("LFR 参数错误: multiplex_layers 应在 1~32（多层网络层数 q）")

    validated: Dict[str, Any] = {
        "n": int(params["n"]),
        "tau1": float(params["tau1"]),
        "tau2": float(params["tau2"]),
        "mu": float(params["mu"]),
        "average_degree": int(params["average_degree"]),
        "min_community": int(params["min_community"]),
        "max_community": int(params["max_community"]),
        "max_iters": int(params.get("max_iters", 10000)),
        "multiplex_layers": multiplex_layers,
    }
    if params.get("max_degree") not in (None, ""):
        validated["max_degree"] = int(params["max_degree"])

    if validated["n"] < 10:
        raise ValueError("LFR 参数错误: n 必须 >= 10")
    if validated["tau1"] <= 1.0 or validated["tau2"] <= 1.0:
        raise ValueError("LFR 参数错误: tau1 和 tau2 必须 > 1")
    if not 0.0 <= validated["mu"] <= 1.0:
        raise ValueError("LFR 参数错误: mu 必须在 [0, 1] 范围内")
    if validated["average_degree"] <= 0:
        raise ValueError("LFR 参数错误: average_degree 必须 > 0")
    if validated["min_community"] <= 0 or validated["max_community"] <= 0:
        raise ValueError("LFR 参数错误: 社区大小必须 > 0")
    if validated["min_community"] > validated["max_community"]:
        raise ValueError("LFR 参数错误: min_community 不能大于 max_community")
    if validated["average_degree"] >= validated["n"]:
        raise ValueError("LFR 参数错误: average_degree 必须小于 n")
    if validated["max_iters"] <= 0:
        raise ValueError("LFR 参数错误: max_iters 必须 > 0")
    if "max_degree" in validated:
        md = validated["max_degree"]
        if md <= 1 or md >= validated["n"]:
            raise ValueError("LFR 参数错误: max_degree 应在 (1, n) 内")

    return validated


def load_lfr_dataset(variant: Any = None) -> DatasetBundle:
    seed = 42
    if isinstance(variant, dict):
        params = _validate_lfr_params(variant)
        label = "LFR Custom"
    else:
        preset_name = (variant or "small_easy").strip().lower()
        if preset_name not in LFR_PRESETS:
            raise ValueError(f"不支持的 LFR 预设: {variant}")
        preset = LFR_PRESETS[preset_name]
        params = _validate_lfr_params(preset["params"])
        label = preset["label"]

    # LFR 在这里先生成单层基准图，再复制成多层并加轻微权重差异。
    multiplex_layers = int(params["multiplex_layers"])
    nx_kwargs = {k: v for k, v in params.items() if k != "multiplex_layers"}
    base_graph = nx.generators.community.LFR_benchmark_graph(
        seed=seed,
        **nx_kwargs,
    )

    base_graph = nx.Graph(base_graph)
    base_graph.remove_edges_from(nx.selfloop_edges(base_graph))
    if not nx.is_connected(base_graph):
        largest_nodes = max(nx.connected_components(base_graph), key=len)
        base_graph = base_graph.subgraph(largest_nodes).copy()

    community_to_id: Dict[frozenset[int], int] = {}
    ground_truth: Dict[int, int] = {}
    # NetworkX LFR 给每个节点保存了 community 集合，这里把它压成整数标签。
    for node, data in base_graph.nodes(data=True):
        community = frozenset(data["community"])
        if community not in community_to_id:
            community_to_id[community] = len(community_to_id)
        ground_truth[node] = community_to_id[community]

    layers = PMCDMExperiment.build_multiplex_from_base(base_graph, layers=multiplex_layers, seed=seed)
    summary = (
        f"{label} | 层数 q={multiplex_layers} | 节点={base_graph.number_of_nodes()} "
        f"| 边={base_graph.number_of_edges()} | 社区数={len(set(ground_truth.values()))} "
        f"| mu={params['mu']} avg_deg={params['average_degree']}"
        + (f" maxk={params['max_degree']}" if params.get("max_degree") is not None else "")
    )
    return DatasetBundle(
        name=label,
        layers=layers,
        ground_truth=ground_truth,
        summary=summary,
    )


def _validate_mlfr_params(params: Dict[str, Any]) -> Dict[str, Any]:
    network_type = str(params.get("network_type", "UU")).upper()
    if network_type not in {"UU"}:
        raise ValueError("mLFR 当前仅接入 UU（无向无权）网络类型")

    validated = {
        "network_type": network_type,
        "n": int(params["n"]),
        "avg": float(params["avg"]),
        "max": int(params["max"]),
        "mix": float(params["mix"]),
        "tau1": float(params["tau1"]),
        "tau2": float(params["tau2"]),
        "mincom": int(params["mincom"]),
        "maxcom": int(params["maxcom"]),
        "l": int(params["l"]),
        "dc": float(params.get("dc", 0.0)),
        "rc": float(params.get("rc", 0.0)),
        "mparam1": float(params.get("mparam1", 2.0)),
        "on": int(params.get("on", 0)),
        "om": int(params.get("om", 0)),
    }

    if validated["n"] < 10:
        raise ValueError("mLFR 参数错误: n 必须 >= 10")
    if validated["avg"] <= 0:
        raise ValueError("mLFR 参数错误: avg 必须 > 0")
    if validated["max"] <= 0:
        raise ValueError("mLFR 参数错误: max 必须 > 0")
    if validated["avg"] >= validated["n"] or validated["max"] >= validated["n"]:
        raise ValueError("mLFR 参数错误: avg 和 max 必须小于 n")
    if validated["avg"] > validated["max"]:
        raise ValueError("mLFR 参数错误: avg 不能大于 max")
    if not 0.0 <= validated["mix"] <= 1.0:
        raise ValueError("mLFR 参数错误: mix 必须在 [0, 1] 范围内")
    if validated["tau1"] <= 0.0 or validated["tau2"] <= 0.0:
        raise ValueError("mLFR 参数错误: tau1 和 tau2 必须 > 0")
    if validated["mincom"] <= 0 or validated["maxcom"] <= 0:
        raise ValueError("mLFR 参数错误: mincom 和 maxcom 必须 > 0")
    if validated["mincom"] > validated["maxcom"]:
        raise ValueError("mLFR 参数错误: mincom 不能大于 maxcom")
    if validated["l"] < 2:
        raise ValueError("mLFR 参数错误: 层数 l 必须 >= 2")
    if not 0.0 <= validated["dc"] <= 1.0:
        raise ValueError("mLFR 参数错误: dc 必须在 [0, 1] 范围内")
    if not 0.0 <= validated["rc"] <= 1.0:
        raise ValueError("mLFR 参数错误: rc 必须在 [0, 1] 范围内")
    if validated["mparam1"] <= 0.0:
        raise ValueError("mLFR 参数错误: mparam1 必须 > 0")
    if validated["on"] < 0 or validated["om"] < 0:
        raise ValueError("mLFR 参数错误: on 和 om 不能为负数")

    return validated


def _ensure_mlfr_bridge_compiled(root: Path) -> None:
    # mLFR 官方仓库是 Java 项目，这里用一个很小的桥接类绕开原始 GUI 启动逻辑。
    class_file = root / "tools" / "mlfr_bridge" / "classes" / "MlfrGenerate.class"
    if class_file.exists():
        return

    source_file = root / "tools" / "mlfr_bridge" / "MlfrGenerate.java"
    output_dir = root / "tools" / "mlfr_bridge" / "classes"
    output_dir.mkdir(parents=True, exist_ok=True)
    classpath = ";".join(
        [
            str(root / "tools" / "mLFR_app_v04" / "mLFR.jar"),
            str(root / "tools" / "mlfr_lib" / "commons-math-2.2.jar"),
            str(root / "tools" / "mlfr_lib" / "guava-r09.jar"),
        ]
    )
    subprocess.run(
        ["javac", "-cp", classpath, "-d", str(output_dir), str(source_file)],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _run_mlfr_generator(root: Path, params: Dict[str, Any], output_prefix: Path) -> None:
    # 官方 mLFR 生成器接收的是“键 值 键 值 ...”形式的命令行参数。
    _ensure_mlfr_bridge_compiled(root)
    classpath = ";".join(
        [
            str(root / "tools" / "mlfr_bridge" / "classes"),
            str(root / "tools" / "mLFR_app_v04" / "mLFR.jar"),
            str(root / "tools" / "mlfr_lib" / "commons-math-2.2.jar"),
            str(root / "tools" / "mlfr_lib" / "guava-r09.jar"),
        ]
    )
    args = [
        "java",
        "-Djava.awt.headless=true",
        "-cp",
        classpath,
        "MlfrGenerate",
        str(output_prefix),
        params["network_type"],
        "N",
        str(params["n"]),
        "AVG",
        str(params["avg"]),
        "MAX",
        str(params["max"]),
        "MIX",
        str(params["mix"]),
        "TAU1",
        str(params["tau1"]),
        "TAU2",
        str(params["tau2"]),
        "MINCOM",
        str(params["mincom"]),
        "MAXCOM",
        str(params["maxcom"]),
        "L",
        str(params["l"]),
        "DC",
        str(params["dc"]),
        "RC",
        str(params["rc"]),
        "MPARAM1",
        str(params["mparam1"]),
        "ON",
        str(params["on"]),
        "OM",
        str(params["om"]),
    ]
    subprocess.run(
        args,
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _load_mlfr_layers(params: Dict[str, Any], output_prefix: Path) -> List[nx.Graph]:
    # mLFR 会输出多个 Layer 文件，这里逐层读回成 NetworkX 图对象。
    layer_graphs: List[nx.Graph] = []
    node_ids = list(range(1, params["n"] + 1))

    for layer_index in range(1, params["l"] + 1):
        layer_path = output_prefix.parent / f"{output_prefix.name}_Layer{layer_index}_Network.txt"
        edges = pd.read_csv(layer_path, sep=r"\s+", header=None)
        graph = nx.Graph(layer=f"Layer{layer_index}")
        graph.add_nodes_from(node_ids)
        for row in edges.itertuples(index=False):
            graph.add_edge(int(row[0]), int(row[1]), weight=1.0)
        layer_graphs.append(graph)

    return layer_graphs


def _load_mlfr_ground_truth(params: Dict[str, Any], output_prefix: Path) -> Dict[int, int]:
    # 社区文件是“node_id community_id”格式，不是按社区聚合的列表格式。
    ground_truth: Dict[int, int] = {}

    if params["rc"] == 0:
        community_files = [output_prefix.parent / f"{output_prefix.name}_Community.txt"]
    else:
        community_files = [
            output_prefix.parent / f"{output_prefix.name}_Layer{layer_index}_Community.txt"
            for layer_index in range(1, params["l"] + 1)
        ]

    community_path = community_files[0]
    with community_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            node_id = int(parts[0])
            community_id = int(parts[1]) - 1
            ground_truth[node_id] = community_id

    return ground_truth


def load_mlfr_dataset(variant: Any = None) -> DatasetBundle:
    root = Path(__file__).resolve().parents[1]
    params = _validate_mlfr_params(variant or {})
    params_payload = json.dumps(params, sort_keys=True)
    dataset_id = hashlib.sha1(params_payload.encode("utf-8")).hexdigest()[:10]
    output_dir = root / "data" / "generated" / "mlfr" / dataset_id
    output_prefix = output_dir / "network"
    output_dir.mkdir(parents=True, exist_ok=True)

    expected_layer = output_dir / "network_Layer1_Network.txt"
    # 同一组参数生成出来的数据会缓存到 data/generated/mlfr，避免每次重复跑 Java 生成器。
    if not expected_layer.exists():
        try:
            _run_mlfr_generator(root, params, output_prefix)
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
            raise RuntimeError(f"mLFR 生成失败: {message}") from exc

    with (output_dir / "params.json").open("w", encoding="utf-8") as handle:
        json.dump(params, handle, ensure_ascii=False, indent=2)

    layers = _load_mlfr_layers(params, output_prefix)
    ground_truth = _load_mlfr_ground_truth(params, output_prefix)
    summary = (
        f"mLFR Benchmark | 层数={len(layers)} | 节点={params['n']} | "
        f"mix={params['mix']} dc={params['dc']} rc={params['rc']} | "
        f"边数=" + ",".join(str(layer.number_of_edges()) for layer in layers)
    )
    return DatasetBundle(
        name="mLFR Benchmark",
        layers=layers,
        ground_truth=ground_truth,
        summary=summary,
    )


def _biogrid_tab3_label(filename: str) -> str:
    base = Path(filename).name
    rest = base.removeprefix("BIOGRID-ORGANISM-")
    slug = rest.rsplit("-", 2)[0] if rest else rest
    return slug.replace("_", " ")


def get_biogrid_species() -> List[Dict[str, str]]:
    # BioGRID：支持 data/BIOGRID-ORGANISM-LATEST.tab3.zip，或解压目录 data/BIOGRID-ORGANISM-LATEST.tab3/
    root = Path(__file__).resolve().parents[1]
    zip_path = root / "data" / "BIOGRID-ORGANISM-LATEST.tab3.zip"
    tab3_dir = root / "data" / "BIOGRID-ORGANISM-LATEST.tab3"
    species: List[Dict[str, str]] = []

    if zip_path.is_file():
        with zipfile.ZipFile(zip_path) as zf:
            for name in sorted(n for n in zf.namelist() if n.endswith(".txt") and not n.endswith("/")):
                basename = Path(name).name
                species.append({"member": basename, "label": _biogrid_tab3_label(basename)})
        return species

    if tab3_dir.is_dir():
        for path in sorted(tab3_dir.glob("BIOGRID-ORGANISM-*.tab3.txt")):
            species.append({"member": path.name, "label": _biogrid_tab3_label(path.name)})
        return species

    return []


def _coerce_opt_bool(value: Any, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


BIOGRID_MAX_LAYERS = 3


def _validate_biogrid_params(params: Dict[str, Any]) -> Dict[str, Any]:
    raw_member = params.get("member", "")
    member = "" if raw_member is None else str(raw_member).strip()
    member = Path(member).name
    species = get_biogrid_species()
    available_members = {item["member"] for item in species}
    if not member and species:
        member = species[0]["member"]
    if not available_members:
        raise ValueError(
            "未找到 BioGRID 数据：请将 BIOGRID-ORGANISM-LATEST.tab3.zip 或解压目录 "
            "data/BIOGRID-ORGANISM-LATEST.tab3/ 置于项目 data/ 下"
        )
    if member not in available_members:
        raise ValueError("BioGRID 参数错误: 选择的物种数据文件不可用，请从列表中重新选择")

    top_layers = int(params.get("top_layers", BIOGRID_MAX_LAYERS))
    top_layers = min(max(1, top_layers), BIOGRID_MAX_LAYERS)
    min_edges = int(params.get("min_edges", 12))
    max_nodes = int(params.get("max_nodes", 300))
    include_genetic = bool(params.get("include_genetic", True))

    if top_layers < 1:
        raise ValueError("BioGRID 参数错误: top_layers 必须 >= 1")
    if min_edges < 1:
        raise ValueError("BioGRID 参数错误: min_edges 必须 >= 1")
    if max_nodes < 20:
        raise ValueError("BioGRID 参数错误: max_nodes 必须 >= 20")

    auto_layers = _coerce_opt_bool(params.get("auto_layers"), True)

    return {
        "member": member,
        "top_layers": top_layers,
        "min_edges": min_edges,
        "max_nodes": max_nodes,
        "include_genetic": include_genetic,
        "auto_layers": auto_layers,
    }


def _infer_biogrid_layer_count(counts: List[int], max_layers: int, coverage_target: float = 0.82) -> tuple[int, float]:
    """按「去重边数」降序序列估计层数：取最小 k 使累计占比 >= coverage_target，且 k 不超过 max_layers。

    若仅一层已达标但第二层仍占总量 >= 4%，则至少取 2 层（在 max_layers 允许且存在时），便于多层实验。
    """
    if not counts:
        return 0, 0.0
    n = len(counts)
    total = sum(counts)
    if total <= 0:
        return 1, 0.0
    cap = max(1, min(max_layers, n))
    cum = 0
    k = cap
    for i in range(cap):
        cum += counts[i]
        if cum / total >= coverage_target:
            k = i + 1
            break
    else:
        k = cap
    k = min(k, cap)
    cov = sum(counts[:k]) / total
    if k == 1 and n >= 2 and cap >= 2 and counts[1] / total >= 0.04:
        k = 2
        cov = sum(counts[:k]) / total
    return max(1, k), cov


def load_biogrid_dataset(variant: Any = None) -> DatasetBundle:
    root = Path(__file__).resolve().parents[1]
    zip_path = root / "data" / "BIOGRID-ORGANISM-LATEST.tab3.zip"
    tab3_dir = root / "data" / "BIOGRID-ORGANISM-LATEST.tab3"

    params = _validate_biogrid_params(variant or {})
    species_map = {item["member"]: item["label"] for item in get_biogrid_species()}
    label = species_map[params["member"]]

    # 我们把 BioGRID 的 Experimental System 当作层标签，用它构造真实多层网络。
    edges_by_system: Dict[str, set[tuple[str, str]]] = defaultdict(set)
    all_nodes: set[str] = set()
    system_counter: Counter[str] = Counter()

    basename = params["member"]

    def _consume_rows(handle) -> None:
        reader = csv.DictReader(
            (line.decode("utf-8", errors="ignore") for line in handle),
            delimiter="\t",
        )
        for row in reader:
            exp_type = row["Experimental System Type"].strip()
            if not params["include_genetic"] and exp_type == "genetic":
                continue
            system = row["Experimental System"].strip()
            if not system or system == "-":
                continue
            source = row["Official Symbol Interactor A"].strip() or row["BioGRID ID Interactor A"].strip()
            target = row["Official Symbol Interactor B"].strip() or row["BioGRID ID Interactor B"].strip()
            if not source or not target or source == target:
                continue
            edge = tuple(sorted((source, target)))
            edges_by_system[system].add(edge)
            system_counter[system] += 1
            all_nodes.add(source)
            all_nodes.add(target)

    if zip_path.is_file():
        with zipfile.ZipFile(zip_path) as zf:
            inner = next((n for n in zf.namelist() if Path(n).name == basename), None)
            if inner is None:
                raise FileNotFoundError(f"BioGRID 压缩包中未找到: {basename}")
            with zf.open(inner) as handle:
                _consume_rows(handle)
    else:
        loose = tab3_dir / basename
        if not loose.is_file():
            raise FileNotFoundError(
                f"未找到 BioGRID 文件: {loose}（请确认已下载或解压 tab3 数据）"
            )
        with loose.open("rb") as handle:
            _consume_rows(handle)

    def _pick_layers() -> tuple[List[str], str]:
        """按去重边数排序；支持自动层数（覆盖率阈值）或固定取前 top_layers 层。"""
        min_e = params["min_edges"]
        top_l = params["top_layers"]
        auto = params.get("auto_layers", False)

        ranked = sorted(
            edges_by_system.keys(),
            key=lambda s: len(edges_by_system[s]),
            reverse=True,
        )
        strict = [s for s in ranked if len(edges_by_system[s]) >= min_e]
        if strict:
            base = strict
            relaxed = False
        else:
            base = [s for s in ranked if len(edges_by_system[s]) >= 1]
            relaxed = True

        if not base:
            return [], ""

        counts = [len(edges_by_system[s]) for s in base]

        if auto:
            k, cov = _infer_biogrid_layer_count(counts, max_layers=top_l)
            selected = base[:k]
            parts = [
                f"自动层数={k}（所选层合计覆盖约 {cov:.0%} 的层内去重边；目标覆盖率 82%；上限 max_layers={top_l}）"
            ]
            if cov < 0.78 and k >= top_l:
                parts.append("（已达层数上限，覆盖率可能低于目标，可调高「最大层数」）")
            if relaxed:
                thinnest = min(len(edges_by_system[s]) for s in selected) if selected else 0
                parts.insert(
                    0,
                    f"min_edges={min_e} 时无层达阈值，已用全部有边系统参与推断（最薄候选层约 {thinnest} 条去重边）。",
                )
            return selected, "".join(parts)

        selected = base[:top_l]
        if relaxed:
            thinnest = min(len(edges_by_system[s]) for s in selected) if selected else 0
            note = (
                f"min_edges={min_e} 时无实验系统层达到该阈值，已自动选取去重边数最多的 {len(selected)} 层"
                f"（最薄层约 {thinnest} 条边）；可在前端调低「每层最少边数」以匹配预期筛选。"
            )
            return selected, note
        return selected, ""

    selected_systems, layer_note = _pick_layers()

    if not selected_systems:
        hint = ""
        if not edges_by_system:
            hint = " 未解析到任何互作行：可尝试勾选「包含 genetic 类型互作」，或确认 tab3 文件完整。"
        else:
            hint = f" 当前 min_edges={params['min_edges']}；可调低该值或增大 top_layers。"
        raise ValueError("BioGRID 数据集中没有满足条件的实验系统层。" + hint)

    # 仅使用「选中层」上出现过的边的端点作为顶点集。若用全文件 all_nodes 铺层，
    # 则大量节点在选中层上无边、聚合度为 0，max_nodes 截断时会被零度节点占满，子图截取失效。
    union_nodes: set[str] = set()
    for system in selected_systems:
        for u, v in edges_by_system[system]:
            union_nodes.add(u)
            union_nodes.add(v)

    layer_graphs: List[nx.Graph] = []
    for system in selected_systems:
        graph = nx.Graph(layer=system)
        graph.add_nodes_from(union_nodes)
        for source, target in edges_by_system[system]:
            graph.add_edge(source, target, weight=1.0)
        layer_graphs.append(graph)

    aggregate = nx.Graph()
    aggregate.add_nodes_from(union_nodes)
    for graph in layer_graphs:
        aggregate.add_edges_from(graph.edges())

    # BioGRID 某些物种规模极大，这里截取高连接节点构成的真实子图，保证实验能跑完。
    active_nodes = [n for n, d in aggregate.degree() if d > 0]
    if len(active_nodes) > params["max_nodes"]:
        degree_order = sorted(
            ((n, aggregate.degree[n]) for n in active_nodes),
            key=lambda item: (-item[1], item[0]),
        )
        kept_nodes = {node for node, _ in degree_order[: params["max_nodes"]]}
        layer_graphs = [graph.subgraph(kept_nodes).copy() for graph in layer_graphs]
        final_nodes: set[str] = kept_nodes
        trunc_note = f" | 已按聚合度截断 {len(union_nodes)}→{len(final_nodes)}"
    else:
        final_nodes = union_nodes
        trunc_note = ""

    summary = (
        f"BioGRID {label} | 层数={len(layer_graphs)} | 节点={len(final_nodes)} | "
        + " ".join(f"{g.graph['layer']}={g.number_of_edges()}" for g in layer_graphs)
        + f" | max_nodes={params['max_nodes']}"
        + trunc_note
        + (f" | {layer_note}" if layer_note else "")
    )
    return DatasetBundle(
        name=f"BioGRID {label}",
        layers=layer_graphs,
        ground_truth=None,
        summary=summary,
    )
