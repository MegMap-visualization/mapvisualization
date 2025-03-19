import typing as t
import dataclasses
import traceback

from shapely.geometry import Point, LineString, Polygon
import numpy as np

from megmap_viz.utils.coord_converter import WGS84
from megmap_viz.megmap_dataset.utils import simplify_line
from megmap_viz.datatypes import LogType
from megmap_viz.utils.datetime_str import get_datetime_str


class RoadDict(t.TypedDict):
    ins_status: str
    ins_trajectory: str
    lane_ids: t.List[str]
    lane_num: int
    pres: t.List[str]


class LaneDict(t.TypedDict):
    centerline: str
    lane_type: str
    lane_type_conf: float
    left_border: str
    max_speed: int
    min_speed: int
    overlaps: t.List[str]
    pres: t.List[str]
    right_border: str
    road_id: str
    sucs: t.List[str]
    turn_type: str


class LinePointDict(t.TypedDict):
    border_color: str
    border_type: str
    conf: float
    nodes: t.List[str]
    length: float


class EqualizationDict(t.TypedDict):
    a0: float
    a1: float
    a2: float
    a3: float
    b0: float
    b1: float
    b2: float
    b3: float
    c0: float
    c1: float
    c2: float
    c3: float
    smax: float
    smin: float


class LinePolylineDict(t.TypedDict, total=False):
    border_color: str
    border_type: str
    conf: float
    equalization: t.List[EqualizationDict]
    start: str
    end: str
    length: float


class NodeDict(t.TypedDict):
    utm_x: float
    utm_y: float
    utm_z: float
    zone_id: int


class ObjectDict(t.TypedDict):
    outline: t.List[str]
    overlaps: t.List[str]
    self_id: str
    type: str


class MemoDataDict(t.TypedDict):
    lanes: t.Dict[str, LaneDict]
    lines: t.Dict[str, t.Union[LinePointDict, LinePolylineDict]]
    nodes: t.Dict[str, NodeDict]
    roads: t.Dict[str, RoadDict]
    objects: t.Dict[str, ObjectDict]


@dataclasses.dataclass
class MemoRoadResult:
    raw_data: RoadDict
    polygon: Polygon


@dataclasses.dataclass
class MemoLaneResult:
    raw_data: LaneDict
    polygon: Polygon
    centerline: LineString


@dataclasses.dataclass
class MemoLineResult:
    raw_data: t.Union[LinePointDict, LinePolylineDict]
    geometry: LineString
    sim_geometry: LineString = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.sim_geometry = simplify_line(self.geometry)


@dataclasses.dataclass
class MemoObjectResult:
    raw_data: ObjectDict
    geometry: t.Union[Polygon, LineString]


@dataclasses.dataclass
class MemoParserResult:
    roads: t.Dict[str, MemoRoadResult]
    lanes: t.Dict[str, MemoLaneResult]
    lines: t.Dict[str, MemoLineResult]
    objects: t.Dict[str, MemoObjectResult]
    logs: t.List[LogType]


class MemoParser:
    memo_data: MemoDataDict

    def __init__(self, memo_data: MemoDataDict) -> None:
        self.memo_data = memo_data

        self.roads: t.Dict[str, MemoRoadResult] = {}
        self.lanes: t.Dict[str, MemoLaneResult] = {}
        self.lines: t.Dict[str, MemoLineResult] = {}
        self.objects: t.Dict[str, MemoObjectResult] = {}

        self.default_utm_zone = list(self.memo_data["nodes"].values())[0][
            "zone_id"
        ]

        self.logs = []

    def run(self) -> MemoParserResult:
        try:
            for line_id in self.memo_data["lines"]:
                try:
                    self.lines[line_id] = self._parse_line(line_id)
                except Exception:
                    self.logs.append(
                        (
                            get_datetime_str(),
                            f"Line: {line_id}\n" f"{traceback.format_exc()}",
                            "warning",
                        )
                    )

            for lane_id in self.memo_data["lanes"]:
                try:
                    self.lanes[lane_id] = self._parse_lane(lane_id)
                except Exception:
                    self.logs.append(
                        (
                            get_datetime_str(),
                            f"Lane: {lane_id}\n" f"{traceback.format_exc()}",
                            "warning",
                        )
                    )

            for road_id in self.memo_data["roads"]:
                try:
                    rv = self._parse_road(road_id)
                except Exception:
                    self.logs.append(
                        (
                            get_datetime_str(),
                            f"Road: {road_id}\n" f"{traceback.format_exc()}",
                            "warning",
                        )
                    )
                    continue
                if rv is None:
                    self.logs.append(
                        (
                            get_datetime_str(),
                            f"road {road_id} has no lanes",
                            "warning",
                        )
                    )
                    continue
                self.roads[road_id] = rv

            for object_id in self.memo_data["objects"]:
                try:
                    rv = self._parse_object(object_id)
                except Exception:
                    self.logs.append(
                        (
                            get_datetime_str(),
                            f"Object: {object_id}\n"
                            f"{traceback.format_exc()}",
                            "warning",
                        )
                    )
                else:
                    if rv is None:
                        self.logs.append(
                            (
                                get_datetime_str(),
                                f"Object: {object_id} is not supported yet.",
                                "warning",
                            )
                        )
                        continue
                    self.objects[object_id] = rv
        except Exception:
            self.logs.append(
                (
                    get_datetime_str(),
                    traceback.format_exc(),
                    "warning",
                )
            )

        return MemoParserResult(
            self.roads, self.lanes, self.lines, self.objects, self.logs
        )

    def _parse_road(self, road_id: str) -> t.Optional[MemoRoadResult]:
        road_dat = self.memo_data["roads"][road_id]

        road_lanes_len = len(road_dat["lane_ids"])
        if road_lanes_len == 0:
            return None
            # raise ValueError(f"road {road_id} must have at least one lane")

        left_boundary_id = self.lanes[road_dat["lane_ids"][0]].raw_data[
            "left_border"
        ]
        right_boundary_id = self.lanes[road_dat["lane_ids"][-1]].raw_data[
            "right_border"
        ]

        left_boundary_geom: LineString = self.lines[left_boundary_id].geometry
        right_boundary_geom: LineString = self.lines[
            right_boundary_id
        ].geometry

        left_boundary_points = list(left_boundary_geom.coords)
        right_boundary_points = list(right_boundary_geom.coords)

        if road_lanes_len == 1:
            polygon_geom = Polygon(
                left_boundary_points + list(reversed(right_boundary_points))
            )
        else:
            first_middle_points: t.List[t.Tuple[float, float]] = []
            last_middle_points: t.List[t.Tuple[float, float]] = []
            added_line_id = {left_boundary_id, right_boundary_id}
            for lane_id in road_dat["lane_ids"]:
                left_boundary_id = self.lanes[lane_id].raw_data["left_border"]
                right_border_id = self.lanes[lane_id].raw_data["right_border"]

                if left_boundary_id not in added_line_id:
                    left_border_points = list(
                        self.lines[left_boundary_id].geometry.coords
                    )
                    last_point, first_point = (
                        left_border_points[0],
                        left_border_points[-1],
                    )
                    first_middle_points.append(first_point)
                    last_middle_points.append(last_point)
                    added_line_id.add(left_boundary_id)

                if right_border_id not in added_line_id:
                    right_border_points = list(
                        self.lines[right_border_id].geometry.coords
                    )
                    last_point, first_point = (
                        right_border_points[0],
                        right_border_points[-1],
                    )
                    first_middle_points.append(first_point)
                    last_middle_points.append(last_point)
                    added_line_id.add(right_border_id)

            polygon_geom = Polygon(
                left_boundary_points
                + first_middle_points
                + list(reversed(right_boundary_points))
                + list(reversed(last_middle_points))
            )

        return MemoRoadResult(road_dat, polygon_geom)

    def _parse_lane(self, lane_id: str) -> MemoLaneResult:
        lane_dat = self.memo_data["lanes"][lane_id]
        left_border_geom = self.lines[lane_dat["left_border"]].geometry
        right_border_geom = self.lines[lane_dat["right_border"]].geometry
        centerline_geom = self.lines[lane_dat["centerline"]].geometry
        polygon_geom = Polygon(
            list(left_border_geom.coords)
            + list(right_border_geom.reverse().coords)
        )
        return MemoLaneResult(lane_dat, polygon_geom, centerline_geom)

    def _parse_line(self, line_id: str) -> MemoLineResult:
        line = self.memo_data["lines"][line_id]

        if line.get("equalization"):
            line = t.cast(LinePolylineDict, line)
            polyline_geom = self._calc_polyline(line)
        else:
            line = t.cast(LinePointDict, line)
            polyline_geom = t.cast(
                LineString,
                LineString(
                    [self._get_point(node_id) for node_id in line["nodes"]]
                ),
            )

        return MemoLineResult(line, polyline_geom)

    def _parse_object(self, object_id: str) -> t.Optional[MemoObjectResult]:
        object_dict = self.memo_data["objects"][object_id]
        if object_dict["type"] == "stopline":
            sn_id, en_id = object_dict["outline"]
            sn, en = self._get_point(sn_id), self._get_point(en_id)
            line_obj = LineString([sn, en])
            return MemoObjectResult(object_dict, line_obj)
        return None

    def _get_polyline_func(
        self, equation: EqualizationDict
    ) -> t.Callable[[float], Point]:
        def func(s: float) -> Point:
            utm_x = (
                equation["a3"]
                + equation["a2"] * s
                + equation["a1"] * s**2
                + equation["a0"] * s**3
            )
            utm_y = (
                equation["b3"]
                + equation["b2"] * s
                + equation["b1"] * s**2
                + equation["b0"] * s**3
            )
            wgs84_x, wgs84_y = WGS84.from_utm(
                utm_x, utm_y, self.default_utm_zone, northern=True
            )
            return Point(wgs84_x, wgs84_y)

        return func

    def _calc_polyline(
        self, polyline: LinePolylineDict, step: float = 1.0
    ) -> LineString:
        if "equalization" not in polyline:
            raise ValueError("polyline must have equalization")
        middle_points: t.List[Point] = []
        for equation in polyline["equalization"]:
            polyline_func = self._get_polyline_func(equation)
            for s in np.arange(equation["smin"], equation["smax"], step):
                middle_points.append(polyline_func(s))
        if "start" in polyline and "end" in polyline:
            start_point = self._get_point(polyline["start"])
            end_point = self._get_point(polyline["end"])
            return LineString([start_point, *middle_points, end_point])
        else:
            return LineString(middle_points)

    def _get_point(self, node_id: str) -> Point:
        utm_x = self.memo_data["nodes"][node_id]["utm_x"]
        utm_y = self.memo_data["nodes"][node_id]["utm_y"]
        utm_zone = self.memo_data["nodes"][node_id]["zone_id"]
        wgs84_x, wgs84_y = WGS84.from_utm(
            utm_x, utm_y, utm_zone, northern=True
        )
        return Point(wgs84_x, wgs84_y)
