"""
可视化模块
用于生成社区检测结果的图像
"""

import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Optional
import seaborn as sns
from pathlib import Path


class Visualizer:
    """社区检测结果可视化"""

    def __init__(self, figsize: tuple[int, int] = (12, 10)):
        """
        初始化可视化器

        Args:
            figsize: 图表大小
        """
        self.figsize = figsize
        sns.set_style("whitegrid")

    def visualize_communities(
            self,
            graph: nx.Graph,
            communities: Dict[int, int],
            title: str = "Community Detection",
            output_path: Optional[str] = None,
            layout: str = "spring"
    ) -> None:
        """
        可视化社区检测结果

        Args:
            graph: NetworkX 图对象
            communities: 节点到社区的映射
            title: 图表标题
            output_path: 输出路径
            layout: 布局方式 ('spring', 'circular', 'kamada_kawai')
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        # 计算布局
        if layout == "spring":
            pos = nx.spring_layout(graph, k=0.5, iterations=50)
        elif layout == "circular":
            pos = nx.circular_layout(graph)
        elif layout == "kamada_kawai":
            pos = nx.kamada_kawai_layout(graph)
        else:
            pos = nx.spring_layout(graph)

        # 获取颜色映射
        unique_communities = len(set(communities.values()))
        colors = plt.cm.Set3(np.linspace(0, 1, unique_communities))
        community_colors = {
            comm: colors[i]
            for i, comm in enumerate(set(communities.values()))
        }

        # 节点颜色
        node_colors = [community_colors[communities[node]] for node in graph.nodes()]

        # 绘制边
        nx.draw_networkx_edges(
            graph, pos,
            alpha=0.2,
            width=0.5,
            ax=ax
        )

        # 绘制节点
        nx.draw_networkx_nodes(
            graph, pos,
            node_color=node_colors,
            node_size=200,
            alpha=0.8,
            ax=ax
        )

        # 绘制标签
        nx.draw_networkx_labels(
            graph, pos,
            font_size=8,
            font_weight='bold',
            ax=ax
        )

        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.axis('off')

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {output_path}")

        plt.show()

    def visualize_statistics(
            self,
            statistics: Dict,
            output_path: Optional[str] = None
    ) -> None:
        """
        可视化统计信息

        Args:
            statistics: 统计信息字典
            output_path: 输出路径
        """
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # 社区大小分布
        communities = statistics.get('communities', {})
        community_sizes = [len(nodes) for nodes in communities.values()]

        axes[0, 0].bar(range(len(community_sizes)), community_sizes)
        axes[0, 0].set_xlabel('Community ID')
        axes[0, 0].set_ylabel('Size')
        axes[0, 0].set_title('Community Size Distribution')

        # 统计信息
        axes[0, 1].axis('off')
        stats_text = f"""
        Number of Communities: {statistics.get('num_communities', 'N/A')}
        Modularity: {statistics.get('modularity', 'N/A'):.4f}
        Avg Community Size: {statistics.get('avg_community_size', 'N/A'):.2f}
        Max Community Size: {statistics.get('max_community_size', 'N/A')}
        Min Community Size: {statistics.get('min_community_size', 'N/A')}
        """
        axes[0, 1].text(0.1, 0.5, stats_text, fontsize=12, family='monospace')

        # 社区大小箱线图
        axes[1, 0].boxplot(community_sizes)
        axes[1, 0].set_ylabel('Community Size')
        axes[1, 0].set_title('Community Size Box Plot')

        # 社区大小直方图
        axes[1, 1].hist(community_sizes, bins=20, edgecolor='black')
        axes[1, 1].set_xlabel('Community Size')
        axes[1, 1].set_ylabel('Frequency')
        axes[1, 1].set_title('Community Size Histogram')

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"统计图表已保存到: {output_path}")

        plt.show()

    def visualize_graph_properties(
            self,
            graph: nx.Graph,
            output_path: Optional[str] = None
    ) -> None:
        """
        可视化图的属性

        Args:
            graph: NetworkX 图对象
            output_path: 输出路径
        """
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # 度数分布
        degrees = [graph.degree(node) for node in graph.nodes()]
        axes[0, 0].hist(degrees, bins=20, edgecolor='black')
        axes[0, 0].set_xlabel('Degree')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('Degree Distribution')

        # 度数排名
        sorted_degrees = sorted(degrees, reverse=True)
        axes[0, 1].plot(sorted_degrees)
        axes[0, 1].set_xlabel('Node Rank')
        axes[0, 1].set_ylabel('Degree')
        axes[0, 1].set_title('Degree Ranking')
        axes[0, 1].set_yscale('log')

        # 图统计
        stats = {
            'Nodes': graph.number_of_nodes(),
            'Edges': graph.number_of_edges(),
            'Density': nx.density(graph),
            'Avg Clustering': nx.average_clustering(graph),
        }

        axes[1, 0].axis('off')
        stats_text = '\n'.join([f'{k}: {v:.4f}' if isinstance(v, float) else f'{k}: {v}'
                                for k, v in stats.items()])
        axes[1, 0].text(0.1, 0.5, stats_text, fontsize=12, family='monospace')

        # 连通分量
        if nx.is_connected(graph):
            axes[1, 1].text(0.5, 0.5, 'Graph is Connected',
                            ha='center', va='center', fontsize=14)
        else:
            components = list(nx.connected_components(graph))
            comp_sizes = [len(c) for c in components]
            axes[1, 1].bar(range(len(comp_sizes)), comp_sizes)
            axes[1, 1].set_xlabel('Component ID')
            axes[1, 1].set_ylabel('Size')
            axes[1, 1].set_title('Connected Components')

        axes[1, 1].axis('off') if nx.is_connected(graph) else None

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"图属性已保存到: {output_path}")

        plt.show()


from typing import Tuple