# 云服务器部署说明

本文档说明如何把“隐私保护的多层网络社区检测系统”部署到一台 Linux 云服务器上，采用：

- `uvicorn` 运行 FastAPI 后端
- `nginx` 作为反向代理
- Vue 前端构建后作为静态文件发布

以下示例默认服务器系统为 `Ubuntu 22.04/24.04`，项目部署目录为：

```bash
/opt/privacy-community-detection
```

如果你的实际路径不同，只需要同步替换本文中的目录即可。

## 1. 服务器准备

更新系统并安装基础软件：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx git
```

可选但推荐安装构建前端所需的 Node.js：

```bash
sudo apt install -y nodejs npm
```

检查版本：

```bash
python3 --version
nginx -v
node -v
npm -v
```

如果你希望用一条命令完成大部分安装和配置，本仓库还提供了 Ubuntu 一键部署脚本：

```bash
sudo bash deploy/bootstrap_ubuntu.sh /opt/privacy-community-detection ubuntu 你的域名或公网IP
```

它会自动完成：

- 安装 Python、nginx、nodejs、npm
- 创建 `.venv` 并安装后端依赖
- 构建前端 `dist`
- 生成并安装 `systemd` 服务
- 生成并启用 `nginx` 站点配置

前提是你已经把项目代码完整上传到服务器目标目录。

## 2. 上传项目代码

把整个项目上传到服务器，例如：

```bash
sudo mkdir -p /opt/privacy-community-detection
sudo chown -R $USER:$USER /opt/privacy-community-detection
```

然后把本地项目内容复制到：

```bash
/opt/privacy-community-detection
```

建议至少保证以下内容完整上传：

- `src/`
- `frontend/`
- `data/`
- `requirements.txt`
- `main.py`

如果你要使用 BioGRID，请确认这个文件也已经上传：

```bash
data/BIOGRID-ORGANISM-LATEST.tab3.zip
```

## 3. 创建 Python 虚拟环境并安装依赖

进入项目目录：

```bash
cd /opt/privacy-community-detection
```

创建并激活虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

安装后端依赖：

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. 构建前端

进入前端目录：

```bash
cd /opt/privacy-community-detection/frontend
```

安装依赖并构建：

```bash
npm install
npm run build
```

构建完成后，静态文件会位于：

```bash
/opt/privacy-community-detection/frontend/dist
```

## 5. 先手动启动后端测试

回到项目根目录：

```bash
cd /opt/privacy-community-detection
source .venv/bin/activate
```

启动 FastAPI：

```bash
python -m uvicorn src.backend:app --host 127.0.0.1 --port 8000
```

此时可以在服务器本机测试：

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/framework/architecture
```

如果有返回 JSON，说明后端工作正常。

## 6. 配置 systemd 守护后端

把仓库中的服务文件复制到系统目录：

```bash
sudo cp deploy/systemd/privacy-community.service /etc/systemd/system/
```

打开文件检查并按实际情况修改这两项：

- `User=ubuntu`
- `WorkingDirectory=/opt/privacy-community-detection`

如果你的部署用户不是 `ubuntu`，要改成自己的用户。

然后重新加载并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable privacy-community
sudo systemctl start privacy-community
```

查看状态：

```bash
sudo systemctl status privacy-community
```

查看日志：

```bash
sudo journalctl -u privacy-community -f
```

## 7. 配置 nginx

把示例配置复制到 nginx：

```bash
sudo cp deploy/nginx/privacy-community.conf /etc/nginx/sites-available/privacy-community
```

按实际情况修改：

- `server_name your-server-domain-or-ip;`
- 前端目录 `/opt/privacy-community-detection/frontend/dist`
- 项目目录 `/opt/privacy-community-detection`

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/privacy-community /etc/nginx/sites-enabled/privacy-community
```

检查 nginx 配置：

```bash
sudo nginx -t
```

重启 nginx：

```bash
sudo systemctl restart nginx
```

## 8. 开放端口

如果服务器启用了防火墙，开放 `80` 端口：

```bash
sudo ufw allow 80/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

云平台安全组也要放行：

- `22`
- `80`

如果你后面要上 HTTPS，再额外放行：

- `443`

## 9. 部署后的访问方式

部署完成后，访问：

```text
http://你的域名或公网IP/
```

后端接口会由 nginx 反代到：

```text
http://127.0.0.1:8000
```

前端的 `/api/*` 请求也会被 nginx 转发到后端。

## 10. 更新项目

更新代码后，推荐按这个顺序执行：

```bash
cd /opt/privacy-community-detection
source .venv/bin/activate
pip install -r requirements.txt
```

如果前端有更新：

```bash
cd /opt/privacy-community-detection/frontend
npm install
npm run build
```

最后重启后端：

```bash
sudo systemctl restart privacy-community
sudo systemctl restart nginx
```

## 11. 常见问题

### 1. 前端能打开，但接口报错

先检查后端服务：

```bash
sudo systemctl status privacy-community
sudo journalctl -u privacy-community -n 100
```

### 2. nginx 启动失败

检查配置语法：

```bash
sudo nginx -t
```

### 3. BioGRID 无法读取

确认数据文件已经上传：

```bash
ls /opt/privacy-community-detection/data/BIOGRID-ORGANISM-LATEST.tab3.zip
```

### 4. AUCS 可视化失败

确认 AUCS 处理后数据存在：

```bash
ls /opt/privacy-community-detection/data/processed/aucs
```

## 12. 当前部署形态说明

这套框架目前是：

- 逻辑上分为：本地多层系统、云服务器1、云服务器2
- 物理上部署为：一个统一的 FastAPI 单体服务

这非常适合：

- 毕业设计演示
- 云服务器快速部署
- 后端统一运维

如果后续你需要，我还可以继续帮你补：

- `HTTPS + Certbot`
- `Dockerfile`
- `docker-compose.yml`
- 多机拆分版部署方案
