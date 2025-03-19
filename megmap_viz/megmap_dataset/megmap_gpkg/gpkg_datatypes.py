from __future__ import annotations
import typing as t
from dataclasses import dataclass, asdict

if t.TYPE_CHECKING:
    from shapely.geometry import LineString, Polygon, MultiPoint


class BoundaryInfo(t.NamedTuple):
    left_line_gid: int
    right_line_gid: int


class LaneProperty(t.TypedDict):
    road_id: str
    road_section_id: str
    lane_id: int
    lane_uid: str
    lane_type: str
    turn_type: str
    direction: str
    is_virtual: bool
    length: float
    color: str
    border_type: str
    speed_limit: str
    predecessor_lane_uids: t.List[str]
    successor_lane_uids: t.List[str]
    left_same_neighbor_lane_uids: t.List[str]
    right_same_neighbor_lane_uids: t.List[str]
    left_opposite_neighbor_lane_uids: t.List[str]
    right_opposite_neighbor_lane_uids: t.List[str]
    signal_references: t.List[str]
    object_references: t.List[str]
    junction_references: t.List[str]
    lane_references: t.List[str]
    left_boundary_gid: int
    right_boundary_gid: int


class DataRow(dict):
    def __init__(
        self,
        gid: int,
        geometry: t.Union[Polygon, LineString, MultiPoint],
        **kwrgs,
    ) -> None:
        super().__init__(gid=gid, geometry=geometry, **kwrgs)

    @property
    def gid(self) -> int:
        return self["gid"]


@dataclass(eq=True, frozen=True, unsafe_hash=True)
class MegMapFileInfo:
    remark: str
    md5: str

    @property
    def filename(self) -> str:
        return f"{self.remark}_{self.md5}.gpkg"

    def to_dict(self) -> t.Dict[str, str]:
        return asdict(self)


@dataclass(eq=True, frozen=True, unsafe_hash=True)
class MayLayerMetadata:
    map_s3_path: str
    map_md5: str
    map_remark: str
    map_type: str
    available_layers: t.List[str]
    layer_id_name_map: t.Dict[str, str]

    def to_dict(self) -> t.Dict[str, str]:
        return asdict(self)
