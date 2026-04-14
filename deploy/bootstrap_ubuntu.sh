#!/usr/bin/env bash
set -euo pipefail

# 用法：
# sudo bash deploy/bootstrap_ubuntu.sh /opt/privacy-community-detection ubuntu your-domain-or-ip
#
# 参数：
#   $1 部署目录
#   $2 运行服务的 Linux 用户
#   $3 server_name（域名或公网 IP）

APP_DIR="${1:-/opt/privacy-community-detection}"
APP_USER="${2:-ubuntu}"
SERVER_NAME="${3:-_}"

if [[ ! -d "$APP_DIR" ]]; then
  echo "部署目录不存在: $APP_DIR"
  echo "请先把项目代码上传到服务器。"
  exit 1
fi

echo "[1/7] 安装系统依赖"
apt update
apt install -y python3 python3-venv python3-pip nginx nodejs npm

echo "[2/7] 创建 Python 虚拟环境并安装依赖"
cd "$APP_DIR"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "[3/7] 构建前端"
cd "$APP_DIR/frontend"
npm install
npm run build

echo "[4/7] 生成 systemd 服务文件"
SERVICE_SRC="$APP_DIR/deploy/systemd/privacy-community.service"
SERVICE_TMP="/tmp/privacy-community.service"
sed \
  -e "s|User=ubuntu|User=$APP_USER|g" \
  -e "s|WorkingDirectory=/opt/privacy-community-detection|WorkingDirectory=$APP_DIR|g" \
  -e "s|ExecStart=/opt/privacy-community-detection/.venv/bin/python|ExecStart=$APP_DIR/.venv/bin/python|g" \
  "$SERVICE_SRC" > "$SERVICE_TMP"
cp "$SERVICE_TMP" /etc/systemd/system/privacy-community.service

echo "[5/7] 生成 nginx 配置"
NGINX_SRC="$APP_DIR/deploy/nginx/privacy-community.conf"
NGINX_TMP="/tmp/privacy-community.conf"
sed \
  -e "s|your-server-domain-or-ip|$SERVER_NAME|g" \
  -e "s|/opt/privacy-community-detection/frontend/dist|$APP_DIR/frontend/dist|g" \
  "$NGINX_SRC" > "$NGINX_TMP"
cp "$NGINX_TMP" /etc/nginx/sites-available/privacy-community
ln -sf /etc/nginx/sites-available/privacy-community /etc/nginx/sites-enabled/privacy-community
rm -f /etc/nginx/sites-enabled/default

echo "[6/7] 启动并设置开机自启"
systemctl daemon-reload
systemctl enable privacy-community
systemctl restart privacy-community
nginx -t
systemctl restart nginx

echo "[7/7] 完成"
echo "后端状态："
systemctl --no-pager --full status privacy-community | head -n 20 || true
echo
echo "访问地址： http://$SERVER_NAME/"
echo "接口文档： http://$SERVER_NAME/docs"
