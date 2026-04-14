"""Evolutionary optimization for privacy-preserving community detection."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
import time
from typing import Any, Dict, Iterable, List, Literal, Optional

import networkx as nx

from .experiment_datasets import DatasetBundle, load_dataset
from .pmcdm import (
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

AlgorithmName = Literal[
    "S-Louvain",
    "PD-Louvain",
    "R-Louvain",
    "DP-Louvain",
    "K-Louvain",
    "DH-Louvain",
]
ParameterKind = Literal["float", "int", "choice"]


@dataclass(frozen=True)
class ParameterBound:
    """Defines the legal range of a single optimizable parameter."""

    # 这一层对应“染色体编码规则”：
    # 每个待优化参数都要先说明它是什么类型、能取什么范围，进化算法才能在合法空间里搜索。

    name: str
    kind: ParameterKind
    low: float | int | None = None
    high: float | int | None = None
    choices: tuple[Any, ...] = ()

    def sample(self, rng: random.Random) -> Any:
        # 初始化种群时，从参数空间里随机采样一个基因值。
        if self.kind == "float":
            return rng.uniform(float(self.low), float(self.high))
        if self.kind == "int":
            return rng.randint(int(self.low), int(self.high))
        if self.kind == "choice":
            if not self.choices:
                raise ValueError(f"参数 {self.name} 未提供可选值")
            return rng.choice(self.choices)
        raise ValueError(f"不支持的参数类型: {self.kind}")

    def clamp(self, value: Any) -> Any:
        # 交叉/变异之后，参数可能跑出边界，这里负责把它拉回合法范围。
        if self.kind == "float":
            return min(max(float(value), float(self.low)), float(self.high))
        if self.kind == "int":
            clamped = min(max(int(round(float(value))), int(self.low)), int(self.high))
            return clamped
        if self.kind == "choice":
            if value in self.choices:
                return value
            return self.choices[0]
        raise ValueError(f"不支持的参数类型: {self.kind}")


@dataclass
class CandidateEvaluation:
    """Result of evaluating one candidate parameter set."""

    # 这个结构保存“一个个体”的完整评估结果：
    # params 是参数染色体，fitness 是适应度，其余字段是便于分析和展示的细粒度指标。

    params: Dict[str, Any]
    fitness: float
    modularity: float
    module_density: float
    nmi: Optional[float]
    privacy_rate: float
    communities: int
    runtime_seconds: float


@dataclass
class GenerationRecord:
    """Compact per-generation progress snapshot."""

    # 每一代都记录一次最优值和平均值，后面可以直接用来画收敛曲线或写实验过程分析。

    generation: int
    best_fitness: float
    mean_fitness: float
    best_params: Dict[str, Any]


@dataclass
class EvolutionResult:
    """Final optimization artifact with history and best candidate."""

    # 最终输出不只包含最优参数，还包含整个进化历史，方便后续论文图表和结果复现。

    dataset_summary: str
    algorithm: AlgorithmName
    best: CandidateEvaluation
    history: List[GenerationRecord]
    evaluations: int


@dataclass
class EvolutionaryOptimizerConfig:
    """Hyperparameters for the first-version evolutionary search."""

    # 这里放的是“进化算法自己的超参数”，不是被优化对象的结果参数。
    # 例如种群规模、进化代数、交叉率、变异率，都决定搜索过程怎么进行。

    dataset_name: str = "aucs"
    dataset_variant: Any = None
    algorithm: AlgorithmName = "DH-Louvain"
    population_size: int = 20
    generations: int = 30
    elite_size: int = 2
    tournament_size: int = 3
    crossover_rate: float = 0.8
    mutation_rate: float = 0.2
    random_state: int = 42
    key_size: int = 512
    delta: float = 1e-5
    parameter_bounds: List[ParameterBound] = field(
        default_factory=lambda: [
            ParameterBound("epsilon", "float", low=0.1, high=5.0),
            ParameterBound("lambd", "float", low=0.1, high=0.9),
        ]
    )
    metric_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "modularity": 0.35,
            "module_density": 0.25,
            "nmi": 0.20,
            "privacy_rate": 0.20,
        }
    )
    runtime_penalty: float = 0.0


class EvolutionaryOptimizer:
    """GA-style optimizer for privacy-performance parameter search."""

    # 这个类相当于一个“外层优化器”：
    # 它不直接做社区检测，而是不断生成参数组合，反复调用现有 PMCDM 流程并比较效果。

    def __init__(self, config: EvolutionaryOptimizerConfig):
        self.config = config
        self.rng = random.Random(config.random_state)
        self.dataset = load_dataset(config.dataset_name, variant=config.dataset_variant)
        self.bounds = {bound.name: bound for bound in config.parameter_bounds}
        # 无真实标签的数据集：预先算好 S-Louvain 参考划分，避免每次评估都重复跑一遍。
        self._slouvain_ref_labels: Optional[List[int]] = (
            reference_labels_slouvain(self.dataset.layers, config.random_state)
            if self.dataset.ground_truth is None
            else None
        )
        # 初始化时先把数据集和参数边界固定下来，避免每一代重复做这些准备工作。
        self._validate_config()

    def optimize(self) -> EvolutionResult:
        # 第一步：随机生成初始种群。
        population = [self._sample_candidate() for _ in range(self.config.population_size)]
        history: List[GenerationRecord] = []
        evaluations = 0
        best_overall: CandidateEvaluation | None = None

        for generation in range(self.config.generations):
            # 第二步：对当前整个人口做适应度评估。
            scored_population = [self._evaluate_candidate(candidate) for candidate in population]
            scored_population.sort(key=lambda item: item.fitness, reverse=True)
            evaluations += len(scored_population)

            generation_best = scored_population[0]
            if best_overall is None or generation_best.fitness > best_overall.fitness:
                best_overall = generation_best

            mean_fitness = sum(item.fitness for item in scored_population) / max(1, len(scored_population))
            history.append(
                GenerationRecord(
                    generation=generation,
                    best_fitness=generation_best.fitness,
                    mean_fitness=mean_fitness,
                    best_params=generation_best.params.copy(),
                )
            )

            if generation == self.config.generations - 1:
                break

            # 第三步：精英保留，直接把当前最好的若干个体送进下一代，避免优解丢失。
            next_population = [item.params.copy() for item in scored_population[: self.config.elite_size]]
            while len(next_population) < self.config.population_size:
                # 第四步：从当前种群里做选择，挑出两个父代。
                parent1 = self._tournament_select(scored_population)
                parent2 = self._tournament_select(scored_population)
                # 第五步：交叉产生子代，再做变异增加多样性。
                child = self._crossover(parent1.params, parent2.params)
                child = self._mutate(child)
                next_population.append(child)
            population = next_population

        return EvolutionResult(
            dataset_summary=self.dataset.summary,
            algorithm=self.config.algorithm,
            best=best_overall,
            history=history,
            evaluations=evaluations,
        )

    def _validate_config(self) -> None:
        # 这部分是基础安全检查，避免配置本身不合理导致算法行为异常。
        if self.config.population_size < 2:
            raise ValueError("population_size 必须 >= 2")
        if self.config.generations < 1:
            raise ValueError("generations 必须 >= 1")
        if not 0 <= self.config.mutation_rate <= 1:
            raise ValueError("mutation_rate 必须在 [0, 1] 范围内")
        if not 0 <= self.config.crossover_rate <= 1:
            raise ValueError("crossover_rate 必须在 [0, 1] 范围内")
        if not 0 < self.config.elite_size <= self.config.population_size:
            raise ValueError("elite_size 必须在 1 到 population_size 之间")
        if self.config.tournament_size < 2:
            raise ValueError("tournament_size 必须 >= 2")
        if not self.config.parameter_bounds:
            raise ValueError("至少需要一个可优化参数")

    def _sample_candidate(self) -> Dict[str, Any]:
        # 生成一个随机个体，也就是一组可执行的参数组合。
        return {name: bound.sample(self.rng) for name, bound in self.bounds.items()}

    def _tournament_select(self, scored_population: List[CandidateEvaluation]) -> CandidateEvaluation:
        # 锦标赛选择：
        # 从种群里随机抽几名“选手”，谁 fitness 高就当父代。
        # 这种方法实现简单，而且比“永远只选最优个体”更不容易早熟收敛。
        size = min(self.config.tournament_size, len(scored_population))
        competitors = self.rng.sample(scored_population, size)
        return max(competitors, key=lambda item: item.fitness)

    def _crossover(self, parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Dict[str, Any]:
        # 交叉算子负责“重组父代基因”：
        # 连续参数用线性混合，离散参数直接从父母中选一个。
        if self.rng.random() > self.config.crossover_rate:
            return parent1.copy() if self.rng.random() < 0.5 else parent2.copy()

        child: Dict[str, Any] = {}
        for name, bound in self.bounds.items():
            left = parent1[name]
            right = parent2[name]
            if bound.kind == "float":
                alpha = self.rng.random()
                child[name] = bound.clamp(alpha * float(left) + (1.0 - alpha) * float(right))
            elif bound.kind == "int":
                chosen = left if self.rng.random() < 0.5 else right
                child[name] = bound.clamp(chosen)
            else:
                child[name] = left if self.rng.random() < 0.5 else right
        return child

    def _mutate(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        # 变异算子负责在局部做随机扰动，避免所有个体越来越像，从而陷入局部最优。
        mutated = candidate.copy()
        for name, bound in self.bounds.items():
            if self.rng.random() > self.config.mutation_rate:
                continue
            if bound.kind == "float":
                span = float(bound.high) - float(bound.low)
                delta = self.rng.gauss(0.0, span * 0.12)
                mutated[name] = bound.clamp(float(mutated[name]) + delta)
            elif bound.kind == "int":
                span = max(1, int(bound.high) - int(bound.low))
                delta = self.rng.randint(-max(1, span // 6), max(1, span // 6))
                mutated[name] = bound.clamp(int(mutated[name]) + delta)
            else:
                mutated[name] = bound.sample(self.rng)
        return mutated

    def _evaluate_candidate(self, candidate: Dict[str, Any]) -> CandidateEvaluation:
        # 这是“参数优化”和“社区检测系统”之间的桥梁：
        # 输入一组候选参数，真正跑一次隐私保护社区检测流程，再把结果转成 fitness。
        start = time.perf_counter()
        epsilon = float(candidate.get("epsilon", 1.0))
        lambd = float(candidate.get("lambd", 0.5))
        key_size = int(candidate.get("key_size", self.config.key_size))
        delta = float(candidate.get("delta", self.config.delta))

        communities, metrics = self._run_single_algorithm(
            self.dataset.layers,
            self.dataset.ground_truth,
            self.config.algorithm,
            epsilon=epsilon,
            delta=delta,
            key_size=key_size,
            lambd=lambd,
        )

        runtime_seconds = time.perf_counter() - start
        fitness = self._compute_fitness(metrics, runtime_seconds)
        return CandidateEvaluation(
            params=candidate.copy(),
            fitness=fitness,
            modularity=metrics["modularity"],
            module_density=metrics["module_density"],
            nmi=metrics["nmi"],
            privacy_rate=metrics["privacy_rate"],
            communities=metrics["communities"],
            runtime_seconds=runtime_seconds,
        )

    def _compute_fitness(self, metrics: Dict[str, Any], runtime_seconds: float) -> float:
        # 第一版采用“加权单目标”方案：
        # 把 Q、D、NMI、pr 合成一个总分，便于直接比较个体优劣。
        # 如果某些数据集没有真实标签，NMI 会自动跳过，不参与分母权重。
        weighted_sum = 0.0
        active_weight = 0.0
        for name, weight in self.config.metric_weights.items():
            value = metrics.get(name)
            if value is None:
                continue
            if isinstance(value, float) and math.isnan(value):
                continue
            weighted_sum += float(weight) * float(value)
            active_weight += float(weight)

        score = weighted_sum / active_weight if active_weight > 0 else 0.0
        if self.config.runtime_penalty > 0:
            score -= self.config.runtime_penalty * runtime_seconds
        return score

    def _run_single_algorithm(
        self,
        layers: List[nx.Graph],
        gt_labels: Optional[Dict[Any, int]],
        algorithm: AlgorithmName,
        *,
        epsilon: float,
        delta: float,
        key_size: int,
        lambd: float,
    ) -> tuple[Dict[Any, int], Dict[str, Any]]:
        # 这里复用了你现有系统的核心流程：
        # Terminal -> Cloud1 扰动/加密 -> Cloud2 检测 -> 计算指标。
        # 对进化算法来说，这个函数就是“黑盒评估器”。
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

        cloud1 = CloudServer1(epsilon, delta, key_size)
        terminal = TerminalClient(cloud1.he)

        processed_layers: List[nx.Graph] = []
        for layer in layers:
            # 同态加密只在指定算法里启用；差分隐私或其它扰动方式由 perturbation_mode 控制。
            uploaded = terminal.encrypt_upload(layer) if use_he else layer.copy()
            processed_layers.append(cloud1.perturb_layer(uploaded, mode=perturbation_mode))

        if use_dh_framework:
            # DH-Louvain 走终端/云1/云2 协同框架。
            cloud2 = CloudServer2(cloud1, random_state=self.config.random_state)
            communities = cloud2.run_dh_louvain(processed_layers, lambd=lambd)
        else:
            # 非 DH 框架的算法直接在扰动后的层图上运行。
            communities = SLouvain(random_state=self.config.random_state).detect(processed_layers)

        nodes = sorted(layers[0].nodes())
        pred = partition_to_labels(communities, nodes)
        nmi = nmi_score(
            pred,
            layers=layers,
            gt_labels=gt_labels,
            random_state=self.config.random_state,
            slouvain_ref_labels=self._slouvain_ref_labels,
        )

        metric_graph = processed_layers[0]
        groups = list(communities_to_groups(communities).values())
        modularity = nx.algorithms.community.modularity(metric_graph, groups, weight="weight")
        module_density = modularity_density(metric_graph, communities)
        pe = cloud1.preserved_edges / max(1, cloud1.total_edges)
        pw = 1.0 if use_he else 0.0

        return communities, {
            "modularity": float(modularity),
            "module_density": float(module_density),
            "nmi": None if math.isnan(nmi) else float(nmi),
            "privacy_rate": float((pe + pw) / 2.0),
            "communities": len(set(communities.values())),
        }


def format_history(history: Iterable[GenerationRecord]) -> str:
    """Pretty-print helper for CLI scripts."""

    # 这个函数主要服务于命令行输出，让每一代的收敛信息一眼可读。
    lines = [
        f"{'代数':<8}{'最佳 fitness':<18}{'平均 fitness':<18}{'最优参数':<40}",
        "-" * 84,
    ]
    for item in history:
        lines.append(
            f"{item.generation:<8d}"
            f"{item.best_fitness:<18.4f}"
            f"{item.mean_fitness:<18.4f}"
            f"{str(item.best_params):<40}"
        )
    return "\n".join(lines)


def _serialize_candidate(evaluation: CandidateEvaluation) -> Dict[str, Any]:
    nmi = evaluation.nmi
    if nmi is not None and isinstance(nmi, float) and math.isnan(nmi):
        nmi = None
    return {
        "params": evaluation.params,
        "fitness": float(evaluation.fitness),
        "modularity": float(evaluation.modularity),
        "module_density": float(evaluation.module_density),
        "nmi": nmi,
        "privacy_rate": float(evaluation.privacy_rate),
        "communities": int(evaluation.communities),
        "runtime_seconds": float(evaluation.runtime_seconds),
    }


def serialize_evolution_result(
    result: EvolutionResult,
    baseline: Optional[CandidateEvaluation] = None,
) -> Dict[str, Any]:
    """将进化结果转为可 JSON 序列化的字典（供 FastAPI / 落盘）。"""
    payload: Dict[str, Any] = {
        "dataset_summary": result.dataset_summary,
        "algorithm": result.algorithm,
        "best": _serialize_candidate(result.best),
        "history": [
            {
                "generation": h.generation,
                "best_fitness": float(h.best_fitness),
                "mean_fitness": float(h.mean_fitness),
                "best_params": dict(h.best_params),
            }
            for h in result.history
        ],
        "evaluations": int(result.evaluations),
    }
    if baseline is not None:
        payload["baseline"] = _serialize_candidate(baseline)
    return payload
