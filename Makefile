# 变量定义
APP_NAME = mapvisualization
REGISTRY = mcd.io/mcd-apps/mapvisualization-mach-galaxy-test
IMAGE_NAME = $(REGISTRY)
TAG ?= latest
BRANCH ?= $(shell git rev-parse --abbrev-ref HEAD)

.PHONY: build push deploy clean all help

build:
	docker build -t $(IMAGE_NAME):$(TAG) .

push:
	docker push $(IMAGE_NAME):$(TAG)

deploy:
	mcd deploy -f appci/app-dev.yaml

clean:
	-docker rmi $(IMAGE_NAME):$(TAG)

all: build push deploy

help:
	@echo "可用的命令:"
	@echo "  build   - 构建 Docker 镜像"
	@echo "  push    - 推送镜像到仓库"
	@echo "  deploy  - 部署到 MCD"
	@echo "  clean   - 清理本地构建"
	@echo "  all     - 执行构建、推送和部署"
