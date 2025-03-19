from typing import Tuple

import utm

from utils.transfer_util import Transfer
from utils.random_color import generate_unique_color


coordinate_transfer = Transfer()


class LogExtracter:
    def __init__(self, route_end_dist=100) -> None:
        self.route_end_dist = route_end_dist
        self.log = {}
        self.res = {}

        self._zone_number = None
        self._zone_letter = None
        self._existing_colors = []

    def run(self, data: dict, auxilary_point: Tuple[float, float]):
        self.log = {}
        self.res = {}
        self._zone_number = None
        self._zone_letter = None
        self.log = data["result"]["check_abnormal_road"]
        self._zone_number, self._zone_letter = self._get_utm_zone_info(
            *auxilary_point
        )
        self.set_abnormal_status()
        self.extract()
        return self.res

    def set_abnormal_status(self):
        self.abnormal_status = [
            "overspeed",
            "abnormal_acceleration",
            "lowspeed",
            "digression",
            "non-stop",
            "stop",
        ]
        self._abnormal_status_name = {
            "overspeed": "超速位置",
            "abnormal_acceleration": "加速度异常位置",
            "lowspeed": "低速位置",
            "digression": "偏离路线位置",
            "non-stop": "未停车位置",
            "stop": "停车位置",
        }
        self._color_map = {
            "overspeed": "#F56C6C",
            "abnormal_acceleration": "#CF3476",
            "lowspeed": "#409EFF",
            "digression": "#E6A23C",
            "non-stop": "#7FB5B5",
            "stop": "#308446",
            "ego_stop_pos": "#6C7156",
        }

    def extract(self):
        # 1. stop pos
        self._extract_stop_pos_x_y(
            self.log["end_pos_info"]["ego_stop_pos"], "ego_stop_pos"
        )
        # 2. all abnormal status in self.abnormal_status
        for status in self.abnormal_status:
            if status in self.log:
                self._extract_all_x_y(status)

    def _get_utm_zone_info(
        self, gcj_lat: float, gcj_lon: float
    ) -> Tuple[int, str]:
        wgs84_lon, wgs84_lat = coordinate_transfer.gcj02_to_wgs84(
            gcj_lon, gcj_lat
        )
        return utm.latlon_to_zone_number(
            wgs84_lat, wgs84_lon
        ), utm.latitude_to_zone_letter(wgs84_lat)

    def _extract_stop_pos_x_y(self, data, key):
        self.res[key] = {}
        self.res[key]["points"] = [self._extract_single_x_y(data)]
        self.res[key]["color"] = self._color_map[key]
        self.res[key]["name"] = "自车停止位置"

    def _extract_all_x_y(self, key):
        """
        Extract all x and y positions from a single abnormal status
        """
        curr_res = []
        for abnormal_status_case in self.log[key]:
            curr_res.extend(self._extract_start_end_x_y(abnormal_status_case))
        self.res[key] = {}
        self.res[key]["points"] = curr_res
        self.res[key]["color"] = self._color_map[key]
        self.res[key]["name"] = self._abnormal_status_name[key]

    def _extract_start_end_x_y(self, data):
        """
        Extract x and y for one abnormal case (start and end pos included)
        """
        return [
            self._extract_single_x_y(data["ego_xy_position"][0]),
            self._extract_single_x_y(data["ego_xy_position"][1]),
        ]

    def _extract_single_x_y(self, data):
        if data.get("wgs84_lon") is not None:
            wgs84_lon, wgs84_lat = float(data["wgs84_lon"]), float(
                data["wgs84_lat"]
            )
            utm_x, utm_y, _, _ = utm.from_latlon(wgs84_lat, wgs84_lon)
            gcj_lon, gcj_lat = coordinate_transfer.wgs84_to_gcj02(
                wgs84_lon, wgs84_lat
            )
            return {
                "utm_x": utm_x,
                "utm_y": utm_y,
                "wgs84_lat": wgs84_lat,
                "wgs84_lon": wgs84_lon,
                "gcj_lon": gcj_lon,
                "gcj_lat": gcj_lat,
            }
        lat, lon = utm.to_latlon(
            data["x"], data["y"], self._zone_number, self._zone_letter
        )
        gcj_lon, gcj_lat = coordinate_transfer.wgs84_to_gcj02(lon, lat)
        return {
            "utm_x": data["x"],
            "utm_y": data["y"],
            "wgs84_lat": lat,
            "wgs84_lon": lon,
            "gcj_lon": gcj_lon,
            "gcj_lat": gcj_lat,
        }
