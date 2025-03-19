import json
import pickle
import sys
from pathlib import Path


from map_routing_inspectors.map_reader import parse_apollo
from utils.file_op import smart_read
from lxml import etree
from map_routing_inspectors.all_routing_inspector import AllRoutingInspector
from map_routing_inspectors.routing_inspector import (
    RoutingInspector,
    RoadNetwork,
)


# TEST_MAP_PATH = "s3://zjf-map/apollo_files/merge/beijing_0710.xml"
TEST_MAP_PATH = "/home/u2004/MegviiProjects/ame_ws/mapviz/map-py-utils-client/tests/data/geely_hzw_sh_0704_plana.xml"


def test_all_routing_inspector():
    xml_str = smart_read(TEST_MAP_PATH)
    xml_root = etree.fromstring(xml_str)
    parser_result = parse_apollo(xml_root)
    all_routing_inspector = AllRoutingInspector(parser_result)
    result = all_routing_inspector.run()
    assert result is not None


def test_routing_inspector():
    test_routing_list = ["Way11037_0_0", "Way11121_0_-1", "Way11124_0_-1"]

    xml_str = smart_read(TEST_MAP_PATH)
    xml_root = etree.fromstring(xml_str)
    parser_result = parse_apollo(xml_root)
    routing_inspector = RoutingInspector(parser_result)

    routing_inspector.set_road_section_id_list(test_routing_list)
    result = routing_inspector.run()
    if isinstance(result, list):
        return
    assert result["summary"]["has_routing"]


def test_astart():
    road_network = RoadNetwork()
    # test_routing_list = ["Way11037_0_0", "Way11121_0_-1", "Way11124_0_-1"]
    test_routing_list = ["Way10143_0_-3", "Way10507_0_0"]

    xml_str = smart_read(TEST_MAP_PATH)
    xml_root = etree.fromstring(xml_str)
    parser_result = parse_apollo(xml_root)

    for road in parser_result.values():
        road_network.add_road(
            road.road_id, road.length, road.parents, road.children
        )

    waypoints = [
        road_id.rsplit("_", 1)[0] + "_0" for road_id in test_routing_list
    ]
    results = []
    for i in range(len(waypoints) - 1):
        start_id = waypoints[i]
        end_id = waypoints[i + 1]
        results.append(road_network.get_all_paths(start_id, end_id))
    assert results
