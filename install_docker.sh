#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== 开始自动安装 Docker (阿里云镜像源) ===${NC}"

# 1. 检查是否已安装
if command -v docker &> /dev/null; then
    echo -e "${GREEN}Docker 已安装，跳过安装步骤。${NC}"
    docker --version
    docker compose version
    exit 0
fi

# 2. 检测系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    echo -e "${RED}无法检测系统版本，请手动安装。${NC}"
    exit 1
fi

echo -e "检测到操作系统: ${GREEN}$OS${NC}"

# 3. 根据系统执行安装
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    echo "正在 Ubuntu/Debian 上安装..."
    
    # 更新并安装必要工具
    sudo apt-get update
    sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

    # 添加阿里云 GPG 密钥
    curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # 添加阿里云源
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # 安装 Docker
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"EulerOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    echo "正在 CentOS/EulerOS/RHEL 上安装..."
    
    # 安装工具
    sudo yum install -y yum-utils

    # 添加阿里云源
    sudo yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo

    # 安装 Docker
    sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

else
    echo -e "${RED}不支持的系统: $OS${NC}"
    echo "请参考 README.md 中的手动安装步骤。"
    exit 1
fi

# 4. 启动服务
echo "正在启动 Docker 服务..."
sudo systemctl start docker
sudo systemctl enable docker

# 5. 验证
echo -e "${GREEN}=== 安装完成！ ===${NC}"
docker compose version
