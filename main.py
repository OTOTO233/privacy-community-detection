"""PMCDM 实验入口。"""

import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.pmcdm import PMCDMExperiment
from src.experiment_datasets import get_biogrid_species, load_dataset


def _print_results(title: str, rows):
    # 统一打印各算法对比结果，方便命令行直接看实验表格。
    print(f"\n{title}")
    print("-" * 95)
    print(f"{'算法':<12}{'Q(模块度)':<14}{'D(模块密度)':<16}{'NMI':<12}{'pr(隐私率)':<14}{'社区数':<10}")
    print("-" * 95)
    for row in rows:
        print(
            f"{row.algorithm:<12}"
            f"{row.modularity:<14.4f}"
            f"{row.module_density:<16.4f}"
            f"{row.nmi:<12.4f}"
            f"{row.privacy_rate:<14.4f}"
            f"{row.communities:<10d}"
        )


def _choose_dataset() -> str:
    # 这里返回的是内部数据集代号，真正的数据装载逻辑在 experiment_datasets.py。
    options = {
        "1": "karate",
        "2": "aucs",
        "3": "mlfr",
        "4": "lfr",
        "5": "biogrid",
        "karate": "karate",
        "aucs": "aucs",
        "lfr": "lfr",
        "mlfr": "mlfr",
        "biogrid": "biogrid",
    }
    print("\n请选择实验数据集:")
    print("1. Karate Club")
    print("2. AUCS")
    print("3. mLFR Benchmark")
    print("4. LFR Benchmark")
    print("5. BioGRID")
    choice = input("输入编号或名称，直接回车默认 1: ").strip().lower()
    return options.get(choice or "1", "karate")


def _choose_lfr_preset() -> str:
    options = {
        "1": "small_easy",
        "2": "small_noisier",
        "3": "medium_noisier",
        "small_easy": "small_easy",
        "small_noisier": "small_noisier",
        "medium_noisier": "medium_noisier",
    }
    print("\n请选择 LFR 预设:")
    print("1. small_easy      (40 节点, mu=0.1, 默认)")
    print("2. small_noisier   (40 节点, mu=0.2)")
    print("3. medium_noisier  (60 节点, mu=0.2)")
    choice = input("输入编号或名称，直接回车默认 1: ").strip().lower()
    return options.get(choice or "1", "small_easy")


def _choose_lfr_mode():
    options = {
        "1": "preset",
        "2": "custom",
        "preset": "preset",
        "custom": "custom",
    }
    print("\n请选择 LFR 配置方式:")
    print("1. 预设参数")
    print("2. 手填参数")
    choice = input("输入编号或名称，直接回车默认 1: ").strip().lower()
    return options.get(choice or "1", "preset")


def _prompt_int(label: str, default: int) -> int:
    # 所有 CLI 数值输入都允许回车使用默认值。
    raw = input(f"{label} [{default}]: ").strip()
    return int(raw) if raw else default


def _prompt_float(label: str, default: float) -> float:
    raw = input(f"{label} [{default}]: ").strip()
    return float(raw) if raw else default


def _collect_lfr_custom_params():
    # LFR 使用 NetworkX 生成，参数和论文里的标准 LFR 含义一致。
    print("\n请输入 LFR 参数，直接回车使用默认值:")
    return {
        "n": _prompt_int("n", 40),
        "tau1": _prompt_float("tau1", 2.5),
        "tau2": _prompt_float("tau2", 1.5),
        "mu": _prompt_float("mu", 0.1),
        "average_degree": _prompt_int("average_degree", 6),
        "min_community": _prompt_int("min_community", 10),
        "max_community": _prompt_int("max_community", 20),
        "max_iters": _prompt_int("max_iters", 10000),
    }


def _collect_mlfr_params():
    # mLFR 走的是官方 Java 生成器，因此这里收集的是官方工具的参数键。
    print("\n请输入 mLFR 参数，直接回车使用默认值:")
    return {
        "network_type": input("network_type [UU]: ").strip().upper() or "UU",
        "n": _prompt_int("n", 40),
        "avg": _prompt_float("avg", 6.0),
        "max": _prompt_int("max", 12),
        "mix": _prompt_float("mix", 0.1),
        "tau1": _prompt_float("tau1", 2.5),
        "tau2": _prompt_float("tau2", 1.5),
        "mincom": _prompt_int("mincom", 10),
        "maxcom": _prompt_int("maxcom", 20),
        "l": _prompt_int("l", 3),
        "dc": _prompt_float("dc", 0.0),
        "rc": _prompt_float("rc", 0.0),
        "mparam1": _prompt_float("mparam1", 2.0),
        "on": _prompt_int("on", 0),
        "om": _prompt_int("om", 0),
    }


def _choose_biogrid_species() -> str:
    # BioGRID 不是固定单个文件，而是一个多物种压缩包，这里动态读取全部物种列表。
    species = get_biogrid_species()
    default_member = "BIOGRID-ORGANISM-Escherichia_coli_K12_MG1655-5.0.256.tab3.txt"
    default_index = next(
        (index for index, item in enumerate(species, start=1) if item["member"] == default_member),
        1,
    )
    print("\nBioGRID 可选物种:")
    for index, item in enumerate(species, start=1):
        print(f"{index}. {item['label']}")

    choice = input(f"输入编号或完整文件名，直接回车默认 {default_index}: ").strip()
    if not choice:
        return species[default_index - 1]["member"]
    if choice.isdigit():
        index = int(choice)
        if 1 <= index <= len(species):
            return species[index - 1]["member"]
    for item in species:
        if choice == item["member"]:
            return item["member"]
    raise ValueError("无效的 BioGRID 物种选择")


def _collect_biogrid_params():
    # BioGRID 原始图通常很大，因此额外提供 max_nodes 做子图截取，避免实验跑太久。
    print("\n请输入 BioGRID 参数，直接回车使用默认值:")
    auto_layers = (input("auto_layers（按去重边累计约 82% 自动选层数）[y]: ").strip().lower() or "y") in {
        "y",
        "yes",
        "1",
        "true",
        "",
    }
    return {
        "member": _choose_biogrid_species(),
        "top_layers": _prompt_int("top_layers（固定层数或自动模式上限，最大 3）", 3),
        "min_edges": _prompt_int("min_edges", 12),
        "max_nodes": _prompt_int("max_nodes", 300),
        "include_genetic": (input("include_genetic [y]: ").strip().lower() or "y") in {"y", "yes", "1", "true"},
        "auto_layers": auto_layers,
    }


def main():
    print("=" * 95)
    print("PMCDM: 多层系统 + 云服务器1/2 + DH-Louvain 对比实验")
    print("=" * 95)

    dataset_name = _choose_dataset()
    lfr_variant = None
    mlfr_variant = None
    biogrid_variant = None
    if dataset_name == "lfr":
        lfr_mode = _choose_lfr_mode()
        lfr_variant = _choose_lfr_preset() if lfr_mode == "preset" else _collect_lfr_custom_params()
    if dataset_name == "mlfr":
        mlfr_variant = _collect_mlfr_params()
    if dataset_name == "biogrid":
        biogrid_variant = _collect_biogrid_params()
    try:
        # 各数据集的“参数格式”不同，这里先整理成统一的 variant 再交给装载器。
        variant = None
        if dataset_name == "lfr":
            variant = lfr_variant
        elif dataset_name == "mlfr":
            variant = mlfr_variant
        elif dataset_name == "biogrid":
            variant = biogrid_variant
        dataset = load_dataset(dataset_name, variant=variant)
    except Exception as exc:
        print(f"\n数据集加载失败: {exc}")
        return
    print(f"\n数据集: {dataset.summary}")

    experiment = PMCDMExperiment(
        epsilon=1.0,
        delta=1e-5,
        key_size=512,
        random_state=42,
    )
    multiplex_layers = dataset.layers
    # 到这一步，所有数据集都会被整理成统一的“多层图列表”接口。
    print(f"多层系统: 已载入 {len(multiplex_layers)} 层网络 (模拟终端上传 -> 云1扰动/加密 -> 云2协同检测)")

    results = experiment.run_benchmark(multiplex_layers, dataset.ground_truth, lambd=0.5)
    _print_results("基准对比（DH-Louvain vs 变种 Louvain）", results)

    lambdas = [0.2, 0.4, 0.6, 0.8]
    mr = experiment.run_multiresolution(multiplex_layers, lambdas=lambdas)
    print("\n多分辨率结果 (DH-Louvain):")
    print("-" * 55)
    print(f"{'lambda':<10}{'D_lambda':<18}{'社区数':<10}")
    print("-" * 55)
    for lambd, score, ncom in mr:
        print(f"{lambd:<10.2f}{score:<18.4f}{ncom:<10d}")

    print("\n完成: 已输出 4 个核心指标 (Q, D, NMI, pr) 与多算法对比。")


if __name__ == "__main__":
    main()
