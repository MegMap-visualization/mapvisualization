# Map Routing Inspectors 接口文档

## /map-routing-inspector/all-submaps [GET]

该接口用于获取地图中所有最大子图。

查询参数:

- map_path: 地图路径, 例如: s3://xxx.xml
- map_md5: 地图文件md5，例如：sgsdget823r9jslkdgjckgskggg

请求示例：

http://xxxx/map-routing-inspector/sub-maps?map_path=s3://xxx.xml&map_md5=sgsdget823r9jslkdgjckgskggg

返回数据：

|字段名|类型|描述|
|:-:|:-:|:-:|
|submaps|object|地图中所有最大子图可视化信息|
|+[submap_id]|object|最大子图对应的中心参考线id和应该赋予的颜色信息|
|++roads|list[ref_lane_id]|该最大子图的所有中心参考线id|
|++color|str|该最大子图应该赋予的颜色|
|isolated_roads|object|地图中的孤立道路可视化信息|
|++roads|list[ref_lane_id]|所有孤立道路的中心参考线id|
|++color|str|孤立道路应该赋予的颜色|

返回示例：

```json
{
  "submaps": {
    "submap_1": {
      "roads": [
        "bb3d8_4_0",
        "13645983A3d88e_0_0",
        "13425317Ac6589_0_0",
        "21623737A7HoXT_0_0",
        "13252324A0f511_0_0",
        "16145903A1cfb7_9_0",
        "4451e_3_0",
        "21637478A7egEP_0_0",
        "16145939A8640f_0_0",
        ...
      ]
    },
    ...
  },
  "isolated_roads": {
    "color": "#ff0c00",
    "roads": [
      "bb3d8_4_0",
      "13645983A3d88e_0_0",
      "13425317Ac6589_0_0",
      "21623737A7HoXT_0_0",
      "13252324A0f511_0_0",
      "16145903A1cfb7_9_0",
      "4451e_3_0",
      "21637478A7egEP_0_0",
      "16145939A8640f_0_0",
      ...
    ]
  }
}
```

## /map-routing-inspector/routing [GET]

查询参数:

- map_path: 地图路径, 例如: s3://xxx.xml
- map_md5: 地图文件md5，例如：sgsdget823r9jslkdgjckgskggg
- rsid_list：设置起点，终点和途径点，例如：13535547Ac845f_0_0,Way10034_0_0,Way10034_1_0

请求示例：

http://xxxx/map-routing-inspector/all-routing-endpoints?map_path=s3://xxx.xml&map_md5=sgsdget823r9jslkdgjckgskggg
&rsid_list=13535547Ac845f_0,Way10034_0

返回数据：

|字段名|类型|描述|
|:-:|:-:|:-:|
|summary|object|对于该次routing是否成功的报告|
|+has_routing|bool|全部routing是否成功|
|+first_failure_road_segment|tuple[start_ref_lane_id, end_ref_lane_id] \| none|记录第一次routing失败的起始ref_lane_id和结束ref_lane_id, 如果routing成功则没有这个字段|
|+ref_lane_ids|list[ref_lane_id]|输入的起始点和途径点|
|details|object|记录了routing的详细结果|
|+[routing_segment_id]|object|记录一段routing的详细结果，比如[ref_lane0, ref_lane1, ref_lane2]是我们需要routing的起始点和途经点，那么[ref_lane0, ref_lane1]是road_seg_0, [ref_lane1, ref_lane2]是road_seg_1|
|++start_road_id|str|road_seg的起始ref_lane_id|
|++end_road_id|str|road_seg的结束ref_lane_id|
|++has_routing|bool|该段routing是否成功|
|++has_multi_routing|bool|该段routing是否有多条routing结果|
|++color|str|该段结果应该渲染的颜色|
|++path|list[ref_lane_id] \| object|road_seg的routing结果，如果是object类型，说明该段有多个routing结果，该object的key为结果名称，value的类型是list[ref_lane_id]|
|++no_succ_lanes|list[ref_lane_id|该段routing时没有后继的ref_lane（routing失败的时候会用到）|

返回示例：

```json
# 失败示例
{
  "summary": {
    "has_routing": false,
    "first_failure_road_segment": [
      "Way10034_0_0",
      "13535547Ac845f_0_0"
    ],
    "ref_lane_ids": [
      "13535547Ac845f_0_0",
      "Way10034_0_0",
      "13535547Ac845f_0_0"
    ]
  },
    "details": {
      "road_seg_1": {
        "start_ref_lane_id": "Way10034_0_0",
        "end_ref_lane_id": "13535547Ac845f_0_0",
        "path": [],
        "has_routing": false,
        "has_multi_routing": false,
        "no_succ_lanes": [
          "Way10034_0_0"
        ],
        "color": "#ffaa00"
      },
      ...
    }
}

# 成功示例
{
    "summary": {
      "has_routing": true,
      "ref_lane_ids": [
        "13535547Ac845f_0",
        "Way10034_0"
      ]
    },
    "details": {
    "road_seg_0": {
      "start_ref_lane_id": "13535547Ac845f_0_0",
      "end_ref_lane_id": "Way10034_0_0",
      "path": [ // 不是多条routing结果
        "13535547Ae4479_0_0",
        "13535547Acae0d_0_0",
        "13535547Acd64a_0_0",
        "13535547Ac460c_0_0",
        "13535547A58e9f_0_0",
        "13535547A58e9f_1_0",
        "13535547A90762_0_0",
        ...
      ],
      "has_routing": true,
      "has_multi_routing": false,  // 不是多条routing结果
      "no_succ_lanes": [
        "13535557Adc145_0_0",
        "13540265A09685_0_0",
        "13540267Adc8a2_0_0",
        ...
      ],
      "color": "#ff0083"
    },
    "road_seg_1": {
      "start_ref_lane_id": "13535547Ac845f_0_0",
      "end_ref_lane_id": "Way10034_0_0",
      "path": { // 多条routing结果
        "path_0": [
          "13535547Ae4479_0_0",
          "13535547Acae0d_0_0",
          "13535547Acd64a_0_0",
          "13535547Ac460c_0_0",
          "13535547A58e9f_0_0",
          "13535547A58e9f_1_0",
          "13535547A90762_0_0",
          ...
        ],
        ...
      },
      "has_routing": true,
      "has_multi_routing": true,  // 多条routing结果
      "no_succ_lanes": [
        "13535557Adc145_0_0",
        "13540265A09685_0_0",
        "13540267Adc8a2_0_0",
        ...
      ],
      "color": "#ff0083"
    },
    ...
    }
}
```
