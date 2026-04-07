"""
数据处理模块
支持多种数据格式的读取和转换
"""

import networkx as nx
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class DataProcessor:
    """数据处理器"""

    @staticmethod
    def read_edge_list(filepath: str, sep: str = '\t') -> nx.Graph:
        """
        从边列表文件读取图

        Args:
            filepath: 文件路径
            sep: 分隔符

        Returns:
            NetworkX 图对象
        """
        df = pd.read_csv(filepath, sep=sep, header=None)

        if df.shape[1] < 2:
            raise ValueError("边列表文件至少需要2列（源节点和目标节点）")

        # 创建图
        G = nx.Graph()

        for _, row in df.iterrows():
            source = int(row[0])
            target = int(row[1])
            weight = float(row[2]) if df.shape[1] > 2 else 1.0

            G.add_edge(source, target, weight=weight)

        return G

    @staticmethod
    def read_adjacency_matrix(filepath: str) -> nx.Graph:
        """
        从邻接矩阵文件读取图

        Args:
            filepath: 文件路径

        Returns:
            NetworkX 图对象
        """
        # 读取矩阵
        adj_matrix = pd.read_csv(filepath, sep='\s+', header=None).values

        # 创建图
        G = nx.Graph()
        n = adj_matrix.shape[0]

        for i in range(n):
            for j in range(i + 1, n):
                if adj_matrix[i, j] != 0:
                    G.add_edge(i, j, weight=adj_matrix[i, j])

        return G

    @staticmethod
    def read_from_txt(filepath: str) -> nx.Graph:
        """
        从文本文件读取图（自动检测格式）

        Args:
            filepath: 文件路径

        Returns:
            NetworkX 图对象
        """
        with open(filepath, 'r') as f:
            lines = f.readlines()

        # 检测文件格式
        # 尝试边列表格式
        try:
            G = DataProcessor.read_edge_list(filepath)
            return G
        except:
            pass

        # 尝试邻接矩阵格式
        try:
            G = DataProcessor.read_adjacency_matrix(filepath)
            return G
        except:
            pass

        raise ValueError("无法识别文件格式")

    @staticmethod
    def read_dataset(filepath: str) -> nx.Graph:
        """
        读取数据集（支持多种格式）

        Args:
            filepath: 文件路径

        Returns:
            NetworkX 图对象
        """
        path = Path(filepath)

        if path.suffix == '.csv':
            return DataProcessor.read_edge_list(filepath)
        elif path.suffix == '.txt':
            return DataProcessor.read_from_txt(filepath)
        elif path.suffix in ['.npy', '.npz']:
            adj_matrix = np.load(filepath)
            G = nx.Graph()
            n = adj_matrix.shape[0]
            for i in range(n):
                for j in range(i + 1, n):
                    if adj_matrix[i, j] != 0:
                        G.add_edge(i, j)
            return G
        else:
            raise ValueError(f"不支持的文件格式: {path.suffix}")

    @staticmethod
    def get_adjacency_matrix(graph: nx.Graph) -> np.ndarray:
        """
        获取图的邻接矩阵

        Args:
            graph: NetworkX 图对象

        Returns:
            邻接矩阵
        """
        return nx.adjacency_matrix(graph).todense()

    @staticmethod
    def graph_statistics(graph: nx.Graph) -> Dict:
        """
        获取图的统计信息

        Args:
            graph: NetworkX 图对象

        Returns:
            统计信息字典
        """
        return {
            'num_nodes': graph.number_of_nodes(),
            'num_edges': graph.number_of_edges(),
            'density': nx.density(graph),
            'is_connected': nx.is_connected(graph),
            'num_components': nx.number_connected_components(graph),
            'avg_degree': 2 * graph.number_of_edges() / graph.number_of_nodes(),
        }