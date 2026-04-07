"""
主程序入口
"""

import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.louvain_algorithm import LouvainDetector
from src.data_processor import DataProcessor
from src.differential_privacy import DifferentialPrivacy
from src.homomorphic_encryption import HomomorphicEncryption
from src.visualization import Visualizer


def main():
    """主程序"""
    print("=" * 60)
    print("隐私保护的社区检测系统 v0.1.0")
    print("=" * 60)
    print()

    # 示例：使用演示数据集
    print("📂 创建示例数据集...")

    # 创建示例图
    import networkx as nx
    G = nx.karate_club_graph()

    print(f"✓ 加载示例图")
    print(f"  - 节点数: {G.number_of_nodes()}")
    print(f"  - 边数: {G.number_of_edges()}")

    # 执行社区检测
    print("\n🔍 执行莱顿社区检测...")
    detector = LouvainDetector(random_state=42)
    communities = detector.detect(G)
    statistics = detector.get_statistics()

    print(f"✓ 检测完成")
    print(f"  - 检测到 {statistics['num_communities']} 个社区")
    print(f"  - 模块度: {statistics['modularity']:.4f}")
    print(f"  - 平均社区大小: {statistics['avg_community_size']:.2f}")

    # 应用差分隐私
    print("\n🔐 应用差分隐私...")
    dp = DifferentialPrivacy(epsilon=1.0, delta=1e-5)
    private_communities = dp.privatize_community_assignment(communities)
    print(f"✓ 差分隐私已应用 (ε={dp.epsilon}, δ={dp.delta})")

    # 初始化同态加密
    print("\n🔒 初始化同态加密...")
    he = HomomorphicEncryption(key_size=2048)
    print(f"✓ 同态加密密钥已生成")

    # 生成可视化
    print("\n🎨 生成可视化...")
    visualizer = Visualizer()
    visualizer.visualize_communities(
        G, communities,
        title="Karate Club Network - Community Detection",
        output_path="output/community_visualization.png"
    )
    print(f"✓ 可视化已保存到 output/community_visualization.png")

    print("\n" + "=" * 60)
    print("✅ 演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()