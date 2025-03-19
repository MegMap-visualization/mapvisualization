## Some Services of The Map Cloud Powered by Python

MegMap Visualization 是一个用于自动驾驶地图数据处理和可视化的服务工具。

## 功能特性

### 1. 车道关键点提取（lane_key_point_extracter）

- 支持获取车道的前后第n个关键点(n=1~5)
- 支持多种坐标系(GCJ02/WGS84/UTM)
- 批量查询多个车道ID

### 2. 测试报告日志分析（log_extracter）

- 提取测试报告中的异常位置信息
- 支持坐标系自动转换
- 异常点可视化展示

### 3. 地图路由检查（map_routing_inspectors）

- 地图连通性分析
- 最大子图检测
- 孤立道路识别
- 多路径规划结果展示

### 4. Apollo地图数据处理（megmap_layer_data）

- 支持Apollo地图格式解析（apollo_elements）
- 多图层数据构建:（megmap_layer_builder）

  - 车道层(LANE)
  - 路口层(INTERSECTION)——junction
  - 停止线层(STOP_LINE)
  - 人行横道层(CROSSWALK)
  - 交通信号灯层(TRAFFIC_LIGHT)——signal
  - 车道连接层(LANE_CONNECTOR)——lane/link
  - 基准路径层(BASELINE_PATHS)
  - 地图边界层(BOUNDARIES)

## 技术架构

- **Web框架**: Flask
- **异步任务**: Celery
- **消息队列**: Redis
- **地理数据处理**:
  - GeoPandas
  - Shapely
  - UTM
- **配置中心**: Nacos
- **测试框架**: Pytest

## 快速开始

```bash

# 或者使用 flask 命令的 --app 参数
flask --app "megmap_viz:create_app" run --host=0.0.0.0 --port=5000
##flask run --host=0.0.0.0 --port=5000

# 启动Celery Worker: 进megmap_viz目录
celery -A megmap_viz.make_celery worker --loglevel INFO -P threads
```

#### 主要端点

```
dasd
http://mapvisualization-ebg-docs-test.mcd.megvii-inc.com/map-routing-inspector/all-submaps

http://mapvisualization-ebg-docs-test.mcd.megvii-inc.com/lane-key-point

http://mapvisualization-ebg-docs-test.mcd.megvii-inc.com/log-extracter
```
