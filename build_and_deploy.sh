#!/bin/bash

# Exit on error
set -e

echo "=================================================="
echo "      WeChat Article to PDF - Deployment Build    "
echo "=================================================="

# 1. Install Backend Dependencies
echo "[1/3] Installing Backend Dependencies..."
pip install -r requirements.txt
# Ensure uvicorn is installed (it's in requirements.txt but good to double check)
pip install uvicorn

# 2. Build Frontend
echo "[2/3] Building Frontend..."
cd frontend
echo "Installing npm packages..."
npm install
echo "Building for production (Base: /wechat2pdf/)..."
npm run build
cd ..

# 3. Setup PM2
echo "[3/3] Setting up PM2..."

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    echo "PM2 not found. Please install it globally: npm install -g pm2"
    echo "Skipping PM2 start."
else
    echo "Starting/Reloading application with PM2..."
    pm2 start ecosystem.config.js
    pm2 save
    echo "PM2 configuration saved."
fi

echo "=================================================="
echo "✅ Build Complete!"
echo ""
echo "Next Steps:"
echo "1. Configure Nginx using the snippet in 'nginx.conf.snippet'"
echo "   (Make sure to update the 'alias' path in the config)"
echo "2. Reload Nginx: sudo systemctl reload nginx"
echo "3. Access your app at: http://YOUR_SERVER_IP/wechat2pdf"
echo "=================================================="
