from typing import List, Optional, Dict, Tuple
import utm
from lxml import etree

from megmap_viz.utils.transfer_util import coordinate_transfer


class LaneKeyPointExtracter:
    def __init__(self) -> None:
        self.__lane_key_point_dict = {}
        self.__lane_key_point_num_dict = {}

    def get_lane_key_points(
        self, lane_uid: str, idx: int
    ) -> Optional[Dict[str, Dict[str, Tuple[float, float]]]]:
        if lane_uid not in self.__lane_key_point_dict:
            return

        lane_key_points = self.__lane_key_point_dict[lane_uid]
        extracting_num = self.__lane_key_point_num_dict[lane_uid]
        if idx > extracting_num:
            idx = extracting_num
        return {
            "head": lane_key_points["head_points"][idx - 1],
            "tail": lane_key_points["tail_points"][idx - 1],
        }

    def extract(self, apollo_xml: etree._Element) -> None:
        roads = apollo_xml.findall("road")

        for road in roads:
            lane_section_right_lanes = road.xpath(".//laneSection/right/lane")
            if not isinstance(lane_section_right_lanes, list):
                continue
            self.__extract_lane_key_point(
                lane_section_right_lanes  # type: ignore
            )

    def __extract_lane_key_point(self, lanes: List[etree._Element]) -> None:
        for lane in lanes:
            uid = lane.attrib["uid"]
            center_line = lane.find("centerLine")
            if center_line is None:
                continue
            res = self.__get_head_tail_points(center_line)
            if res is None:
                return
            head_tail_points, extracting_num = res
            self.__lane_key_point_dict[uid] = head_tail_points
            self.__lane_key_point_num_dict[uid] = extracting_num

    def __get_head_tail_points(
        self, center_line: etree._Element
    ) -> Optional[Tuple[Dict[str, List[Dict[str, Tuple[float, float]]]], int]]:
        points = center_line.xpath(".//point")

        if not isinstance(points, list):
            return

        if len(points) < 2:
            return
        elif 2 <= len(points) < 6:
            extrating_num = 1
        elif 6 <= len(points) < 10:
            extrating_num = 3
        else:
            extrating_num = 5

        head_points = []
        tail_points = []
        for head_point, tail_point in zip(
            points[:extrating_num], points[-extrating_num:]
        ):
            (head_wgs84_lon, head_wgs84_lat) = float(
                head_point.attrib["x"]  # type: ignore
            ), float(
                head_point.attrib["y"]  # type: ignore
            )
            head_utm_x, head_utm_y, _, _ = utm.from_latlon(
                longitude=head_wgs84_lon, latitude=head_wgs84_lat
            )
            (
                head_gcj02_lon,
                head_gcj02_lat,
            ) = coordinate_transfer.wgs84_to_gcj02(
                wgs84_lon=head_wgs84_lon, wgs84_lat=head_wgs84_lat
            )
            head_points.append(
                {
                    "wgs84_lon": head_wgs84_lon,
                    "wgs84_lat": head_wgs84_lat,
                    "utm_x": head_utm_x,
                    "utm_y": head_utm_y,
                    "gcj_lon": head_gcj02_lon,
                    "gcj_lat": head_gcj02_lat,
                }
            )

            (tail_wgs84_lon, tail_wgs84_lat) = float(
                tail_point.attrib["x"]  # type: ignore
            ), float(
                tail_point.attrib["y"]  # type: ignore
            )
            tail_utm_x, tail_utm_y, _, _ = utm.from_latlon(
                longitude=tail_wgs84_lon, latitude=tail_wgs84_lat
            )
            (
                tail_gcj02_lon,
                tail_gcj02_lat,
            ) = coordinate_transfer.wgs84_to_gcj02(
                wgs84_lon=tail_wgs84_lon, wgs84_lat=tail_wgs84_lat
            )
            tail_points.insert(
                0,
                {
                    "wgs84_lon": tail_wgs84_lon,
                    "wgs84_lat": tail_wgs84_lat,
                    "utm_x": tail_utm_x,
                    "utm_y": tail_utm_y,
                    "gcj_lon": tail_gcj02_lon,
                    "gcj_lat": tail_gcj02_lat,
                },
            )

        return {
            "head_points": head_points,
            "tail_points": tail_points,
        }, extrating_num
