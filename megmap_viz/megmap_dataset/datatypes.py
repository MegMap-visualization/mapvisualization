from __future__ import annotations
import typing as t
import datetime
from enum import Enum, auto

import geopandas as gpd


MegMapLayer = gpd.GeoDataFrame


class MegMapLayerType(Enum):
    """Enumeration of the types of map layers."""

    LANE = auto()  # all lanes information
    INTERSECTION = auto()  # junction boundaries
    STOP_LINE = auto()  # stop lines
    CROSSWALK = auto()  # crosswalks
    TRAFFIC_LIGHT = auto()  # traffic lights
    LANE_CONNECTOR = auto()  # center lines of vitual lanes in junctions
    BASELINE_PATH = auto()  # center lines of lanes
    LANE_BOUNDARY = auto()  # boundary of the lane
    LANE_GROUP_POLYGON = (
        auto()
    )  # the group of lanes in same direction  polygon
    REFERENCE_LINE = auto()  # reference lines

    @classmethod
    def deserialize(cls, layer: str) -> MegMapLayerType:
        """Deserialize the type when loading from a string."""
        return MegMapLayerType.__members__[layer]


class RemarkInfo(t.NamedTuple):
    is_true: bool
    remark: str
    name: t.Optional[str] = None
    date: t.Optional[datetime.date] = None
    version: t.Optional[int] = None

    def __lt__(self, other: "RemarkInfo"):
        # If self is not true, it should be the first
        if not self.is_true:
            return True
        if not other.is_true:
            return False
        # Sort by date first
        if self.date and other.date:
            if self.date != other.date:
                return self.date < other.date
            # Sort by version if date is the same
            elif self.version and other.version:
                return self.version < other.version
        return False

    def __eq__(self, other: "RemarkInfo"):
        if isinstance(other, RemarkInfo):
            return (
                self.is_true == other.is_true
                and self.date == other.date
                and self.version == other.version
            )
        return False


class BuilderType(Enum):
    APOLLO = "apollo"
    MEMO = "memory_driving"
