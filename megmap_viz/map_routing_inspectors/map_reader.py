from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Dict, Union, Set, List, Optional, Tuple

from lxml import etree


@dataclass
class RoadNode:
    """
    由 road id, 前驱，后继 定义的 road node
    """

    road_id: str
    length: float
    parents: Set[str]
    children: Set[str]


ParserResult = Dict[str, RoadNode]


class ApolloXMLParser(ABC):
    def __init__(self, apollo_root: etree._Element):
        self._apollo_root = apollo_root
        self._road_node_dict = {}

    def parse_tree(self):
        for road in self._apollo_root.findall("road"):
            self._parse_road(road)
        return self._road_node_dict

    @abstractmethod
    def _parse_road(self, road: etree._Element) -> ParserResult:
        pass

    def _get_road_section_id(self, lane_id):
        return lane_id.rsplit("_", 1)[0] + "_0"


class RoutingApolloXMLParser(ApolloXMLParser):
    """
    从 xml 地图文件中获取 road id 及其前驱后继（仅限于 road 级别)，存储为字典
    """

    def _parse_road(self, road):
        lanes = road.find("lanes")
        if lanes is None:
            raise Exception("Road must have lanes element")

        # road_id = road.get("id")

        for lane_section in lanes.findall("laneSection"):
            (
                lane_sec_id,
                lane_pred_set,
                lane_succ_set,
                length,
            ) = self._parse_lane_section(
                lane_section, ["left", "right", "center"]
            )
            if lane_sec_id is None:
                continue
            if lane_sec_id in lane_pred_set:
                lane_pred_set.remove(lane_sec_id)
            if lane_sec_id in lane_succ_set:
                lane_succ_set.remove(lane_sec_id)
            self._road_node_dict[lane_sec_id] = RoadNode(
                lane_sec_id, length, lane_pred_set, lane_succ_set
            )

    def _parse_lane_section(
        self, lane_section, key_li
    ) -> Tuple[Optional[str], Set, Set, float]:
        lane_pred_set = set()
        lane_succ_set = set()
        lane_sec_id = None
        max_length = 0
        for key in key_li:
            (
                lane_sec_id,
                curr_lane_pred,
                curr_lane_succ,
                length,
            ) = self._parse_lane(lane_section, key)
            max_length = max(max_length, length)
            lane_pred_set.update(curr_lane_pred)
            lane_succ_set.update(curr_lane_succ)
        return lane_sec_id, lane_pred_set, lane_succ_set, max_length

    def _parse_lane(
        self, lane_section, key
    ) -> Tuple[Optional[str], List[str], List[str], float]:
        lane_section = lane_section.find(key)
        if lane_section is None:
            return None, [], [], 0
        curr_lane_pred = []
        curr_lane_succ = []
        curr_lane_sec_id = None
        max_length = 0
        for lane in lane_section.findall("lane"):
            length = float(
                lane.find("centerLine").find("geometry").get("length")
            )
            max_length = max(max_length, length)
            if lane.find("link") is not None:
                curr_lane_id = lane.get("uid")
                curr_lane_sec_id = self._get_road_section_id(curr_lane_id)

                for link_pre in lane.find("link").findall("predecessor"):
                    pred_id = link_pre.get("id")
                    pred_road_id = self._get_road_section_id(pred_id)
                    curr_lane_pred.append(pred_road_id)
                for link_suc in lane.find("link").findall("successor"):
                    curr_id = link_suc.get("id")
                    curr_road_id = self._get_road_section_id(curr_id)
                    curr_lane_succ.append(curr_road_id)

        return curr_lane_sec_id, curr_lane_pred, curr_lane_succ, max_length


def parse_apollo(apollo_xml_root: etree._Element) -> ParserResult:
    parser = RoutingApolloXMLParser(apollo_xml_root)

    return parser.parse_tree()
