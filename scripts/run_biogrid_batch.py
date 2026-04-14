"""依次对 BioGRID 中前 N 个物种跑 PMCDM 基准，导出 CSV 与 Markdown 汇总表。"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiment_datasets import BIOGRID_MAX_LAYERS, get_biogrid_species, load_dataset
from src.pmcdm import PMCDMExperiment


def _fmt_float(v: float) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return ""
    return f"{float(v):.6f}"


def _aggregate_unique_edges(layers) -> int:
    seen: set[tuple[Any, Any]] = set()
    for g in layers:
        for u, v in g.edges():
            seen.add(tuple(sorted((u, v), key=str)))
    return len(seen)


def _biogrid_variant(max_nodes: int) -> Dict[str, Any]:
    return {
        "top_layers": BIOGRID_MAX_LAYERS,
        "min_edges": 12,
        "max_nodes": max_nodes,
        "include_genetic": True,
        "auto_layers": True,
    }


def _resolve_member(species_list: List[Dict[str, str]], token: str) -> Dict[str, str] | None:
    """按完整文件名、或 member 子串唯一匹配一条物种记录。"""
    raw = token.strip()
    if not raw:
        return None
    name = Path(raw).name
    for item in species_list:
        if item["member"] == raw or item["member"] == name:
            return item
    key = raw.lower().replace(" ", "_")
    hits = [s for s in species_list if key in s["member"].lower()]
    if len(hits) == 1:
        return hits[0]
    hits2 = [s for s in species_list if raw in s["member"]]
    if len(hits2) == 1:
        return hits2[0]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="BioGRID 前 N 个物种批量基准实验")
    parser.add_argument(
        "--members",
        type=str,
        default="",
        help="逗号分隔：tab3 文件名或唯一子串（如 Gallus_gallus,Caenorhabditis_elegans）；若指定则忽略 --count",
    )
    parser.add_argument("--count", type=int, default=10, help="物种数量（按 tab3 文件名排序后的前 N 个）")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "output",
        help="输出目录（默认项目 output/）",
    )
    parser.add_argument("--lambd", type=float, default=0.5, help="DH-Louvain / PD-Louvain 的 λ")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--max-nodes",
        type=int,
        default=1000,
        help="BioGRID 子图最大节点数（默认 1000，须 >=20）",
    )
    args = parser.parse_args()
    if args.max_nodes < 20:
        print("max_nodes 须 >= 20", file=sys.stderr)
        sys.exit(2)

    species_list = get_biogrid_species()
    if not species_list:
        print("未找到 BioGRID 数据：请将 BIOGRID-ORGANISM-LATEST.tab3.zip 或解压目录放到 data/ 下。")
        sys.exit(1)

    if args.members.strip():
        take = []
        for part in args.members.split(","):
            item = _resolve_member(species_list, part)
            if item is None:
                print(f"无法匹配物种 token: {part!r}（请改用 tab3 文件名中的唯一片段）", file=sys.stderr)
                sys.exit(2)
            take.append(item)
    else:
        take = species_list[: max(1, args.count)]

    variant_base = _biogrid_variant(args.max_nodes)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = f"pick{len(take)}" if args.members.strip() else f"top{len(take)}"
    csv_path = args.out_dir / f"biogrid_{tag}_batch_{stamp}.csv"
    md_path = args.out_dir / f"biogrid_{tag}_batch_{stamp}.md"

    experiment = PMCDMExperiment(
        epsilon=1.0,
        delta=1e-5,
        key_size=512,
        random_state=args.random_state,
    )

    csv_rows: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []

    for i, item in enumerate(take, start=1):
        member = item["member"]
        label = item["label"]
        print(f"[{i}/{len(take)}] {label} ({member}) ...", flush=True)
        variant = {**variant_base, "member": member}
        try:
            dataset = load_dataset("biogrid", variant=variant)
        except Exception as exc:
            print(f"  跳过：加载失败 — {exc}")
            csv_rows.append(
                {
                    "species_label": label,
                    "member_file": member,
                    "dataset_summary": "",
                    "n_nodes": "",
                    "n_layers": "",
                    "n_edges_agg": "",
                    "algorithm": "",
                    "modularity": "",
                    "module_density": "",
                    "nmi": "",
                    "privacy_rate": "",
                    "communities": "",
                    "error": str(exc),
                }
            )
            summary_rows.append(
                {
                    "species_label": label,
                    "member_file": member,
                    "n_nodes": "",
                    "n_layers": "",
                    "n_edges_agg": "",
                    "DH_Q": "",
                    "DH_D": "",
                    "DH_NMI": "",
                    "DH_pr": "",
                    "DH_num_communities": "",
                    "error": str(exc),
                }
            )
            continue

        layers = dataset.layers
        n_nodes = layers[0].number_of_nodes()
        n_layers = len(layers)
        n_edges = _aggregate_unique_edges(layers)

        rows = experiment.run_benchmark(layers, dataset.ground_truth, lambd=args.lambd)
        dh = next((r for r in rows if r.algorithm == "DH-Louvain"), None)

        for r in rows:
            csv_rows.append(
                {
                    "species_label": label,
                    "member_file": member,
                    "dataset_summary": dataset.summary.replace("\n", " ").strip(),
                    "n_nodes": n_nodes,
                    "n_layers": n_layers,
                    "n_edges_agg": n_edges,
                    "algorithm": r.algorithm,
                    "modularity": _fmt_float(r.modularity),
                    "module_density": _fmt_float(r.module_density),
                    "nmi": _fmt_float(r.nmi),
                    "privacy_rate": _fmt_float(r.privacy_rate),
                    "communities": r.communities,
                    "error": "",
                }
            )

        summary_rows.append(
            {
                "species_label": label,
                "member_file": member,
                "n_nodes": n_nodes,
                "n_layers": n_layers,
                "n_edges_agg": n_edges,
                "DH_Q": _fmt_float(dh.modularity) if dh is not None else "",
                "DH_D": _fmt_float(dh.module_density) if dh is not None else "",
                "DH_NMI": _fmt_float(dh.nmi) if dh is not None else "",
                "DH_pr": _fmt_float(dh.privacy_rate) if dh is not None else "",
                "DH_num_communities": dh.communities if dh is not None else "",
                "error": "",
            }
        )

    fieldnames = [
        "species_label",
        "member_file",
        "dataset_summary",
        "n_nodes",
        "n_layers",
        "n_edges_agg",
        "algorithm",
        "modularity",
        "module_density",
        "nmi",
        "privacy_rate",
        "communities",
        "error",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    # Markdown：一张汇总表（DH-Louvain）+ 说明
    title = f"指定 {len(take)} 个物种" if args.members.strip() else f"前 {len(take)} 个物种（文件名排序）"
    lines = [
        f"# BioGRID 批量实验（{title}）",
        "",
        f"- 生成时间：{stamp}",
        f"- λ = {args.lambd}，random_state = {args.random_state}",
        f"- BioGRID 参数：层数上限={BIOGRID_MAX_LAYERS}, min_edges=12, max_nodes={args.max_nodes}, include_genetic=True, auto_layers=True（member 见下表 CSV）",
        f"- 全量 6 算法逐行结果：**{csv_path.name}**",
        "",
        "## 汇总表（DH-Louvain）",
        "",
        "| # | 物种 | 节点数 | 层数 | 去重边数* | Q | D | NMI | pr | 社区数 |",
        "|---|------|--------|------|-----------|---|---|-----|----|--------|",
    ]
    for idx, s in enumerate(summary_rows, start=1):
        lines.append(
            "| {idx} | {lab} | {nn} | {nl} | {ne} | {q} | {d} | {nmi} | {pr} | {nc} |".format(
                idx=idx,
                lab=s["species_label"].replace("|", "\\|"),
                nn=s["n_nodes"],
                nl=s["n_layers"],
                ne=s["n_edges_agg"],
                q=s["DH_Q"] if s["DH_Q"] != "" else ("—" if s.get("error") else ""),
                d=s["DH_D"] if s["DH_D"] != "" else ("—" if s.get("error") else ""),
                nmi=s["DH_NMI"] if s["DH_NMI"] != "" else ("—" if s.get("error") else ""),
                pr=s["DH_pr"] if s["DH_pr"] != "" else ("—" if s.get("error") else ""),
                nc=(
                    str(s["DH_num_communities"])
                    if s["DH_num_communities"] != ""
                    else ("—" if s.get("error") else "")
                ),
            )
        )
    lines.extend(
        [
            "",
            "*去重边数：各层边集合并后的无向边数量（跨层同一条物理边只计一次）。*",
            "",
        ]
    )

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print()
    print(f"已写入：{csv_path}")
    print(f"已写入：{md_path}")


if __name__ == "__main__":
    main()
