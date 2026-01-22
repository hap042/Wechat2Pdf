# 使用官方 Python 轻量级镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 优化国内网络环境 (替换 apt 和 pip 源)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 安装系统依赖 (OpenCV 需要 libgl1)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY backend/ ./backend/
COPY models/ ./models/

# 暴露端口
EXPOSE 8000

# 启动命令 (使用 2 个 workers 适配低内存环境)
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
