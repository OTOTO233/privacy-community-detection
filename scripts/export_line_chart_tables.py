from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

ITERATION_CSV = OUTPUT / "biogrid_5_iterations_experiment.csv"
LFR_MU_CSV = OUTPUT / "lfr_experiment_mu_n300_all.csv"


FIG55_SPECIES_ORDER = ["Plasmodium", "HIV-1", "E.coli", "Xenopus", "MERS"]
FIG56_ALGO_ORDER = ["S-Louvain", "PD-Louvain", "R-Louvain", "DP-Louvain", "K-Louvain", "DH-Louvain"]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _fmt_float(value: float) -> str:
    return f"{value:.4f}"


def _write_markdown(path: Path, sections: list[tuple[str, list[str], list[list[str]]]]) -> None:
    lines: list[str] = []
    for title, headers, rows in sections:
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in rows:
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def export_fig55_tables() -> list[tuple[str, list[str], list[list[str]]]]:
    rows = _read_csv(ITERATION_CSV)
    metrics = [
        ("d_over_n", "表A-1 图5-5(a) 五个真实生物网络 D/n 随迭代次数变化"),
        ("modularity", "表A-2 图5-5(b) 五个真实生物网络 Q 随迭代次数变化"),
        ("nmi", "表A-3 图5-5(c) 五个真实生物网络 NMI 随迭代次数变化"),
    ]
    sections: list[tuple[str, list[str], list[list[str]]]] = []

    for field, title in metrics:
        pivot_rows: list[dict[str, str]] = []
        md_rows: list[list[str]] = []
        for species in FIG55_SPECIES_ORDER:
            series = [row for row in rows if row["species"] == species]
            series.sort(key=lambda item: int(item["iteration"]))
            out_row = {"species": species}
            md_row = [species]
            for item in series:
                key = f"iter_{item['iteration']}"
                value = _fmt_float(float(item[field]))
                out_row[key] = value
                md_row.append(value)
            pivot_rows.append(out_row)
            md_rows.append(md_row)

        suffix = {
            "d_over_n": "d_over_n",
            "modularity": "modularity",
            "nmi": "nmi",
        }[field]
        _write_csv(OUTPUT / f"table_fig5_5_{suffix}_by_iteration.csv", pivot_rows)
        headers = ["网络", "1次", "2次", "3次", "4次", "5次", "6次"]
        sections.append((title, headers, md_rows))

    return sections


def export_fig56_to_fig58_tables() -> list[tuple[str, list[str], list[list[str]]]]:
    rows = _read_csv(LFR_MU_CSV)
    metrics = [
        ("modularity", "表A-4 图5-6 基准网络参数控制实验中模块度 Q 随 μ 变化"),
        ("module_density", "表A-5 图5-7 基准网络参数控制实验中模块密度 D 随 μ 变化"),
        ("nmi", "表A-6 图5-8 基准网络参数控制实验中 NMI 随 μ 变化"),
    ]
    sections: list[tuple[str, list[str], list[list[str]]]] = []

    for field, title in metrics:
        grouped: dict[str, dict[str, str]] = {}
        for row in rows:
            mu = f"{float(row['mu']):.2f}"
            grouped.setdefault(mu, {"mu": mu})
            grouped[mu][row["algorithm"]] = _fmt_float(float(row[field]))

        ordered_mu = sorted(grouped.keys(), key=float)
        pivot_rows = [grouped[mu] for mu in ordered_mu]
        md_rows: list[list[str]] = []
        for mu in ordered_mu:
            row = grouped[mu]
            md_rows.append([mu] + [row.get(algo, "") for algo in FIG56_ALGO_ORDER])

        suffix = {
            "modularity": "modularity",
            "module_density": "module_density",
            "nmi": "nmi",
        }[field]
        _write_csv(OUTPUT / f"table_fig5_{6 if field == 'modularity' else 7 if field == 'module_density' else 8}_{suffix}_by_mu.csv", pivot_rows)
        headers = ["μ"] + FIG56_ALGO_ORDER
        sections.append((title, headers, md_rows))

    return sections


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sections = export_fig55_tables() + export_fig56_to_fig58_tables()
    _write_markdown(OUTPUT / "missing_line_chart_tables.md", sections)
    print(OUTPUT / "missing_line_chart_tables.md")


if __name__ == "__main__":
    main()
