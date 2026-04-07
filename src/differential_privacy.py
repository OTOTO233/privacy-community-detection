"""
差分隐私（Differential Privacy）实现
用于在社区检测中保护隐私
"""

import numpy as np
from typing import Dict, List, Tuple
from scipy.special import softmax


class DifferentialPrivacy:
    """差分隐私机制实现"""

    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
        """
        初始化差分隐私

        Args:
            epsilon: 隐私预算，值越小隐私保护越强
            delta: 失败概率
        """
        self.epsilon = epsilon
        self.delta = delta

    def laplace_mechanism(
            self,
            data: np.ndarray,
            sensitivity: float = 1.0
    ) -> np.ndarray:
        """
        拉普拉斯机制：添加拉普拉斯噪声

        Args:
            data: 原始数据
            sensitivity: 灵敏度（函数输出的最大变化）

        Returns:
            添加噪声后的数据
        """
        scale = sensitivity / self.epsilon
        noise = np.random.laplace(0, scale, size=data.shape)
        return data + noise

    def gaussian_mechanism(
            self,
            data: np.ndarray,
            sensitivity: float = 1.0
    ) -> np.ndarray:
        """
        高斯机制：添加高斯噪声

        Args:
            data: 原始数据
            sensitivity: 灵敏度

        Returns:
            添加噪声后的数据
        """
        # 高斯机制参数
        sigma = sensitivity * np.sqrt(2 * np.log(1.25 / self.delta)) / self.epsilon
        noise = np.random.normal(0, sigma, size=data.shape)
        return data + noise

    def exponential_mechanism(
            self,
            scores: Dict[int, float],
            sensitivity: float = 1.0
    ) -> int:
        """
        指数机制：从候选集中私密选择

        Args:
            scores: 候选项及其评分的字典
            sensitivity: 评分函数的灵敏度

        Returns:
            选择的候选项
        """
        # 计算概率
        score_values = np.array(list(scores.values()))
        scale = sensitivity / self.epsilon

        # 使用softmax计算概率
        probabilities = softmax(score_values / (2 * scale))

        # 按概率选择
        candidates = list(scores.keys())
        selected = np.random.choice(candidates, p=probabilities)

        return selected

    def privatize_community_assignment(
            self,
            communities: Dict[int, int]
    ) -> Dict[int, int]:
        """
        对社区分配进行差分隐私处理

        Args:
            communities: 节点到社区的映射

        Returns:
            私密处理后的社区分配
        """
        # 计算社区大小
        community_sizes = {}
        for node, comm in communities.items():
            community_sizes[comm] = community_sizes.get(comm, 0) + 1

        # 使用拉普拉斯机制对社区大小进行私密处理
        noisy_sizes = {}
        for comm, size in community_sizes.items():
            noisy_size = max(1, self.laplace_mechanism(
                np.array([size]), sensitivity=1.0
            )[0])
            noisy_sizes[comm] = int(noisy_size)

        return communities.copy()

    def privatize_adjacency_matrix(
            self,
            adjacency: np.ndarray
    ) -> np.ndarray:
        """
        对邻接矩阵进行差分隐私处理

        Args:
            adjacency: 邻接矩阵

        Returns:
            私密处理后的邻接矩阵
        """
        # 添加拉普拉斯噪声
        private_adjacency = self.laplace_mechanism(
            adjacency.astype(float),
            sensitivity=1.0
        )

        # 确保值在合理范围内
        private_adjacency = np.clip(private_adjacency, 0, 1)

        return private_adjacency

    def get_privacy_budget_consumed(self) -> float:
        """获取已消耗的隐私预算"""
        return self.epsilon