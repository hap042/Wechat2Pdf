# WeChat2Pdf (微信公众号文章转 PDF)

这是一个全栈应用，旨在将微信公众号文章智能转换为干净、可打印的 PDF 文档。

## ✨ 核心特性

- **智能去噪**: 使用 EAST 深度学习模型自动识别并移除文末广告、二维码和无关图片。
- **高质量输出**: 基于 Chrome 打印渲染或高性能 HTML 转换，保留文章原貌。
- **批量处理**: 支持同时处理多个 URL。
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

## ☁️ 云服务器部署指南 (Docker 推荐)

**这是最推荐的部署方式，特别是对于 2GB 内存的服务器。**
我们使用 Docker 容器化部署，不仅环境隔离，而且可以避免在服务器上进行高内存消耗的构建操作。

### 1. 准备工作
在**本地机器**上构建前端（避免在服务器上运行 npm install/build 消耗内存）：
```bash
cd frontend
npm install
npm run build
# 此时会生成 dist 目录
```

### 2. 上传文件到服务器
将整个项目（包含本地生成的 `frontend/dist`）上传到服务器。

### 3. 服务器端启动
确保服务器已安装 `docker` 和 `docker-compose`。

```bash
# 在服务器项目根目录下运行
docker-compose up -d --build
```

### 3. 访问
服务启动后，Docker 会映射到宿主机的 **8080** 端口。
你可以通过 `http://服务器IP:8080/wechat2pdf` 访问。

### 4. (可选) 集成到现有 Nginx
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

# 重启服务 (会重新加载配置)
docker-compose restart

# 停止服务
docker-compose stop

# 停止并删除容器 (不会删除数据)
docker-compose down

# 更新代码并重新构建启动
git pull
docker-compose up -d --build
```

### 3. 服务器重启了怎么办？
什么都不用做。
我们在 `docker-compose.yml` 中配置了 `restart: always`，服务器重启后 Docker 守护进程会自动把你的服务拉起来。

---

## ☁️ 云服务器部署指南 (Docker 手动构建前端)

如果你不想使用 Docker，可以参考以下步骤。

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
  - 查看日志: `docker-compose logs -f`
  - 重启: `docker-compose restart`
  - 停止: `docker-compose down`

- **PM2 方式**:
  - 查看日志: `pm2 logs wechat2pdf-api`
  - 重启: `pm2 restart wechat2pdf-api`
