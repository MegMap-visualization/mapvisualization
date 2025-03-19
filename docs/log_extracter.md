# Test Report Log Extracter 接口文档

## /log-extracter [GET]

该接口用于获取测试报告中的异常位置的坐标点和错误信息。

请求参数：

- log_s3_path: 测试报告路径, 例如: s3://xxx.json
- auxilary_point: 辅助点坐标, 用来将测试报告中的utm坐标点转换为gcj坐标点，例如：116.397627,39.908656；格式是 `gcj_lon,gcj_lat`，其中gcj_lon和gcj_lat是经过gcj02坐标系转换后的坐标点，两者用英文逗号分割，**从加载的地图中随便取一个点即可**。

请求示例：

http://xxxx/log-extracter?log_s3_path=s3://tjc/tempcode/temp_res.json&auxilary_point=116.28342692091731,39.85008608516268

返回数据：

|字段名|类型|描述|
|:-:|:-:|:-:|
|abnormal_acceleration|object|加速度异常位置|
|+name|str|前端列表渲染应该展示的名字|
|+color|str|该数据需要渲染的颜色|
|+points|list[object]|异常位置的坐标点信息|
|++gcj_lat|number|gcj纬度|
|++gcj_lon|number|gcj经度|
|++utm_x|number|Easting value of UTM coordinates|
|++utm_y|number|Northing value of UTM coordinates|
|++wgs84_lat|number|wgs84纬度|
|++wgs84_lon|number|wgs84经度|
| | | |
|digression|object|偏离路线位置|
|+name|str|前端列表渲染应该展示的名字|
|+color|str|该数据需要渲染的颜色|
|+points|list[object]|异常位置的坐标点信息|
|++gcj_lat|number|gcj纬度|
|++gcj_lon|number|gcj经度|
|++utm_x|number|Easting value of UTM coordinates|
|++utm_y|number|Northing value of UTM coordinates|
|++wgs84_lat|number|wgs84纬度|
|++wgs84_lon|number|wgs84经度|
| | | |
|ego_stop_pos|object|自车停止位置|
|+name|str|前端列表渲染应该展示的名字|
|+color|str|该数据需要渲染的颜色|
|+points|list[object]|异常位置的坐标点信息|
|++gcj_lat|number|gcj纬度|
|++gcj_lon|number|gcj经度|
|++utm_x|number|Easting value of UTM coordinates|
|++utm_y|number|Northing value of UTM coordinates|
|++wgs84_lat|number|wgs84纬度|
|++wgs84_lon|number|wgs84经度|
| | | |
|non-stop|object|未停车位置|
|+name|str|前端列表渲染应该展示的名字|
|+color|str|该数据需要渲染的颜色|
|+points|list[object]|异常位置的坐标点信息|
|++gcj_lat|number|gcj纬度|
|++gcj_lon|number|gcj经度|
|++utm_x|number|Easting value of UTM coordinates|
|++utm_y|number|Northing value of UTM coordinates|
|++wgs84_lat|number|wgs84纬度|
|++wgs84_lon|number|wgs84经度|
| | | |
|overspeed|object|超速位置|
|+name|str|前端列表渲染应该展示的名字|
|+color|str|该数据需要渲染的颜色|
|+points|list[object]|异常位置的坐标点信息|
|++gcj_lat|number|gcj纬度|
|++gcj_lon|number|gcj经度|
|++utm_x|number|Easting value of UTM coordinates|
|++utm_y|number|Northing value of UTM coordinates|
|++wgs84_lat|number|wgs84纬度|
|++wgs84_lon|number|wgs84经度|
| | | |
|stop|object|停车位置|
|+name|str|前端列表渲染应该展示的名字|
|+color|str|该数据需要渲染的颜色|
|+points|list[object]|异常位置的坐标点信息|
|++gcj_lat|number|gcj纬度|
|++gcj_lon|number|gcj经度|
|++utm_x|number|Easting value of UTM coordinates|
|++utm_y|number|Northing value of UTM coordinates|
|++wgs84_lat|number|wgs84纬度|
|++wgs84_lon|number|wgs84经度|
| | | |
|lowspeed|object|低速位置|
|+name|str|前端列表渲染应该展示的名字|
|+color|str|该数据需要渲染的颜色|
|+points|list[object]|异常位置的坐标点信息|
|++gcj_lat|number|gcj纬度|
|++gcj_lon|number|gcj经度|
|++utm_x|number|Easting value of UTM coordinates|
|++utm_y|number|Northing value of UTM coordinates|
|++wgs84_lat|number|wgs84纬度|
|++wgs84_lon|number|wgs84经度|

返回示例：

```json
{
    "abnormal_acceleration": {
        "color": "#ff7b00",
        "name": "加速度异常位置",
        "points": [
        {
            "gcj_lat": 40.004776978576345,
            "gcj_lon": 116.36776187023592,
            "utm_x": 445504.1224506387,
            "utm_y": 4428330.016701728,
            "wgs84_lat": 40.00340220307518,
            "wgs84_lon": 116.36154433037845
        },
        {
            "gcj_lat": 40.0051744682138,
            "gcj_lon": 116.36747001561528,
            "utm_x": 445479.56754623755,
            "utm_y": 4428374.359175402,
            "wgs84_lat": 40.00380010982225,
            "wgs84_lon": 116.36125294717036
        },
        ...
        ]
    },
    ...
}
```