"""
FastAPI 后端应用。

对外提供两类能力：
1. 读取内置数据集或用户上传图文件；
2. 执行社区检测与结果可视化。
"""

from __future__ import annotations

import math
import os
from pathlib import Path
import tempfile
from datetime import datetime
import re
from typing import Any, Dict, List, Optional

import networkx as nx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sklearn.metrics import normalized_mutual_info_score

from .data_processor import DataProcessor
from .experiment_datasets import LFR_PRESETS, get_biogrid_species, load_dataset
from .pmcdm import (
    CloudServer1,
    CloudServer2,
    PMCDMExperiment,
    SLouvain,
    TerminalClient,
    communities_to_groups,
    modularity_density,
    partition_to_labels,
)
from .visualization import Visualizer

app = FastAPI(
    title="Privacy Community Detection API",
    description="基于隐私保护的多层网络社区检测系统",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALGORITHMS = [
    "S-Louvain",
    "PD-Louvain",
    "R-Louvain",
    "DP-Louvain",
    "K-Louvain",
    "DH-Louvain",
]


def _slugify_filename(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return text.strip("._") or "visualization"


def _build_output_image_path(dataset_name: str, algorithm: str) -> Path:
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = _slugify_filename(f"{dataset_name}_{algorithm}_{timestamp}.png")
    return output_dir / filename


def _parse_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _ensure_algorithm(name: str) -> str:
    if name not in ALGORITHMS:
        raise HTTPException(status_code=400, detail=f"不支持的算法: {name}")
    return name


def _safe_float(value: Optional[str], default: float) -> float:
    if value in (None, ""):
        return default
    return float(value)


def _safe_int(value: Optional[str], default: int) -> int:
    if value in (None, ""):
        return default
    return int(value)


def _aggregate_layers(layers: List[nx.Graph]) -> nx.Graph:
    aggregate = nx.Graph()
    for layer in layers:
        aggregate.add_nodes_from(layer.nodes())
        for u, v, data in layer.edges(data=True):
            weight = float(data.get("weight", 1.0))
            if aggregate.has_edge(u, v):
                aggregate[u][v]["weight"] += weight
            else:
                aggregate.add_edge(u, v, weight=weight)
    return aggregate


def _graph_statistics(graph: nx.Graph) -> Dict[str, Any]:
    if graph.number_of_nodes() == 0:
        return {
            "num_nodes": 0,
            "num_edges": 0,
            "density": 0.0,
            "is_connected": False,
            "num_components": 0,
            "avg_degree": 0.0,
        }
    return DataProcessor.graph_statistics(graph)


def _serialize_metric(value: float) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return float(value)


def _run_single_algorithm(
    layers: List[nx.Graph],
    gt_labels: Optional[Dict[Any, int]],
    algorithm: str,
    experiment: PMCDMExperiment,
    lambd: float,
) -> tuple[Dict[Any, int], Dict[str, Any]]:
    perturbation_mode = {
        "S-Louvain": "none",
        "PD-Louvain": "none",
        "R-Louvain": "random",
        "DP-Louvain": "dp",
        "K-Louvain": "k-anon",
        "DH-Louvain": "dp",
    }[algorithm]
    use_he = algorithm in {"PD-Louvain", "DH-Louvain"}
    use_dh_framework = algorithm in {"PD-Louvain", "DH-Louvain"}

    cloud1 = CloudServer1(experiment.epsilon, experiment.delta, experiment.key_size)
    terminal = TerminalClient(cloud1.he)

    processed_layers: List[nx.Graph] = []
    for layer in layers:
        uploaded = terminal.encrypt_upload(layer) if use_he else layer.copy()
        processed_layers.append(cloud1.perturb_layer(uploaded, mode=perturbation_mode))

    if use_dh_framework:
        cloud2 = CloudServer2(cloud1, random_state=experiment.random_state)
        communities = cloud2.run_dh_louvain(processed_layers, lambd=lambd)
    else:
        communities = SLouvain(random_state=experiment.random_state).detect(processed_layers)

    nodes = sorted(layers[0].nodes())
    pred = partition_to_labels(communities, nodes)
    nmi = float("nan")
    if gt_labels is not None:
        gt = partition_to_labels(gt_labels, nodes)
        nmi = normalized_mutual_info_score(gt, pred)

    metric_graph = processed_layers[0]
    groups = list(communities_to_groups(communities).values())
    modularity = nx.algorithms.community.modularity(metric_graph, groups, weight="weight")
    module_density = modularity_density(metric_graph, communities)
    pe = cloud1.preserved_edges / max(1, cloud1.total_edges)
    pw = 1.0 if use_he else 0.0

    row = {
        "algorithm": algorithm,
        "modularity": float(modularity),
        "module_density": float(module_density),
        "nmi": _serialize_metric(nmi),
        "privacy_rate": float((pe + pw) / 2.0),
        "num_communities": len(set(communities.values())),
    }
    return communities, row


def _build_upload_bundle(file_path: str, filename: str, random_state: int) -> Dict[str, Any]:
    graph = DataProcessor.read_dataset(file_path)
    layers = PMCDMExperiment.build_multiplex_from_base(graph, layers=3, seed=random_state)
    summary = (
        f"Uploaded Dataset | 文件={filename} | 层数={len(layers)} | "
        f"节点={graph.number_of_nodes()} | 边={graph.number_of_edges()}"
    )
    return {
        "name": filename,
        "layers": layers,
        "ground_truth": None,
        "summary": summary,
    }


def _build_builtin_variant(
    dataset_name: str,
    *,
    lfr_preset: Optional[str],
    lfr_custom_enabled: bool,
    lfr_n: Optional[str],
    lfr_tau1: Optional[str],
    lfr_tau2: Optional[str],
    lfr_mu: Optional[str],
    lfr_average_degree: Optional[str],
    lfr_min_community: Optional[str],
    lfr_max_community: Optional[str],
    lfr_max_iters: Optional[str],
    mlfr_network_type: Optional[str],
    mlfr_n: Optional[str],
    mlfr_avg: Optional[str],
    mlfr_max: Optional[str],
    mlfr_mix: Optional[str],
    mlfr_tau1: Optional[str],
    mlfr_tau2: Optional[str],
    mlfr_mincom: Optional[str],
    mlfr_maxcom: Optional[str],
    mlfr_l: Optional[str],
    mlfr_dc: Optional[str],
    mlfr_rc: Optional[str],
    mlfr_mparam1: Optional[str],
    mlfr_on: Optional[str],
    mlfr_om: Optional[str],
    biogrid_member: Optional[str],
    biogrid_top_layers: Optional[str],
    biogrid_min_edges: Optional[str],
    biogrid_max_nodes: Optional[str],
    biogrid_include_genetic: Optional[str],
) -> Any:
    if dataset_name == "lfr":
        if not lfr_custom_enabled:
            return lfr_preset or "small_easy"
        return {
            "n": _safe_int(lfr_n, 40),
            "tau1": _safe_float(lfr_tau1, 2.5),
            "tau2": _safe_float(lfr_tau2, 1.5),
            "mu": _safe_float(lfr_mu, 0.1),
            "average_degree": _safe_int(lfr_average_degree, 6),
            "min_community": _safe_int(lfr_min_community, 10),
            "max_community": _safe_int(lfr_max_community, 20),
            "max_iters": _safe_int(lfr_max_iters, 10000),
        }
    if dataset_name == "mlfr":
        return {
            "network_type": (mlfr_network_type or "UU").strip().upper() or "UU",
            "n": _safe_int(mlfr_n, 40),
            "avg": _safe_float(mlfr_avg, 6.0),
            "max": _safe_int(mlfr_max, 12),
            "mix": _safe_float(mlfr_mix, 0.1),
            "tau1": _safe_float(mlfr_tau1, 2.5),
            "tau2": _safe_float(mlfr_tau2, 1.5),
            "mincom": _safe_int(mlfr_mincom, 10),
            "maxcom": _safe_int(mlfr_maxcom, 20),
            "l": _safe_int(mlfr_l, 3),
            "dc": _safe_float(mlfr_dc, 0.0),
            "rc": _safe_float(mlfr_rc, 0.0),
            "mparam1": _safe_float(mlfr_mparam1, 2.0),
            "on": _safe_int(mlfr_on, 0),
            "om": _safe_int(mlfr_om, 0),
        }
    if dataset_name == "biogrid":
        return {
            "member": (biogrid_member or "").strip(),
            "top_layers": _safe_int(biogrid_top_layers, 3),
            "min_edges": _safe_int(biogrid_min_edges, 20),
            "max_nodes": _safe_int(biogrid_max_nodes, 300),
            "include_genetic": _parse_bool(biogrid_include_genetic, True),
        }
    return None


def _load_bundle(
    source_type: str,
    *,
    file: Optional[UploadFile],
    random_state: int,
    dataset_name: str,
    variant: Any,
) -> Dict[str, Any]:
    if source_type == "upload":
        if file is None:
            raise HTTPException(status_code=400, detail="上传模式下必须提供文件")
        suffix = Path(file.filename or "graph.txt").suffix or ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file.file.read())
            temp_path = tmp.name
        try:
            return _build_upload_bundle(temp_path, file.filename or "uploaded_graph", random_state)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    try:
        bundle = load_dataset(dataset_name, variant=variant)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "name": bundle.name,
        "layers": bundle.layers,
        "ground_truth": bundle.ground_truth,
        "summary": bundle.summary,
    }


def _bundle_payload(bundle: Dict[str, Any]) -> Dict[str, Any]:
    aggregate = _aggregate_layers(bundle["layers"])
    return {
        "dataset": {
            "name": bundle["name"],
            "summary": bundle["summary"],
            "num_layers": len(bundle["layers"]),
            "layer_info": [
                {
                    "name": layer.graph.get("layer", f"Layer {index + 1}"),
                    "num_nodes": layer.number_of_nodes(),
                    "num_edges": layer.number_of_edges(),
                }
                for index, layer in enumerate(bundle["layers"])
            ],
        },
        "graph_info": _graph_statistics(aggregate),
    }


@app.get("/")
async def root():
    return {"message": "Privacy Community Detection API"}


@app.get("/datasets")
async def dataset_catalog():
    try:
        species = get_biogrid_species()
    except FileNotFoundError:
        species = []

    return {
        "datasets": [
            {"id": "karate", "label": "Karate Club", "source": "builtin"},
            {"id": "aucs", "label": "AUCS", "source": "builtin"},
            {"id": "mlfr", "label": "mLFR Benchmark", "source": "builtin"},
            {"id": "lfr", "label": "LFR Benchmark", "source": "builtin"},
            {"id": "biogrid", "label": "BioGRID", "source": "builtin"},
            {"id": "upload", "label": "上传自定义图文件", "source": "upload"},
        ],
        "algorithms": ALGORITHMS,
        "lfr_presets": [
            {"id": key, "label": value["label"], "params": value["params"]}
            for key, value in LFR_PRESETS.items()
        ],
        "biogrid_species": species,
        "defaults": {
            "dataset_name": "karate",
            "algorithm": "DH-Louvain",
            "epsilon": 1.0,
            "delta": 1e-5,
            "key_size": 512,
            "random_state": 42,
            "lambd": 0.5,
            "layout": "spring",
            "include_benchmark": True,
        },
    }


@app.post("/detect")
async def detect_communities(
    source_type: str = Form("builtin"),
    dataset_name: str = Form("karate"),
    algorithm: str = Form("DH-Louvain"),
    epsilon: float = Form(1.0),
    delta: float = Form(1e-5),
    key_size: int = Form(512),
    random_state: int = Form(42),
    lambd: float = Form(0.5),
    include_benchmark: str = Form("true"),
    lfr_preset: str = Form("small_easy"),
    lfr_custom_enabled: str = Form("false"),
    lfr_n: Optional[str] = Form(None),
    lfr_tau1: Optional[str] = Form(None),
    lfr_tau2: Optional[str] = Form(None),
    lfr_mu: Optional[str] = Form(None),
    lfr_average_degree: Optional[str] = Form(None),
    lfr_min_community: Optional[str] = Form(None),
    lfr_max_community: Optional[str] = Form(None),
    lfr_max_iters: Optional[str] = Form(None),
    mlfr_network_type: Optional[str] = Form("UU"),
    mlfr_n: Optional[str] = Form(None),
    mlfr_avg: Optional[str] = Form(None),
    mlfr_max: Optional[str] = Form(None),
    mlfr_mix: Optional[str] = Form(None),
    mlfr_tau1: Optional[str] = Form(None),
    mlfr_tau2: Optional[str] = Form(None),
    mlfr_mincom: Optional[str] = Form(None),
    mlfr_maxcom: Optional[str] = Form(None),
    mlfr_l: Optional[str] = Form(None),
    mlfr_dc: Optional[str] = Form(None),
    mlfr_rc: Optional[str] = Form(None),
    mlfr_mparam1: Optional[str] = Form(None),
    mlfr_on: Optional[str] = Form(None),
    mlfr_om: Optional[str] = Form(None),
    biogrid_member: Optional[str] = Form(None),
    biogrid_top_layers: Optional[str] = Form(None),
    biogrid_min_edges: Optional[str] = Form(None),
    biogrid_max_nodes: Optional[str] = Form(None),
    biogrid_include_genetic: Optional[str] = Form("true"),
    file: Optional[UploadFile] = File(None),
):
    algorithm = _ensure_algorithm(algorithm)
    variant = _build_builtin_variant(
        dataset_name,
        lfr_preset=lfr_preset,
        lfr_custom_enabled=_parse_bool(lfr_custom_enabled),
        lfr_n=lfr_n,
        lfr_tau1=lfr_tau1,
        lfr_tau2=lfr_tau2,
        lfr_mu=lfr_mu,
        lfr_average_degree=lfr_average_degree,
        lfr_min_community=lfr_min_community,
        lfr_max_community=lfr_max_community,
        lfr_max_iters=lfr_max_iters,
        mlfr_network_type=mlfr_network_type,
        mlfr_n=mlfr_n,
        mlfr_avg=mlfr_avg,
        mlfr_max=mlfr_max,
        mlfr_mix=mlfr_mix,
        mlfr_tau1=mlfr_tau1,
        mlfr_tau2=mlfr_tau2,
        mlfr_mincom=mlfr_mincom,
        mlfr_maxcom=mlfr_maxcom,
        mlfr_l=mlfr_l,
        mlfr_dc=mlfr_dc,
        mlfr_rc=mlfr_rc,
        mlfr_mparam1=mlfr_mparam1,
        mlfr_on=mlfr_on,
        mlfr_om=mlfr_om,
        biogrid_member=biogrid_member,
        biogrid_top_layers=biogrid_top_layers,
        biogrid_min_edges=biogrid_min_edges,
        biogrid_max_nodes=biogrid_max_nodes,
        biogrid_include_genetic=biogrid_include_genetic,
    )
    bundle = _load_bundle(
        source_type,
        file=file,
        random_state=random_state,
        dataset_name=dataset_name,
        variant=variant,
    )

    experiment = PMCDMExperiment(
        epsilon=epsilon,
        delta=delta,
        key_size=key_size,
        random_state=random_state,
    )
    communities, selected_result = _run_single_algorithm(
        bundle["layers"],
        bundle["ground_truth"],
        algorithm,
        experiment,
        lambd,
    )

    benchmark_rows = None
    if _parse_bool(include_benchmark, True):
        benchmark_rows = []
        for algo in ALGORITHMS:
            _, row = _run_single_algorithm(
                bundle["layers"],
                bundle["ground_truth"],
                algo,
                experiment,
                lambd,
            )
            benchmark_rows.append(row)

    payload = _bundle_payload(bundle)
    payload.update(
        {
            "selected_algorithm": algorithm,
            "statistics": selected_result,
            "benchmark": benchmark_rows,
            "communities": {str(node): int(group) for node, group in communities.items()},
        }
    )
    return payload


@app.post("/visualize")
async def visualize_results(
    source_type: str = Form("builtin"),
    dataset_name: str = Form("karate"),
    algorithm: str = Form("DH-Louvain"),
    epsilon: float = Form(1.0),
    delta: float = Form(1e-5),
    key_size: int = Form(512),
    random_state: int = Form(42),
    lambd: float = Form(0.5),
    layout: str = Form("spring"),
    lfr_preset: str = Form("small_easy"),
    lfr_custom_enabled: str = Form("false"),
    lfr_n: Optional[str] = Form(None),
    lfr_tau1: Optional[str] = Form(None),
    lfr_tau2: Optional[str] = Form(None),
    lfr_mu: Optional[str] = Form(None),
    lfr_average_degree: Optional[str] = Form(None),
    lfr_min_community: Optional[str] = Form(None),
    lfr_max_community: Optional[str] = Form(None),
    lfr_max_iters: Optional[str] = Form(None),
    mlfr_network_type: Optional[str] = Form("UU"),
    mlfr_n: Optional[str] = Form(None),
    mlfr_avg: Optional[str] = Form(None),
    mlfr_max: Optional[str] = Form(None),
    mlfr_mix: Optional[str] = Form(None),
    mlfr_tau1: Optional[str] = Form(None),
    mlfr_tau2: Optional[str] = Form(None),
    mlfr_mincom: Optional[str] = Form(None),
    mlfr_maxcom: Optional[str] = Form(None),
    mlfr_l: Optional[str] = Form(None),
    mlfr_dc: Optional[str] = Form(None),
    mlfr_rc: Optional[str] = Form(None),
    mlfr_mparam1: Optional[str] = Form(None),
    mlfr_on: Optional[str] = Form(None),
    mlfr_om: Optional[str] = Form(None),
    biogrid_member: Optional[str] = Form(None),
    biogrid_top_layers: Optional[str] = Form(None),
    biogrid_min_edges: Optional[str] = Form(None),
    biogrid_max_nodes: Optional[str] = Form(None),
    biogrid_include_genetic: Optional[str] = Form("true"),
    file: Optional[UploadFile] = File(None),
):
    algorithm = _ensure_algorithm(algorithm)
    variant = _build_builtin_variant(
        dataset_name,
        lfr_preset=lfr_preset,
        lfr_custom_enabled=_parse_bool(lfr_custom_enabled),
        lfr_n=lfr_n,
        lfr_tau1=lfr_tau1,
        lfr_tau2=lfr_tau2,
        lfr_mu=lfr_mu,
        lfr_average_degree=lfr_average_degree,
        lfr_min_community=lfr_min_community,
        lfr_max_community=lfr_max_community,
        lfr_max_iters=lfr_max_iters,
        mlfr_network_type=mlfr_network_type,
        mlfr_n=mlfr_n,
        mlfr_avg=mlfr_avg,
        mlfr_max=mlfr_max,
        mlfr_mix=mlfr_mix,
        mlfr_tau1=mlfr_tau1,
        mlfr_tau2=mlfr_tau2,
        mlfr_mincom=mlfr_mincom,
        mlfr_maxcom=mlfr_maxcom,
        mlfr_l=mlfr_l,
        mlfr_dc=mlfr_dc,
        mlfr_rc=mlfr_rc,
        mlfr_mparam1=mlfr_mparam1,
        mlfr_on=mlfr_on,
        mlfr_om=mlfr_om,
        biogrid_member=biogrid_member,
        biogrid_top_layers=biogrid_top_layers,
        biogrid_min_edges=biogrid_min_edges,
        biogrid_max_nodes=biogrid_max_nodes,
        biogrid_include_genetic=biogrid_include_genetic,
    )
    bundle = _load_bundle(
        source_type,
        file=file,
        random_state=random_state,
        dataset_name=dataset_name,
        variant=variant,
    )

    experiment = PMCDMExperiment(
        epsilon=epsilon,
        delta=delta,
        key_size=key_size,
        random_state=random_state,
    )
    communities, _ = _run_single_algorithm(
        bundle["layers"],
        bundle["ground_truth"],
        algorithm,
        experiment,
        lambd,
    )
    graph = _aggregate_layers(bundle["layers"])

    visualizer = Visualizer()
    output_path = _build_output_image_path(bundle["name"], algorithm)

    visualizer.visualize_communities(
        graph,
        communities,
        title=f"{bundle['name']} | {algorithm}",
        output_path=str(output_path),
        layout=layout,
    )
    return FileResponse(str(output_path), media_type="image/png", filename=output_path.name)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
