"""Core services behind the deployable backend framework."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import networkx as nx
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from ..data_processor import DataProcessor
from ..experiment_datasets import BIOGRID_MAX_LAYERS, LFR_PRESETS, get_biogrid_species, load_dataset
from ..pmcdm import (
    CloudServer1,
    CloudServer2,
    PMCDMExperiment,
    SLouvain,
    TerminalClient,
    communities_to_groups,
    modularity_density,
    nmi_score,
    partition_to_labels,
    reference_labels_slouvain,
)
from ..visualization import Visualizer
from .ea_schema import EAOptimizeRequest
from .models import ComponentDescriptor

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
    root = Path(__file__).resolve().parents[2]
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


def _safe_float(value: Optional[str], default: float) -> float:
    if value in (None, ""):
        return default
    return float(value)


def _safe_int(value: Optional[str], default: int) -> int:
    if value in (None, ""):
        return default
    return int(value)


def _serialize_metric(value: float) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return float(value)


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


class LocalMultilayerSystemService:
    """Local service responsible for datasets, aggregation and visualization."""

    @staticmethod
    def graph_statistics(graph: nx.Graph) -> Dict[str, Any]:
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

    @staticmethod
    def build_upload_bundle(file_path: str, filename: str, random_state: int) -> Dict[str, Any]:
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

    @staticmethod
    def build_builtin_variant(dataset_name: str, form: Dict[str, Any]) -> Any:
        if dataset_name == "lfr":
            if not _parse_bool(form.get("lfr_custom_enabled"), False):
                return form.get("lfr_preset") or "bench500"
            out = {
                "n": _safe_int(form.get("lfr_n"), 500),
                "tau1": _safe_float(form.get("lfr_tau1"), 2.0),
                "tau2": _safe_float(form.get("lfr_tau2"), 1.5),
                "mu": _safe_float(form.get("lfr_mu"), 0.25),
                "average_degree": _safe_int(form.get("lfr_average_degree"), 10),
                "min_community": _safe_int(form.get("lfr_min_community"), 20),
                "max_community": _safe_int(form.get("lfr_max_community"), 50),
                "max_iters": _safe_int(form.get("lfr_max_iters"), 15000),
                "multiplex_layers": _safe_int(form.get("lfr_multiplex_layers"), 3),
            }
            if form.get("lfr_max_degree") not in (None, ""):
                out["max_degree"] = _safe_int(form.get("lfr_max_degree"), 40)
            return out
        if dataset_name == "mlfr":
            return {
                "network_type": (form.get("mlfr_network_type") or "UU").strip().upper() or "UU",
                "n": _safe_int(form.get("mlfr_n"), 40),
                "avg": _safe_float(form.get("mlfr_avg"), 6.0),
                "max": _safe_int(form.get("mlfr_max"), 12),
                "mix": _safe_float(form.get("mlfr_mix"), 0.1),
                "tau1": _safe_float(form.get("mlfr_tau1"), 2.5),
                "tau2": _safe_float(form.get("mlfr_tau2"), 1.5),
                "mincom": _safe_int(form.get("mlfr_mincom"), 10),
                "maxcom": _safe_int(form.get("mlfr_maxcom"), 20),
                "l": _safe_int(form.get("mlfr_l"), 3),
                "dc": _safe_float(form.get("mlfr_dc"), 0.0),
                "rc": _safe_float(form.get("mlfr_rc"), 0.0),
                "mparam1": _safe_float(form.get("mlfr_mparam1"), 2.0),
                "on": _safe_int(form.get("mlfr_on"), 0),
                "om": _safe_int(form.get("mlfr_om"), 0),
            }
        if dataset_name == "biogrid":
            return {
                "member": (form.get("biogrid_member") or "").strip(),
                "top_layers": min(
                    BIOGRID_MAX_LAYERS,
                    max(1, _safe_int(form.get("biogrid_top_layers"), BIOGRID_MAX_LAYERS)),
                ),
                "min_edges": _safe_int(form.get("biogrid_min_edges"), 12),
                "max_nodes": _safe_int(form.get("biogrid_max_nodes"), 300),
                "include_genetic": _parse_bool(form.get("biogrid_include_genetic"), True),
                "auto_layers": _parse_bool(form.get("biogrid_auto_layers"), True),
            }
        return None

    def load_bundle(
        self,
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
                return self.build_upload_bundle(temp_path, file.filename or "uploaded_graph", random_state)
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

    def bundle_payload(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
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
            "graph_info": self.graph_statistics(aggregate),
        }

    def render_visualization(
        self,
        bundle: Dict[str, Any],
        communities: Dict[Any, int],
        *,
        algorithm: str,
        layout: str,
    ) -> FileResponse:
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

    def build_interactive_3d_payload(
        self,
        graph: nx.Graph,
        communities: Dict[Any, int],
        *,
        random_state: int,
    ) -> Dict[str, Any]:
        if graph.number_of_nodes() == 0:
            return {"nodes": [], "edges": [], "community_ids": []}

        positions = nx.spring_layout(graph, dim=3, k=0.7, iterations=100, seed=random_state)
        degrees = dict(graph.degree())
        max_degree = max(degrees.values(), default=1)
        top_degree_nodes = {
            node
            for node, _ in sorted(degrees.items(), key=lambda item: (-item[1], str(item[0])))[: min(18, len(degrees))]
        }

        nodes = []
        for node in graph.nodes():
            community = int(communities.get(node, -1))
            position = positions[node]
            nodes.append(
                {
                    "id": str(node),
                    "x": float(position[0]),
                    "y": float(position[1]),
                    "z": float(position[2]),
                    "community": community,
                    "degree": int(degrees.get(node, 0)),
                    "size": float(7.0 + 11.0 * degrees.get(node, 0) / max(1, max_degree)),
                    "label": str(node) if node in top_degree_nodes else "",
                }
            )

        edges = []
        for source, target in graph.edges():
            edges.append(
                {
                    "source": str(source),
                    "target": str(target),
                    "weight": float(graph[source][target].get("weight", 1.0)),
                    "source_pos": [float(value) for value in positions[source]],
                    "target_pos": [float(value) for value in positions[target]],
                }
            )

        return {
            "nodes": nodes,
            "edges": edges,
            "community_ids": sorted({int(comm) for comm in communities.values()}),
        }

    def build_multilayer_3d_payload(
        self,
        layers: List[nx.Graph],
        communities: Dict[Any, int],
        *,
        random_state: int,
    ) -> Dict[str, Any]:
        if not layers:
            return {
                "mode": "multilayer",
                "layer_names": [],
                "nodes": [],
                "intra_edges": [],
                "interlayer_edges": [],
                "community_ids": [],
            }

        aggregate = _aggregate_layers(layers)
        if aggregate.number_of_nodes() == 0:
            return {
                "mode": "multilayer",
                "layer_names": [],
                "nodes": [],
                "intra_edges": [],
                "interlayer_edges": [],
                "community_ids": [],
            }

        base_positions = nx.spring_layout(aggregate, dim=2, k=0.8, iterations=120, seed=random_state)
        degrees = dict(aggregate.degree())
        max_degree = max(degrees.values(), default=1)
        layer_gap = 1.8

        layer_names = [layer.graph.get("layer", f"Layer {index + 1}") for index, layer in enumerate(layers)]
        all_layer_nodes: List[Dict[str, Any]] = []
        intra_edges: List[Dict[str, Any]] = []
        interlayer_edges: List[Dict[str, Any]] = []
        nodes_by_layer: List[set[Any]] = [set(layer.nodes()) for layer in layers]

        for layer_index, layer in enumerate(layers):
            z_value = float(layer_index * layer_gap)
            layer_name = layer_names[layer_index]
            for node in sorted(layer.nodes(), key=str):
                position = base_positions.get(node, (0.0, 0.0))
                all_layer_nodes.append(
                    {
                        "id": f"{node}::{layer_index}",
                        "node_id": str(node),
                        "layer_index": layer_index,
                        "layer_name": layer_name,
                        "x": float(position[0]),
                        "y": float(position[1]),
                        "z": z_value,
                        "community": int(communities.get(node, -1)),
                        "degree": int(degrees.get(node, 0)),
                        "size": float(5.0 + 7.0 * degrees.get(node, 0) / max(1, max_degree)),
                    }
                )

            for source, target in layer.edges():
                source_pos = base_positions.get(source, (0.0, 0.0))
                target_pos = base_positions.get(target, (0.0, 0.0))
                intra_edges.append(
                    {
                        "layer_index": layer_index,
                        "layer_name": layer_name,
                        "source": str(source),
                        "target": str(target),
                        "source_pos": [float(source_pos[0]), float(source_pos[1]), z_value],
                        "target_pos": [float(target_pos[0]), float(target_pos[1]), z_value],
                    }
                )

        for layer_index in range(len(layers) - 1):
            shared_nodes = sorted(nodes_by_layer[layer_index] & nodes_by_layer[layer_index + 1], key=str)
            for node in shared_nodes:
                position = base_positions.get(node, (0.0, 0.0))
                interlayer_edges.append(
                    {
                        "node_id": str(node),
                        "source_layer_index": layer_index,
                        "target_layer_index": layer_index + 1,
                        "source_layer_name": layer_names[layer_index],
                        "target_layer_name": layer_names[layer_index + 1],
                        "source_pos": [float(position[0]), float(position[1]), float(layer_index * layer_gap)],
                        "target_pos": [float(position[0]), float(position[1]), float((layer_index + 1) * layer_gap)],
                    }
                )

        return {
            "mode": "multilayer",
            "layer_names": layer_names,
            "nodes": all_layer_nodes,
            "intra_edges": intra_edges,
            "interlayer_edges": interlayer_edges,
            "community_ids": sorted({int(comm) for comm in communities.values()}),
        }


class CloudServer1Service:
    """Adapter for the first cloud role inside the unified backend."""

    def __init__(self, epsilon: float, delta: float, key_size: int):
        self.runtime = CloudServer1(epsilon, delta, key_size)

    @property
    def he(self):
        return self.runtime.he

    @property
    def preserved_edges(self) -> float:
        return self.runtime.preserved_edges

    @property
    def total_edges(self) -> int:
        return self.runtime.total_edges

    def perturb_layer(self, graph: nx.Graph, mode: str) -> nx.Graph:
        return self.runtime.perturb_layer(graph, mode=mode)


class CloudServer2Service:
    """Adapter for the second cloud role inside the unified backend."""

    def __init__(self, cloud1: CloudServer1Service, random_state: int):
        self.runtime = CloudServer2(cloud1.runtime, random_state=random_state)

    def detect_communities(self, layer_graphs: List[nx.Graph], lambd: float) -> Dict[Any, int]:
        return self.runtime.run_dh_louvain(layer_graphs, lambd=lambd)


class IntegratedPMCDMBackend:
    """Single deployable backend framework integrating local and cloud roles."""

    def __init__(self):
        self.local_system = LocalMultilayerSystemService()
        self.components = [
            ComponentDescriptor(
                id="local-multilayer-system",
                name="本地多层系统",
                role="数据编排与可视化",
                responsibilities=[
                    "加载内置或上传数据集",
                    "构建多层网络与统计信息",
                    "生成静态图与交互式 3D 图",
                ],
            ),
            ComponentDescriptor(
                id="cloud-server-1",
                name="云服务器1",
                role="隐私扰动与加密处理",
                responsibilities=[
                    "执行差分隐私或 k-anon 扰动",
                    "模拟同态加密上传流程",
                    "统计边保留率与隐私相关指标",
                ],
            ),
            ComponentDescriptor(
                id="cloud-server-2",
                name="云服务器2",
                role="可信优化与社区检测",
                responsibilities=[
                    "执行 DH-Louvain 优化",
                    "统一调度多算法对比流程",
                    "输出社区划分与评价结果",
                ],
            ),
        ]

    def framework_overview(self) -> Dict[str, Any]:
        return {
            "name": "Integrated PMCDM Backend Framework",
            "deployment_mode": "single-service",
            "entrypoint": "src.backend:app",
            "components": [component.to_dict() for component in self.components],
            "routes": {
                "system": [
                    "/",
                    "/datasets",
                    "/framework/architecture",
                    "/optimize/ea",
                    "/api/optimize/ea",
                ],
                "pipeline": ["/detect", "/visualize", "/visualize3d"],
            },
        }

    def dataset_catalog(self) -> Dict[str, Any]:
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

    def ensure_algorithm(self, name: str) -> str:
        if name not in ALGORITHMS:
            raise HTTPException(status_code=400, detail=f"不支持的算法: {name}")
        return name

    def run_evolutionary_optimize(self, body: EAOptimizeRequest) -> Dict[str, Any]:
        """遗传算法搜索 epsilon、lambda 等，在加权适应度下优化隐私–效用折中。"""
        from ..evolutionary_optimizer import (
            EvolutionaryOptimizer,
            EvolutionaryOptimizerConfig,
            serialize_evolution_result,
        )

        form = dict(body.form)
        if str(form.get("source_type", "builtin")) == "upload":
            raise HTTPException(status_code=400, detail="进化优化暂仅支持内置数据集，请切换为内置数据后重试")

        dataset_name = str(form.get("dataset_name", "karate"))
        algorithm = self.ensure_algorithm(str(form.get("algorithm", "DH-Louvain")))
        evaluations_cap = body.population_size * body.generations
        if evaluations_cap > 250:
            raise HTTPException(
                status_code=400,
                detail="种群×代数不能超过 250（当前为 "
                + str(evaluations_cap)
                + "），请调小规模以免请求超时",
            )

        variant = self.local_system.build_builtin_variant(dataset_name, form)
        key_size = int(form.get("key_size", 512))
        delta = float(form.get("delta", 1e-5))
        random_state = int(form.get("random_state", 42))

        config = EvolutionaryOptimizerConfig(
            dataset_name=dataset_name,
            dataset_variant=variant,
            algorithm=algorithm,
            population_size=body.population_size,
            generations=body.generations,
            random_state=random_state,
            key_size=key_size,
            delta=delta,
        )
        optimizer = EvolutionaryOptimizer(config)
        result = optimizer.optimize()

        baseline = None
        if body.compare_baseline:
            baseline = optimizer._evaluate_candidate(
                {
                    "epsilon": float(form.get("epsilon", 1.0)),
                    "lambd": float(form.get("lambd", 0.5)),
                }
            )

        payload = serialize_evolution_result(result, baseline=baseline)
        if body.save_json:
            root = Path(__file__).resolve().parents[2]
            output_dir = root / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = output_dir / f"ea_optimize_{stamp}.json"
            with out_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            payload["saved_path"] = str(out_path)
        return payload

    def load_bundle_from_request(
        self,
        *,
        source_type: str,
        dataset_name: str,
        file: Optional[UploadFile],
        random_state: int,
        form: Dict[str, Any],
    ) -> Dict[str, Any]:
        variant = self.local_system.build_builtin_variant(dataset_name, form)
        return self.local_system.load_bundle(
            source_type,
            file=file,
            random_state=random_state,
            dataset_name=dataset_name,
            variant=variant,
        )

    def run_single_algorithm(
        self,
        *,
        layers: List[nx.Graph],
        gt_labels: Optional[Dict[Any, int]],
        algorithm: str,
        epsilon: float,
        delta: float,
        key_size: int,
        random_state: int,
        lambd: float,
        slouvain_ref_labels: Optional[List[int]] = None,
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

        cloud1 = CloudServer1Service(epsilon, delta, key_size)
        terminal = TerminalClient(cloud1.he)
        processed_layers: List[nx.Graph] = []
        for layer in layers:
            uploaded = terminal.encrypt_upload(layer) if use_he else layer.copy()
            processed_layers.append(cloud1.perturb_layer(uploaded, mode=perturbation_mode))

        if use_dh_framework:
            cloud2 = CloudServer2Service(cloud1, random_state=random_state)
            communities = cloud2.detect_communities(processed_layers, lambd=lambd)
        else:
            communities = SLouvain(random_state=random_state).detect(processed_layers)

        nodes = sorted(layers[0].nodes())
        pred = partition_to_labels(communities, nodes)
        nmi = nmi_score(
            pred,
            layers=layers,
            gt_labels=gt_labels,
            random_state=random_state,
            slouvain_ref_labels=slouvain_ref_labels,
        )

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

    def detect(self, *, bundle: Dict[str, Any], form: Dict[str, Any]) -> Dict[str, Any]:
        algorithm = self.ensure_algorithm(str(form["algorithm"]))
        epsilon = float(form["epsilon"])
        delta = float(form["delta"])
        key_size = int(form["key_size"])
        random_state = int(form["random_state"])
        lambd = float(form["lambd"])
        include_benchmark = _parse_bool(form.get("include_benchmark"), True)

        gt = bundle.get("ground_truth")
        slouvain_ref = (
            reference_labels_slouvain(bundle["layers"], random_state) if gt is None else None
        )

        communities, selected_result = self.run_single_algorithm(
            layers=bundle["layers"],
            gt_labels=gt,
            algorithm=algorithm,
            epsilon=epsilon,
            delta=delta,
            key_size=key_size,
            random_state=random_state,
            lambd=lambd,
            slouvain_ref_labels=slouvain_ref,
        )

        benchmark_rows = None
        if include_benchmark:
            benchmark_rows = []
            for algo in ALGORITHMS:
                _, row = self.run_single_algorithm(
                    layers=bundle["layers"],
                    gt_labels=gt,
                    algorithm=algo,
                    epsilon=epsilon,
                    delta=delta,
                    key_size=key_size,
                    random_state=random_state,
                    lambd=lambd,
                    slouvain_ref_labels=slouvain_ref,
                )
                benchmark_rows.append(row)

        payload = self.local_system.bundle_payload(bundle)
        payload.update(
            {
                "selected_algorithm": algorithm,
                "statistics": selected_result,
                "benchmark": benchmark_rows,
                "communities": {str(node): int(group) for node, group in communities.items()},
                "framework": self.framework_overview(),
            }
        )
        return payload

    def visualize(self, *, bundle: Dict[str, Any], form: Dict[str, Any]) -> FileResponse:
        algorithm = self.ensure_algorithm(str(form["algorithm"]))
        random_state = int(form["random_state"])
        gt = bundle.get("ground_truth")
        slouvain_ref = (
            reference_labels_slouvain(bundle["layers"], random_state) if gt is None else None
        )
        communities, _ = self.run_single_algorithm(
            layers=bundle["layers"],
            gt_labels=gt,
            algorithm=algorithm,
            epsilon=float(form["epsilon"]),
            delta=float(form["delta"]),
            key_size=int(form["key_size"]),
            random_state=random_state,
            lambd=float(form["lambd"]),
            slouvain_ref_labels=slouvain_ref,
        )
        return self.local_system.render_visualization(
            bundle,
            communities,
            algorithm=algorithm,
            layout=str(form["layout"]),
        )

    def visualize3d(self, *, bundle: Dict[str, Any], form: Dict[str, Any]) -> Dict[str, Any]:
        algorithm = self.ensure_algorithm(str(form["algorithm"]))
        random_state = int(form["random_state"])
        gt = bundle.get("ground_truth")
        slouvain_ref = (
            reference_labels_slouvain(bundle["layers"], random_state) if gt is None else None
        )
        communities, selected_result = self.run_single_algorithm(
            layers=bundle["layers"],
            gt_labels=gt,
            algorithm=algorithm,
            epsilon=float(form["epsilon"]),
            delta=float(form["delta"]),
            key_size=int(form["key_size"]),
            random_state=random_state,
            lambd=float(form["lambd"]),
            slouvain_ref_labels=slouvain_ref,
        )
        graph = _aggregate_layers(bundle["layers"])
        payload = self.local_system.bundle_payload(bundle)
        payload.update(
            {
                "selected_algorithm": algorithm,
                "statistics": selected_result,
                "plot": self.local_system.build_multilayer_3d_payload(
                    bundle["layers"],
                    communities,
                    random_state=random_state,
                ),
                "aggregate_plot": self.local_system.build_interactive_3d_payload(
                    graph,
                    communities,
                    random_state=random_state,
                ),
                "framework": self.framework_overview(),
            }
        )
        return payload
