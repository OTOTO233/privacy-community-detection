# privacy-community-detection
# 隐私保护的社区检测系统

面向本科毕业设计的复杂网络分析与隐私计算融合项目。

本项目聚焦于“在不直接暴露原始网络结构的前提下，完成社区检测任务”这一问题，围绕多层网络场景设计并实现了一个集算法验证、隐私机制模拟、可视化展示和 Web 交互于一体的原型系统。项目既可用于算法实验，也适合作为课程设计或毕业答辩中的系统演示平台。

## 一、课题背景

在社交网络、通信网络和协作网络中，社区检测能够帮助识别节点之间的潜在组织结构，是复杂网络分析中的核心问题之一。但真实网络数据通常包含大量敏感关系信息，例如好友关系、通信联系和协作连接，若直接在明文图数据上进行社区检测，容易造成隐私泄露。

因此，本项目尝试将社区检测算法与隐私保护机制结合，构建一个“终端上传、云端协同、保护隐私、输出社区结构”的完整流程，用于验证隐私保护条件下社区检测的可行性与效果。

## 二、项目目标

本项目的目标不是单纯实现一个 Louvain 算法，而是完成一个更接近科研课题原型的系统，具体包括：

1. 实现适用于多层网络的社区检测流程。
2. 将差分隐私与同态加密机制引入检测流程中。
3. 建立终端、云服务器 1、云服务器 2 的三方协同架构。
4. 提供模块度、模块密度、NMI、隐私率等指标用于实验评估。
5. 提供基于 FastAPI + Vue 的前后端演示界面，支持答辩现场展示。

## 三、系统总体方案

项目整体围绕 PMCDM 实验框架展开，核心流程如下：

1. 用户上传图数据集。
2. 系统读取图结构并构造多层网络。
3. 终端侧对边权进行同态加密模拟。
4. 云服务器 1 对网络进行差分隐私扰动，并计算加密统计量。
5. 云服务器 2 在协同条件下执行 DH-Louvain 社区检测。
6. 系统输出社区划分结果、性能指标以及可视化图像。

对应代码实现位于：

- [main.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/main.py)
- [src/pmcdm/architecture.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/src/pmcdm/architecture.py)
- [src/pmcdm/experiment.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/src/pmcdm/experiment.py)
- [src/pmcdm/dh_louvain.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/src/pmcdm/dh_louvain.py)

## 四、核心模块

### 1. 社区检测模块

项目实现了基于多层网络的 `DH-Louvain` 检测流程，算法采用“两阶段贪心优化”思想：

- 阶段一：节点在候选社区之间移动，提升目标函数值。
- 阶段二：对已有社区进行进一步合并，提升整体划分质量。

该模块支持在多层图上使用加权模块度密度进行优化，能够较好体现多层网络条件下的社区结构特征。

### 2. 隐私保护模块

项目引入两类典型隐私保护技术：

- 差分隐私：通过扰动图结构，降低敏感边关系被直接恢复的风险。
- 同态加密：基于 Paillier 密码体制，对边权及统计量进行加密处理，模拟密文计算场景。

这两种机制分别对应“结构扰动保护”和“数据计算保护”，形成了较完整的隐私保护实验链路。

### 3. 实验评估模块

为了体现课题研究属性，项目实现了多种评价指标：

- `Q`：模块度，用于衡量社区划分质量。
- `D`：模块密度，用于衡量社区内部连接紧密程度。
- `NMI`：归一化互信息，用于评价与真实标签的接近程度。
- `pr`：隐私率，用于描述隐私保护效果。

此外，系统还支持多分辨率实验，可观察不同 `lambda` 参数下的社区划分变化。

### 4. Web 展示模块

项目提供简洁的前后端演示系统，支持：

- 选择 `Karate / AUCS / LFR / mLFR / BioGRID` 内置数据集，或上传 `txt / csv / npy / npz` 图数据；
- 设置隐私预算、失败概率、随机种子、算法、`lambda` 与布局方式；
- 为 `LFR / mLFR / BioGRID` 动态填写数据集参数；
- 执行社区检测；
- 展示图统计信息、层信息、社区数量和指标结果；
- 生成社区可视化图像。

这一部分适合答辩时进行现场演示。

## 五、项目创新点

相较于传统社区检测课程作业，本项目更强调“算法 + 架构 + 隐私机制 + 展示系统”的综合设计，主要体现在以下方面：

1. 将多层网络社区检测与隐私保护机制结合，而非单一算法复现。
2. 通过终端、云 1、云 2 的三方架构，体现隐私计算场景建模能力。
3. 不仅给出检测结果，还建立了较完整的指标评估体系。
4. 在实验脚本之外补充了 Web 化展示界面，更适合毕业答辩演示。

## 六、技术栈

### 后端与算法

- Python 3.9+
- NetworkX
- NumPy / Pandas / SciPy
- scikit-learn
- FastAPI
- Uvicorn

### 隐私计算

- diffprivlib
- python-paillier

### 前端展示

- Vue 3
- Axios
- 原生 HTML / CSS

## 七、项目结构

```text
privacy-community-detection/
├── src/
│   ├── backend.py                # FastAPI 后端接口
│   ├── data_processor.py         # 图数据读取与统计
│   ├── differential_privacy.py   # 差分隐私机制
│   ├── homomorphic_encryption.py # 同态加密机制
│   ├── visualization.py          # 可视化绘图
│   └── pmcdm/
│       ├── architecture.py       # 终端/云1/云2 架构模拟
│       ├── dh_louvain.py         # DH-Louvain 算法
│       ├── experiment.py         # 实验流程封装
│       └── metrics.py            # 评价指标计算
├── frontend/
│   └── index.html                # 答辩演示页面
├── main.py                       # 控制台实验入口
├── requirements.txt              # 项目依赖
└── README.md                     # 项目说明文档
```

## 八、运行方式

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行实验脚本

```bash
python main.py
```

该命令启动后会先询问实验数据集，目前支持 `Karate Club`、`AUCS`、`LFR Benchmark`、`mLFR Benchmark` 和 `BioGRID`。若选择 `LFR`，还可以继续选择“预设参数”或“手填参数”；若选择 `mLFR`，可以手填 `network_type / n / avg / max / mix / tau1 / tau2 / mincom / maxcom / l / dc / rc / mparam1 / on / om`；若选择 `BioGRID`，可以选择物种预设，并设置按 `Experimental System` 构造的层数、最小边数阈值以及 `max_nodes` 子图规模，随后输出不同算法下的 `Q / D / NMI / pr` 指标结果。

### 3. 启动后端服务

```bash
python -m uvicorn src.backend:app --reload --host 0.0.0.0 --port 8000
```

后端现在包含：

- `GET /datasets`：返回内置数据集、算法列表、LFR 预设和 BioGRID 物种目录；
- `POST /detect`：支持“内置数据集”或“上传文件”两种模式；
- `POST /visualize`：根据当前参数生成社区结构图像。

### 4. 打开前端页面

启动后端后，直接在浏览器中打开：

```text
frontend/index.html
```

前端页面已支持：

- 切换“内置数据集 / 上传文件”；
- 按数据集类型动态展示 `LFR / mLFR / BioGRID` 参数；
- 选择具体算法并查看单算法结果；
- 可选返回全算法对比表；
- 生成当前配置对应的可视化图像。

## 九、答辩演示建议

答辩现场可按以下顺序展示项目：

1. 介绍课题背景与研究意义。
2. 说明系统总体架构及三方协同流程。
3. 展示算法模块和隐私保护模块。
4. 运行 `main.py` 展示实验指标输出。
5. 启动前后端，上传示例数据并演示检测与可视化过程。
6. 总结项目创新点、实验效果与可改进方向。

## 十、后续可改进方向

目前项目已具备原型系统和答辩展示价值，后续仍可进一步增强：

1. 引入真实公开网络数据集开展更系统的对比实验。
2. 优化前后端联动细节，使指标展示更加完整。
3. 增加实验结果持久化与图表分析能力。
4. 将算法性能优化到更大规模图数据场景。
5. 增加论文所需的流程图、时序图和实验报告自动导出能力。

## 十一、参考文献

1. Blondel, V. D., Guillaume, J. L., Lambiotte, R., and Lefebvre, E. Fast unfolding of communities in large networks.
2. Dwork, C., and Roth, A. The algorithmic foundations of differential privacy.
3. Paillier, P. Public-key cryptosystems based on composite degree residuosity classes.

## 十二、作者信息

- 作者：OTOTO233
- 项目类型：本科毕业设计原型系统
- 许可证：MIT License

---

最后更新：2026-04-07
