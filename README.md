# privacy-community-detection

隐私保护的多层网络社区检测系统，本科毕业设计项目。

项目围绕“在不直接暴露原始网络结构的前提下完成社区检测”这一问题展开，结合多层网络建模、差分隐私、同态加密模拟、遗传算法参数优化和 Web 可视化界面，形成了一套可实验、可演示、可部署的原型系统。

## 项目特性

- 支持 `Karate / AUCS / LFR / mLFR / BioGRID` 等数据集
- 支持 `S-Louvain / PD-Louvain / R-Louvain / DP-Louvain / K-Louvain / DH-Louvain` 六种算法变体
- 提供 `Q / D / NMI / pr` 等评价指标
- 支持差分隐私拓扑扰动与 Paillier 同态加密模拟
- 提供遗传算法参数优化模块，用于搜索 `epsilon` 与 `lambda`
- 提供 `FastAPI + Vue` 前后端可视化系统
- 已完成云服务器部署验证，支持公网访问

## 系统结构

项目在逻辑上采用“三层协同”思路：

1. 终端侧负责数据上传与加密上传模拟
2. 云服务器 1 负责差分隐私扰动与加密统计
3. 云服务器 2 负责社区检测优化与指标输出

物理部署上，当前版本采用单机整合部署：

- `FastAPI + Uvicorn` 提供后端接口
- `nginx` 负责反向代理与前端静态资源发布
- `Vue` 前端提供交互式实验页面

## 核心模块

### 1. 社区检测

项目核心算法为 `DH-Louvain`，在 Louvain 两阶段贪心优化思想基础上，引入模块密度与多层网络信息，适用于隐私保护条件下的社区检测任务。

相关实现：

- [src/pmcdm/dh_louvain.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/src/pmcdm/dh_louvain.py)
- [src/pmcdm/s_louvain.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/src/pmcdm/s_louvain.py)
- [src/pmcdm/experiment.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/src/pmcdm/experiment.py)

### 2. 隐私保护

项目结合两类机制：

- 差分隐私：通过带噪边筛选对拓扑进行扰动
- 同态加密：基于 Paillier 体制模拟密文上传与密文统计

相关实现：

- [src/differential_privacy.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/src/differential_privacy.py)
- [src/homomorphic_encryption.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/src/homomorphic_encryption.py)
- [src/pmcdm/architecture.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/src/pmcdm/architecture.py)

### 3. 遗传算法优化

项目实现了基于遗传算法的参数搜索器，用于自动搜索 `epsilon` 与 `lambda`，提升隐私保护与社区检测性能之间的折中效果。

相关实现：

- [src/evolutionary_optimizer.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/src/evolutionary_optimizer.py)
- [scripts/run_ea_optimization.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/scripts/run_ea_optimization.py)
- [scripts/run_ea_before_after_compare.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/scripts/run_ea_before_after_compare.py)

### 4. Web 系统

后端提供统一的实验接口，前端提供三栏式实验页面，可完成：

- 选择内置数据集或上传图文件
- 动态配置 `LFR / mLFR / BioGRID` 参数
- 执行单算法检测与全算法对比
- 查看指标表格
- 生成静态图与 3D 交互可视化
- 运行遗传算法自动调参

相关实现：

- [src/backend_framework/routers.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/src/backend_framework/routers.py)
- [src/backend_framework/services.py](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/src/backend_framework/services.py)
- [frontend/src/App.vue](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/frontend/src/App.vue)

## 目录结构

```text
privacy-community-detection/
├── data/                         # 原始、处理后和生成型数据
├── deploy/                       # nginx、systemd 与云端部署脚本
├── frontend/                     # Vue 前端
├── output/                       # 实验结果、图表、论文导出文件
├── scripts/                      # 辅助实验与论文生成脚本
├── src/                          # 核心算法、后端与可视化实现
├── tests/                        # 测试代码
├── tools/                        # 相关工具与桥接目录
├── main.py                       # 控制台实验入口
├── requirements.txt              # Python 依赖
├── DEPLOYMENT.md                 # 云服务器部署说明
└── README.md
```

## 本地运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行控制台实验

```bash
python main.py
```

### 3. 启动后端

```bash
python -m uvicorn src.backend:app --reload --host 0.0.0.0 --port 8000
```

启动后可访问：

- `GET /datasets`
- `POST /detect`
- `POST /visualize`
- `POST /visualize3d`
- `POST /optimize/ea`
- `GET /docs`

### 4. 启动前端

```bash
cd frontend
npm install
npm run serve
```

开发模式下默认访问：

```text
http://127.0.0.1:8080
```

## 云服务器部署

项目已经完成腾讯云 Ubuntu 服务器部署验证，当前推荐部署形态为：

- 系统镜像：`Ubuntu 22.04 LTS`
- 运行方式：`Uvicorn + systemd + nginx`
- 前端：`Vue build 后静态发布`

部署相关文件：

- [DEPLOYMENT.md](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/DEPLOYMENT.md)
- [deploy/bootstrap_ubuntu.sh](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/deploy/bootstrap_ubuntu.sh)
- [deploy/systemd/privacy-community.service](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/deploy/systemd/privacy-community.service)
- [deploy/nginx/privacy-community.conf](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/deploy/nginx/privacy-community.conf)

如果项目代码已经上传到服务器，可直接执行：

```bash
sudo bash deploy/bootstrap_ubuntu.sh /opt/privacy-community-detection ubuntu 你的域名或公网IP
```

## 数据与实验

当前项目支持以下典型实验：

- `Karate / AUCS` 基准对比实验
- `BioGRID` 真实生物网络实验
- `LFR` 参数控制实验
- `BioGRID` 迭代次数实验
- 遗传算法优化前后对比实验

实验输出通常位于：

- `output/*.csv`
- `output/*.png`
- `output/*.md`
- `output/*.docx`

## 当前成果

截至当前版本，项目已经完成：

- 算法实现与多算法基线对比
- 前后端可视化系统开发
- 实验图表与论文生成辅助脚本
- 系统运行截图采集
- 云端部署验证
- 论文正文、图表、参考文献与格式对齐稿整理

## 后续可扩展方向

- 引入差分进化等更多参数优化算法
- 增强大规模图上的性能优化
- 增加结果缓存与任务队列
- 增加 HTTPS 与域名部署说明
- 增加更多真实网络数据集与对比实验

## 参考说明

项目用于毕业设计、课程展示和隐私保护社区检测实验验证。若你需要继续扩展部署、实验或论文输出，优先查看：

- [README.md](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/README.md)
- [DEPLOYMENT.md](/E:/360MoveData/Users/17598/Desktop/111/毕设/privacy-community-detection/DEPLOYMENT.md)

最后更新：2026-04-14
