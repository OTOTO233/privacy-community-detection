# privacy-community-detection
# 🔐 隐私保护的社区检测系统

Privacy-Preserving Community Detection System

## 📋 项目介绍

基于隐私保护的复杂社区检测系统是一个整合了图论、社区检测算法和隐私保护技术的综合系统。该项目实现了以下核心功能：

### ✨ 核心特性

1. **莱顿社区检测算法 (Louvain Algorithm)**
   - 基于模块度优化的贪心算法
   - 支持加权和无权图
   - 高效的社区检测

2. **差分隐私 (Differential Privacy)**
   - 拉普拉斯机制 (Laplace Mechanism)
   - 高斯机制 (Gaussian Mechanism)
   - 指数机制 (Exponential Mechanism)
   - 隐私预算控制

3. **同态加密 (Homomorphic Encryption)**
   - 基于 Paillier 密码系统
   - 支持在加密数据上进行运算
   - 加法和乘法同态性质

4. **数据处理**
   - 支持多种格式 (CSV, TXT, NPY)
   - 自动格式检测
   - 图统计信息计算

5. **可视化模块**
   - 社区检测结果可视化
   - 多种布局算法 (Spring, Circular, Kamada-Kawai)
   - 统计信息展示

6. **Web 前端**
   - 基于 Vue.js 的交互界面
   - 支持数据集上传
   - 实时参数调整
   - 图像生成与下载

## 🚀 快速开始

### 环境要求

- Python >= 3.9
- pip 或 conda

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行示例

```bash
python main.py
```

### 启动后端服务

```bash
python -m uvicorn src.backend:app --reload --host 0.0.0.0 --port 8000
```

### 访问前端

在浏览器中打开 `frontend/index.html`

## 📚 使用示例

### Python 脚本使用

```python
import networkx as nx
from src.louvain_algorithm import LouvainDetector
from src.differential_privacy import DifferentialPrivacy
from src.visualization import Visualizer

# 创建示例图
G = nx.karate_club_graph()

# 社区检测
detector = LouvainDetector()
communities = detector.detect(G)

# 应用差分隐私
dp = DifferentialPrivacy(epsilon=1.0)
private_communities = dp.privatize_community_assignment(communities)

# 可视化
visualizer = Visualizer()
visualizer.visualize_communities(G, communities)
```

### REST API 使用

```bash
# 上传文件并执行检测
curl -F "file=@data.txt" http://localhost:8000/detect

# 生成可视化
curl -F "file=@data.txt" http://localhost:8000/visualize -o output.png
```

## 📁 项目结构

```
privacy-community-detection/
├── src/
│   ├── __init__.py
│   ├── louvain_algorithm.py      # 莱顿算法
│   ├── differential_privacy.py   # 差分隐私
│   ├── homomorphic_encryption.py # 同态加密
│   ├── data_processor.py         # 数据处理
│   ├── visualization.py          # 可视化
│   └── backend.py                # FastAPI 后端
├── frontend/
│   └── index.html                # Web 前端
├── tests/
│   └── test_algorithms.py        # 单元测试
├── data/
│   └── .gitkeep                  # 数据集目录
├── docs/
│   └── .gitkeep                  # 文档目录
├── main.py                       # 主程序入口
├── requirements.txt              # 依赖清单
├── .gitignore                    # Git 忽略配置
└── README.md                     # 项目文档
```

## 🔧 API 接口

### 社区检测接口

**POST** `/detect`

请求参数：
- `file`: 数据文件 (Form Data)
- `epsilon`: 隐私预算 (可选, 默认: 1.0)
- `delta`: 失败概率 (可选, 默认: 1e-5)
- `use_encryption`: 是否使用加密 (可选, 默认: false)
- `random_state`: 随机种子 (可选, 默认: 42)

响应格式：
```json
{
  "communities": {
    "0": 0,
    "1": 0,
    "2": 1,
    ...
  },
  "statistics": {
    "num_communities": 3,
    "modularity": 0.4231,
    "avg_community_size": 12.5,
    "max_community_size": 20,
    "min_community_size": 5
  },
  "graph_info": {
    "num_nodes": 34,
    "num_edges": 78,
    "density": 0.1343,
    "avg_degree": 4.58
  }
}
```

### 可视化接口

**POST** `/visualize`

请求参数：
- `file`: 数据文件 (Form Data)
- `format`: 布局方式 (可选, 默认: spring)

响应：PNG 图像

## 📊 数据格式

### 边列表格式 (.txt, .csv)

```
source target [weight]
0      1      1.0
0      2      0.5
1      2      1.0
...
```

### 邻接矩阵格式 (.npy)

```
NumPy 数组格式的邻接矩阵
```

## 🔐 隐私保护机制

### 差分隐私参数

- **ε (epsilon)**: 隐私预算
  - 值越小，隐私保护越强
  - 值越大，数据有用性越高
  - 推荐范围: 0.1 ~ 10

- **δ (delta)**: 失败概率
  - 失败的概率上界
  - 推荐值: 1e-5 ~ 1e-3

## 🧪 测试

```bash
pytest tests/
```

## 📝 文献参考

1. Blondel, V. D., et al. (2008). "Fast unfolding of communities in large networks." 
   Journal of statistical mechanics: theory and experiment, 2008(10), P10008.

2. Dwork, C., & Roth, A. (2014). "The algorithmic foundations of differential privacy." 
   Foundations and Trends in Theoretical Computer Science, 9(3-4), 211-407.

3. Paillier, P. (1999). "Public-key cryptosystems based on composite degree residuosity classes." 
   In International Conference on the Theory and Applications of Cryptographic Techniques (pp. 223-238).

## 📄 许可证

MIT License

## 👨‍💻 作者

OTOTO233

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 联系方式

如有问题，请在 GitHub 上提交 Issue。

---

**最后更新**: 2026-03-08
