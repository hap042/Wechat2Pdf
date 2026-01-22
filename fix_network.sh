#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== 开始配置 Docker 国内镜像源加速 ===${NC}"

# 创建配置目录
sudo mkdir -p /etc/docker

# 写入镜像源配置
# 使用 DaoCloud, 百度云, 南京大学等稳定镜像
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://mirror.baidubce.com",
    "https://docker.nju.edu.cn",
    "https://dockerproxy.com"
  ]
}
EOF

echo -e "${GREEN}配置已写入 /etc/docker/daemon.json${NC}"

# 重启 Docker 服务
echo "正在重启 Docker 服务..."
sudo systemctl daemon-reload
sudo systemctl restart docker

echo -e "${GREEN}=== 配置完成！请重试启动命令 ===${NC}"
echo "建议运行: docker compose up -d --build"
