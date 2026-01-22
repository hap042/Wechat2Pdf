#!/bin/bash
set -e

echo "=== 开始构建 PDFCraft ==="

# 1. Build Frontend
echo "[1/4] 构建前端..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build
cd ..

# 2. Prepare Output Directory
echo "[2/4] 准备发布目录..."
rm -rf release
mkdir -p release/backend
mkdir -p release/static

# 3. Copy Backend Files
echo "[3/4] 复制后端文件..."
cp -r backend release/backend/
cp -r models release/backend/
cp requirements.txt release/backend/

# Create a start script for backend
cat > release/backend/start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
# Install dependencies if needed (optional, better to do manually)
# pip install -r requirements.txt
export PYTHONPATH=$PYTHONPATH:$(pwd)
exec uvicorn backend.api:app --host 0.0.0.0 --port 8000 --workers 4
EOF
chmod +x release/backend/start.sh

# 4. Copy Static Files
echo "[4/4] 复制静态资源..."
cp -r frontend/dist/* release/static/

# 5. Create Nginx Config Example
cat > release/nginx_pdfcraft.conf << 'EOF'
server {
    listen 80;
    server_name your_domain.com;  # 修改为你的域名或 IP

    root /path/to/pdfcraft/static;  # 修改为实际的 static 目录路径
    index index.html;

    # 前端静态文件
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # 增加超时时间，防止生成大文件时超时
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }
}
EOF

echo "=== 构建完成 ==="
echo "发布文件已生成在 'release/' 目录。"
echo "请查看 release/README.txt 获取部署说明。"

# Create README for deployment
cat > release/README.txt << 'EOF'
=== PDFCraft 部署说明 ===

项目包含两部分：
1. static/: 前端静态网页文件
2. backend/: Python 后端服务

## 部署步骤

### 1. 后端部署 (Python)
1. 将 backend 目录上传到服务器。
2. 安装依赖:
   cd backend
   pip install -r requirements.txt
3. 启动服务 (建议使用 supervisor 或 systemd 托管):
   ./start.sh
   (服务将运行在 8000 端口)

### 2. 前端部署 (Nginx)
1. 将 static 目录上传到服务器 (例如 /var/www/pdfcraft)。
2. 参考 nginx_pdfcraft.conf 配置你的 Nginx。
   - 修改 server_name
   - 修改 root 路径指向你的 static 目录
3. 重载 Nginx: sudo nginx -s reload

### 3. 验证
访问你的域名/IP，应该能看到界面。尝试转换一个文章链接。
EOF
