# WeChat2Pdf (微信公众号试卷转 PDF)

这是一个全栈应用，专注于将微信公众号文章中的**试卷图片**智能提取并转换为干净、可打印的 PDF 文档。

禁止商用，禁止影响公众号正常运营。
仅分享，不提供任何形式的技术支持。

## ✨ 核心特性

- **智能去噪**: 使用 EAST 深度学习模型自动识别并移除文末广告、二维码和无关图片。
- **高质量输出**: 基于 Chrome 打印渲染或高性能 HTML 转换，保留文章原貌。
- **并发处理**: 基于 FastAPI 异步架构，支持多用户/多窗口同时提交任务，无需排队等待（注：暂不支持单次提交多个 URL）。
- **高性能架构**:
  - 后端: FastAPI (异步处理) + OpenCV (图像处理)
  - 前端: React + Vite + TailwindCSS
  - 部署: Docker Compose 或 Nginx + PM2

---

## 🚀 本地开发指南 (Local Development)

### 1. 环境要求
- Python 3.8+
- Node.js 16+
- Git

### 2. 快速启动
我们提供了一键启动脚本，自动安装依赖并同时运行前后端：

```bash
# 赋予脚本执行权限
chmod +x start_dev.sh

# 启动开发环境
./start_dev.sh
```

启动后访问：
- **前端页面**: http://localhost:5173
- **后端 API**: http://localhost:8000/docs

---

## ☁️ 云服务器部署指南 (推荐: Git 直连)

**这是最简单、最省心的部署方式 (特别是针对 2GB 内存服务器)。**
前端构建产物 (`frontend/dist`) 已经包含在代码仓库中，服务器**无需安装 Node.js，也无需进行构建**。

### 1. 准备工作 & 快速安装
为了解决国内服务器安装 Docker 困难的问题，我们在项目中内置了一个自动安装脚本。

请按顺序执行：

```bash
# 1. 克隆代码 (如果服务器没有 git，请先执行: sudo apt install git -y 或 sudo yum install git -y)
git clone https://github.com/hap042/Wechat2Pdf.git
cd Wechat2Pdf

# 2. 一键安装 Docker (自动配置阿里云源)
sudo bash install_docker.sh

# 3. 验证安装 (看到版本号即成功)
docker compose version
```

<details>
<summary>点击展开：Docker 手动安装步骤 (备选方案)</summary>

#### 方案 A：Ubuntu / Debian 系统 (阿里云源)
复制并执行以下所有命令：

```bash
# 1. 更新系统并安装必要工具
sudo apt-get update && sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# 2. 添加阿里云 GPG 密钥
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 3. 添加阿里云软件源
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. 安装 Docker
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 5. 启动 Docker 并设置开机自启
sudo systemctl start docker && sudo systemctl enable docker
```

#### 方案 B：CentOS / EulerOS 系统 (华为云/阿里云常用)
```bash
# 1. 安装工具
sudo yum install -y yum-utils

# 2. 添加阿里云源
sudo yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo

# 3. 安装 Docker
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 4. 启动并设置开机自启
sudo systemctl start docker && sudo systemctl enable docker
```
</details>

### 2. 启动服务
在 `Wechat2Pdf` 目录下，执行以下命令：

```bash
# 1. 一键启动 (Docker 会自动拉取 Python 环境并挂载内置的前端文件)
# 注意：新版 Docker 命令是 'docker compose' (中间有空格)，不是 'docker-compose'
docker compose up -d --build
```

### 3. (可选) 解决 Docker 镜像拉取失败
如果启动时报错 `connection refused` 或拉取镜像超时，这是因为国内访问 Docker Hub 受限。

我们提供了一键修复脚本：
```bash
# 运行镜像加速配置脚本
sudo bash fix_network.sh

# 然后再次尝试启动
docker compose up -d --build
```

### 4. 访问服务
服务启动后，Docker 会映射到宿主机的 **8080** 端口。
你可以通过 `http://服务器IP:8080/wechat2pdf` 访问。

### 5. (可选) 集成到现有 Nginx
如果你服务器上已经跑了 Nginx（占用了 80 端口），请在你的**宿主机 Nginx 配置**中添加：

```nginx
location /wechat2pdf {
    proxy_pass http://127.0.0.1:8080; # 转发给 Docker 容器
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

## 🛠 运维与常见问题 (FAQ)

### 1. 服务会断开吗？
**不会。**
Docker 容器是独立运行的守护进程。当你断开 SSH 连接（退出终端）时，服务**依然会在后台持续运行**。
即使服务器重启，Docker 也会根据 `restart: always` 策略自动重启你的服务。

### 2. 如何重启/停止服务？
```bash
# 进入项目目录
cd Wechat2Pdf

# 查看实时日志
docker compose logs -f

# 重启服务 (会重新加载配置)
docker compose restart

# 停止服务
docker compose stop

# 停止并删除容器 (不会删除数据)
docker compose down

# 更新代码并重新构建启动
git pull
docker compose up -d --build
```

### 3. 服务器重启了怎么办？
什么都不用做。
我们在 `docker-compose.yml` 中配置了 `restart: always`，服务器重启后 Docker 守护进程会自动把你的服务拉起来。

---

## ☁️ 其他部署方式 (PM2 + Nginx)

如果你不想使用 Docker，可以参考以下步骤直接在物理机/虚拟机上运行。

### 1. ⚠️ 低内存服务器特别说明 (2GB RAM)
对于 2GB 内存的服务器，请务必注意以下两点：
1.  **直接使用仓库中的 dist**：我们已经提交了构建好的前端文件，你**不需要**在服务器上运行 `npm install` 或 `npm run build`。
2.  **限制后端并发**：我们已经将 `ecosystem.config.js` 中的 `workers` 调整为 2。请不要随意增加，否则加载 AI 模型会导致内存耗尽。

### 2. 基础环境准备
```bash
# Ubuntu 示例
sudo apt update
sudo apt install python3-pip nginx git
# 安装 PM2
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2
```

### 3. 后端部署
```bash
git clone https://github.com/hap042/Wechat2Pdf.git
cd Wechat2Pdf

# 安装 Python 依赖
pip3 install -r requirements.txt

# 使用 PM2 启动后端服务 (已优化内存配置)
pm2 start ecosystem.config.js
pm2 save
```

### 4. 前端部署
无需做任何操作！代码仓库中已经包含了 `frontend/dist`。

### 5. Nginx 配置
编辑 Nginx 配置文件 (例如 `/etc/nginx/sites-available/wechat2pdf`):

```nginx
server {
    listen 80;
    server_name your_domain.com;  # 替换为你的域名或 IP

    # 前端静态文件 (直接指向仓库里的 dist 目录)
    location / {
        root /path/to/Wechat2Pdf/frontend/dist; # 替换为实际绝对路径
        index index.html;
        try_files $uri $uri/ /index.html;
        gzip_static on;
    }

    # 后端 API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }
}
```

**重启 Nginx**:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🛠 常用维护命令

- **Docker 方式**:
  - 查看日志: `docker compose logs -f`
  - 重启: `docker compose restart`
  - 停止: `docker compose down`

- **PM2 方式**:
  - 查看日志: `pm2 logs wechat2pdf-api`
  - 重启: `pm2 restart wechat2pdf-api`

- **更新代码**:
  - `cd ~/Wechat2Pdf`
  - `git pull`
  - `docker compose up -d --build`
  - 更改页面，拉取即可。更改后台代码后，需要重启 docker 服务。

