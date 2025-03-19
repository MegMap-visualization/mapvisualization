#!/bin/bash
set -e

echo "Starting entrypoint script..."

# 创建非root用户
if ! id "megmap" &>/dev/null; then
    echo "Creating user megmap..."
    groupadd -r megmap && useradd -r -g megmap megmap
else
    echo "User megmap already exists."
fi

# 创建并设置必要目录的权限
echo "Creating and setting permissions for directories..."
mkdir -p /data/cache /data/uploads /var/log/celery /var/run/celery
chown -R megmap:megmap /data /app /var/log/celery /var/run/celery
chmod 755 /data /data/cache /data/uploads

# 启动 Redis 服务
echo "Starting Redis server..."
redis-server --daemonize yes

# 检查 Redis 是否启动成功
if redis-cli ping | grep -q "PONG"; then
    echo "Redis server is running."
else
    echo "Failed to start Redis server."
    exit 1
fi

# 先尝试直接导入 Flask 应用
echo "Testing Flask app import..."
su megmap -c "PYTHONPATH=/app python3 -c 'from megmap_viz import create_app; app=create_app()'" || {
    echo "Failed to import Flask application"
    exit 1
}

# 使用非root用户启动 Celery Worker
echo "Starting Celery worker..."
su megmap -c "cd /app && PYTHONPATH=/app celery -A megmap_viz.make_celery worker \
    --loglevel DEBUG \
    -P threads \
    --max-memory-per-child=3000000 \
    --max-tasks-per-child=10 \
    --concurrency=1 \
    --pidfile=/var/run/celery/celery.pid \
    --logfile=/var/log/celery/celery.log" &

# 使用非root用户启动 Flask 应用
echo "Starting Flask application with Gunicorn..."
exec su megmap -c "cd /app && PYTHONPATH=/app gunicorn \
    --workers 2 \
    --threads 2 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --log-level debug \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --reload \
    --preload \
    --limit-request-line 40940 \
    'megmap_viz:create_app()' \
    -b 0.0.0.0:5000 2>&1 | tee /var/log/gunicorn.log"
