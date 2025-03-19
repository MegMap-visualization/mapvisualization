FROM python:3.9

USER root
WORKDIR /app

# 配置pip源
RUN pip config set global.index-url http://mirrors.i.brainpp.cn/pypi/simple/ && \
    pip config set global.extra-index-url "http://pypi.i.brainpp.cn/brain/dev/+simple" && \
    pip config set global.trusted-host "mirrors.i.brainpp.cn pypi.i.brainpp.cn"

# 先安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    gdal-bin \
    libgdal-dev \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# 设置 GDAL 环境变量
ENV GDAL_VERSION=3.0.4 \
    CPLUS_INCLUDE_PATH=/usr/include/gdal \
    C_INCLUDE_PATH=/usr/include/gdal

# 预先安装 pyproj
RUN pip install --no-cache-dir pyproj==3.6.0

# 安装 poetry
RUN pip install --no-cache-dir poetry

# 复制项目文件
COPY . /app/

# 安装依赖
RUN poetry config virtualenvs.create false && \
    poetry config installer.max-workers 1 && \
    poetry install --no-interaction --no-ansi --no-cache

# 创建非root用户
RUN groupadd -r megmap && useradd -r -g megmap megmap && \
    chown -R megmap:megmap /app

# 暴露端口
EXPOSE 5000

# 启动脚本
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
