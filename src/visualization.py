"""
可视化模块
用于生成社区检测结果的图像
"""

import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
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
        plt.rcParams["font.family"] = ["SimSun"]
        plt.rcParams["font.sans-serif"] = ["SimSun"]
        plt.rcParams["axes.unicode_minus"] = False

    def _compute_layout(self, graph: nx.Graph, layout: str) -> Dict:
        if layout == "spring":
            return nx.spring_layout(graph, k=0.5, iterations=50, seed=42)
        if layout == "circular":
            return nx.circular_layout(graph)
        if layout == "kamada_kawai":
            return nx.kamada_kawai_layout(graph)
        if layout == "3d_spring":
            return nx.spring_layout(graph, dim=3, k=0.7, iterations=100, seed=42)
        return nx.spring_layout(graph, k=0.5, iterations=50, seed=42)

    def _build_community_colors(self, communities: Dict[int, int]) -> Dict[int, np.ndarray]:
        unique_ids = sorted(set(communities.values()))
        colors = plt.cm.Set3(np.linspace(0, 1, len(unique_ids)))
        return {comm: colors[i] for i, comm in enumerate(unique_ids)}

    def _build_community_markers(self, communities: Dict[int, int]) -> Dict[int, str]:
        markers = ["o", "s", "^", "D", "v", "P", "X", "*", "<", ">"]
        unique_ids = sorted(set(communities.values()))
        return {comm: markers[i % len(markers)] for i, comm in enumerate(unique_ids)}

    def _visualize_communities_2d(
            self,
            graph: nx.Graph,
            communities: Dict[int, int],
            title: str,
            output_path: Optional[str],
            layout: str,
    ) -> None:
        fig, ax = plt.subplots(figsize=self.figsize)
        pos = self._compute_layout(graph, layout)
        community_colors = self._build_community_colors(communities)
        community_markers = self._build_community_markers(communities)
        community_markers = self._build_community_markers(communities)

        nx.draw_networkx_edges(
            graph, pos,
            alpha=0.32,
            width=1.2,
            ax=ax
        )

        for community_id in sorted(set(communities.values())):
            nodes = [node for node in graph.nodes() if communities.get(node) == community_id]
            if not nodes:
                continue
            nx.draw_networkx_nodes(
                graph, pos,
                nodelist=nodes,
                node_color=[community_colors[community_id]],
                node_shape=community_markers[community_id],
                node_size=230,
                alpha=0.88,
                edgecolors="white",
                linewidths=0.8,
                ax=ax,
                label=f"社区 {community_id}",
            )

        ax.set_title(title, fontsize=18, fontweight='bold')
        ax.legend(loc="best", frameon=True, fontsize=15)
        ax.axis('off')
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {output_path}")
            plt.close(fig)
            return

        plt.show()

    def _visualize_communities_3d(
            self,
            graph: nx.Graph,
            communities: Dict[int, int],
            title: str,
            output_path: Optional[str],
    ) -> None:
        fig = plt.figure(figsize=self.figsize)
        ax = fig.add_subplot(111, projection="3d")
        pos = self._compute_layout(graph, "3d_spring")
        community_colors = self._build_community_colors(communities)

        for source, target in graph.edges():
            x_coords = [pos[source][0], pos[target][0]]
            y_coords = [pos[source][1], pos[target][1]]
            z_coords = [pos[source][2], pos[target][2]]
            ax.plot(x_coords, y_coords, z_coords, color="#7f8c8d", alpha=0.28, linewidth=1.2)

        for community_id in sorted(set(communities.values())):
            nodes = [node for node in graph.nodes() if communities.get(node) == community_id]
            if not nodes:
                continue
            ax.scatter(
                [pos[node][0] for node in nodes],
                [pos[node][1] for node in nodes],
                [pos[node][2] for node in nodes],
                c=[community_colors[community_id]],
                marker=community_markers[community_id],
                s=85,
                alpha=0.92,
                depthshade=True,
                edgecolors="white",
                linewidths=0.7,
                label=f"社区 {community_id}",
            )

        ax.set_title(title, fontsize=18, fontweight='bold')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        ax.grid(False)
        ax.view_init(elev=22, azim=38)
        ax.legend(loc="best", frameon=True, fontsize=15)

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {output_path}")
            plt.close(fig)
            return

        plt.show()

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
            layout: 布局方式 ('spring', 'circular', 'kamada_kawai', '3d_spring')
        """
        if layout == "3d_spring":
            self._visualize_communities_3d(graph, communities, title, output_path)
            return

        self._visualize_communities_2d(graph, communities, title, output_path, layout)

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
            plt.close(fig)
            return

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
            plt.close(fig)
            return

        plt.show()


from typing import Tuple
