# 车道关键点查询接口文档

## /lane-key-point [GET]

该接口用于获取查询车道的前后第n个点，比如获取车道的前后第3个点，n范围为[1,5]。

查询参数:

- map_path: 地图路径, 例如: s3://xxx.xml
- map_md5: 地图文件md5，例如：sgsdget823r9jslkdgjckgskggg
- lane_uid_list：需要查询的车道uid，例如：13535547Ac845f_0_-1,Way10034_0_-1,Way10034_1_-1
- idx(可选): 需要查询的车道的第几个点，默认为3，范围为[1,5]

请求示例：

http://xxxx/lane-key-point?map_path=/home/u2004/MegviiProjects/ame_ws/mapviz/map-py-utils-client/tests/data/beijing_0710.xml&map_md5=e0f1bc93e8f94b74241d4df4b794f9fb&lane_uid_list=13252313Ad99d4_0_-1

返回数据：

|字段名|类型|描述|
|:-:|:-:|:-:|
|[lane_uid]|str|车道uid|
|+head|object|车道首部第idx个点，默认为第3个点|
|++gcj_lat|number|gcj纬度|
|++gcj_lon|number|gcj经度|
|++utm_x|number|Easting value of UTM coordinates|
|++utm_y|number|Northing value of UTM coordinates|
|++wgs84_lat|number|wgs84纬度|
|++wgs84_lon|number|wgs84经度|
|+tail|object|车道尾部第idx个点，默认为倒数第3个点|
|++gcj_lat|number|gcj纬度|
|++gcj_lon|number|gcj经度|
|++utm_x|number|Easting value of UTM coordinates|
|++utm_y|number|Northing value of UTM coordinates|
|++wgs84_lat|number|wgs84纬度|
|++wgs84_lon|number|wgs84经度|

** 说明 **：如果对应车道没有找到，那么对应的车道它的值就是None

返回示例：

```json
{
    // 成功的lane
    "13252313Ad99d4_0_-1": {
        "head": {
        "gcj_lat": 39.88027582617059,
        "gcj_lon": 116.27621487180325,
        "utm_x": 437593.088151026,
        "utm_y": 4414588.3156744,
        "wgs84_lat": 39.879053395112244,
        "wgs84_lon": 116.27018443131425
        },
        "tail": {
        "gcj_lat": 39.87945804518634,
        "gcj_lon": 116.2765168787596,
        "utm_x": 437618.16201582295,
        "utm_y": 4414497.318381711,
        "wgs84_lat": 39.87823542146802,
        "wgs84_lon": 116.27048632158154
        }
    },
    // 失败的lane
    "13252313Ad99d4_0_0": null
    ...
}
```