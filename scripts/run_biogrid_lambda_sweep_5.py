from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiment_datasets import BIOGRID_MAX_LAYERS, get_biogrid_species, load_dataset
from src.pmcdm import PMCDMExperiment


DEFAULT_TOKENS = [
    "Plasmodium_falciparum_3D7",
    "Human_Immunodeficiency_Virus_1",
    "Escherichia_coli_K12_MG1655",
    "Xenopus_laevis",
    "Middle-East_Respiratory_Syndrome-related_Coronavirus",
]
LAMBDA_VALUES = [round(i * 0.1, 1) for i in range(11)]


def _resolve_member(species_list: list[dict[str, str]], token: str) -> dict[str, str] | None:
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
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="固定 5 个 BioGRID 数据集，扫描 lambda=0..1 并导出单表")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "output")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--max-nodes", type=int, default=1000)
    args = parser.parse_args()

    species_list = get_biogrid_species()
    if not species_list:
        raise RuntimeError("未找到 BioGRID 数据，请检查 data/ 目录")

    selected: list[dict[str, str]] = []
    for token in DEFAULT_TOKENS:
        item = _resolve_member(species_list, token)
        if item is None:
            raise RuntimeError(f"无法匹配物种 token: {token}")
        selected.append(item)

    variant_base = {
        "top_layers": BIOGRID_MAX_LAYERS,
        "min_edges": 12,
        "max_nodes": args.max_nodes,
        "include_genetic": True,
        "auto_layers": True,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = args.out_dir / f"biogrid_5_lambda_sweep_{stamp}.csv"

    exp = PMCDMExperiment(epsilon=1.0, delta=1e-5, key_size=512, random_state=args.random_state)
    rows: list[dict[str, Any]] = []

    for idx, item in enumerate(selected, start=1):
        member = item["member"]
        label = item["label"]
        print(f"[{idx}/{len(selected)}] dataset={label}", flush=True)
        dataset = load_dataset("biogrid", variant={**variant_base, "member": member})
        n_nodes = dataset.layers[0].number_of_nodes()
        n_layers = len(dataset.layers)
        for lambd in LAMBDA_VALUES:
            print(f"  lambda={lambd}", flush=True)
            result = exp.run_benchmark(dataset.layers, dataset.ground_truth, lambd=lambd, algorithms=["DH-Louvain"])[0]
            rows.append(
                {
                    "species_label": label,
                    "member_file": member,
                    "lambda": lambd,
                    "algorithm": result.algorithm,
                    "modularity": result.modularity,
                    "module_density": result.module_density,
                    "nmi": result.nmi,
                    "privacy_rate": result.privacy_rate,
                    "communities": result.communities,
                    "n_nodes": n_nodes,
                    "n_layers": n_layers,
                    "dataset_summary": dataset.summary.replace("\n", " ").strip(),
                }
            )

    with out_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"已写入: {out_path}")


if __name__ == "__main__":
    main()
