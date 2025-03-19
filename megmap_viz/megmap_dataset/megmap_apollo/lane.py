from __future__ import annotations
import typing as t
from dataclasses import dataclass
from functools import cached_property

from .base import ApolloGeometry, ApolloReference


@dataclass
class ApolloLanePredecessor:
    lane_uid: str


@dataclass
class ApolloLaneSuccessor:
    lane_uid: str


@dataclass
class ApolloLaneNeighbor:
    lane_uid: str
    side: t.Literal["left", "right"]
    direction: str


@dataclass
class ApolloLaneSpeedLimit:
    max: int


@dataclass
class ApolloLaneLink:
    predecessors: t.List[ApolloLanePredecessor]
    neighbors: t.List[ApolloLaneNeighbor]
    successors: t.List[ApolloLaneSuccessor]


@dataclass
class ApolloLaneBorderType:
    s_offset: float
    type: str
    color: str


@dataclass
class ApolloLaneBorder:
    border_type: t.Optional[ApolloLaneBorderType]
    geometry: ApolloGeometry

    @cached_property
    def color(self) -> str:
        if self.border_type is None:
            return "unknown"
        else:
            return self.border_type.color

    @cached_property
    def is_virtual(self) -> bool:
        if self.border_type is None:
            return False
        else:
            return self.border_type.type == "virtual"

    @cached_property
    def type(self) -> str:
        if self.border_type is None:
            return "unknown"
        else:
            return self.border_type.type


@dataclass
class ApolloLaneSampleAssociate:
    s_offset: float
    left_width: float
    right_width: float


@dataclass
class ApolloLaneRoadSampleAssociation(ApolloLaneSampleAssociate):
    pass


@dataclass
class ApolloLane:
    id_: int
    uid: str
    type_: str
    direction: str
    turn_type: str

    speed_limit: t.Optional[ApolloLaneSpeedLimit]
    link: ApolloLaneLink
    border: ApolloLaneBorder
    left_border: t.Optional[ApolloLaneBorder]
    center_line: ApolloGeometry

    sample_associates: t.List[ApolloLaneSampleAssociate]
    road_sample_associations: t.List[ApolloLaneRoadSampleAssociation]

    signal_overlap_group: t.List[ApolloReference]
    object_overlap_group: t.List[ApolloReference]
    junction_overlap_group: t.List[ApolloReference]
    lane_overlap_group: t.List[ApolloReference]

    @property
    def type(self) -> str:
        return self.type_

    @property
    def id(self) -> int:
        return self.id_

    @cached_property
    def side(self) -> t.Literal["left", "right", "center"]:
        if self.id > 0:
            return "left"
        elif self.id < 0:
            return "right"
        else:
            return "center"

    @cached_property
    def road_id(self) -> str:
        return self.uid.rsplit("_", 2)[0]

    @cached_property
    def section_id(self) -> int:
        return int(self.uid.rsplit("_", 2)[1])

    @cached_property
    def road_section_id(self) -> str:
        return self.uid.rsplit("_", 1)[0]

    @cached_property
    def color(self) -> str:
        if self.border.border_type is None:
            return "unknown"
        else:
            return self.border.border_type.color

    @cached_property
    def is_virtual(self) -> bool:
        if self.border.border_type is None:
            return False
        else:
            return self.border.border_type.type == "virtual"

    @cached_property
    def border_type(self) -> str:
        if self.border.border_type is None:
            return "unknown"
        else:
            return self.border.border_type.type

    def __lt__(self, other: ApolloLane) -> bool:
        if self.section_id != other.section_id:
            return self.section_id < other.section_id
        return self.id < other.id


@dataclass
class ApolloLaneBoundary:
    left: ApolloGeometry
    right: ApolloGeometry


@dataclass
class ApolloLaneSection:
    id_: int

    boundary: ApolloLaneBoundary

    left_lanes: t.List[ApolloLane]
    right_lanes: t.List[ApolloLane]  # we only use right lanes for now
    ref_line: ApolloLane

    @property
    def id(self) -> int:
        return self.id_

    def __lt__(self, other: ApolloLaneSection) -> bool:
        return self.id < other.id
