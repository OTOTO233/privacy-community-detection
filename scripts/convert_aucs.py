"""Convert the AUCS MPX file into the processed edge-list layout used by this repo."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
import re


KNOWN_LAYERS = {"coauthor", "facebook", "leisure", "lunch", "work"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _find_aucs_source(root: Path) -> Path:
    candidates = [
        root / "data" / "raw" / "aucs.mpx",
        root / "data" / "raw" / "multinet" / "inst" / "extdata" / "aucs.mpx",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "未找到 aucs.mpx。请将原始文件放到 data/raw/aucs.mpx "
        "或 data/raw/multinet/inst/extdata/aucs.mpx。"
    )


def _parse_actor_id(value: str) -> int:
    match = re.search(r"(\d+)$", value.strip())
    if not match:
        raise ValueError(f"无法解析 AUCS 节点编号: {value}")
    return int(match.group(1))


def parse_mpx(path: Path) -> tuple[dict[int, str], dict[str, dict[tuple[int, int], float]]]:
    nodes: dict[int, str] = {}
    layer_edges: dict[str, dict[tuple[int, int], float]] = defaultdict(dict)
    section = ""

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            lowered = line.lower()
            if lowered.startswith("#actors"):
                section = "vertices"
                continue
            if lowered.startswith("#edges"):
                section = "edges"
                continue
            if lowered.startswith("#actor attributes"):
                section = "attrs"
                continue
            if line.startswith("%") or line.startswith("#"):
                continue

            if section == "vertices":
                parts = [part.strip() for part in line.split(",")]
                if len(parts) < 2:
                    continue
                node_id = _parse_actor_id(parts[0])
                nodes[node_id] = parts[1] or "NA"
                continue

            if section == "edges":
                parts = [part.strip() for part in line.split(",")]
                if len(parts) < 3:
                    continue
                source = _parse_actor_id(parts[0])
                target = _parse_actor_id(parts[1])
                layer = parts[2].lower()
                if layer not in KNOWN_LAYERS:
                    continue
                weight = float(parts[3]) if len(parts) > 3 and parts[3] else 1.0
                edge = tuple(sorted((source, target)))
                layer_edges[layer][edge] = weight

    if not nodes and layer_edges:
        node_ids = sorted({node for edges in layer_edges.values() for edge in edges for node in edge})
        nodes = {node_id: "NA" for node_id in node_ids}

    if not layer_edges:
        raise ValueError("未能从 MPX 文件中解析出任何边，请检查原始文件格式。")

    return nodes, layer_edges


def write_processed_files(
    root: Path,
    nodes: dict[int, str],
    layer_edges: dict[str, dict[tuple[int, int], float]],
) -> None:
    out_dir = root / "data" / "processed" / "aucs"
    layers_dir = out_dir / "layers"
    out_dir.mkdir(parents=True, exist_ok=True)
    layers_dir.mkdir(parents=True, exist_ok=True)

    nodes_path = out_dir / "nodes.csv"
    with nodes_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["node_id", "group"])
        for node_id in sorted(nodes):
            writer.writerow([node_id, nodes[node_id]])

    all_edges = []
    summary_rows = []
    for layer_name in sorted(layer_edges):
        layer_path = layers_dir / f"{layer_name}_undirected.txt"
        edges = sorted(layer_edges[layer_name].items())
        with layer_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter=" ")
            for (source, target), weight in edges:
                writer.writerow([source, target, weight])
                all_edges.append((source, target, layer_name, weight))
        summary_rows.append((layer_name, len(edges)))

    edges_path = out_dir / "edges_all.csv"
    with edges_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source", "target", "layer", "weight"])
        for row in all_edges:
            writer.writerow(row)

    summary_path = out_dir / "summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["layer", "num_edges"])
        writer.writerows(summary_rows)


def main() -> None:
    root = _repo_root()
    source_path = _find_aucs_source(root)
    nodes, layer_edges = parse_mpx(source_path)
    write_processed_files(root, nodes, layer_edges)

    print(f"已转换 AUCS 数据: {source_path}")
    print(f"节点数: {len(nodes)}")
    for layer_name in sorted(layer_edges):
        print(f"{layer_name}: {len(layer_edges[layer_name])} 条边")


if __name__ == "__main__":
    main()
