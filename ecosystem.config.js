module.exports = {
  apps: [{
    name: 'wechat2pdf-api',
    script: 'python3',
    args: '-m uvicorn backend.api:app --host 127.0.0.1 --port 8000 --workers 4',
    cwd: __dirname,
    interpreter: 'none',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      PYTHONUNBUFFERED: '1'
    }
  }]
};
