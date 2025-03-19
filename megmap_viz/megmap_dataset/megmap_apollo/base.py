from dataclasses import dataclass
from functools import cached_property

from shapely.geometry import LineString

from megmap_viz.megmap_dataset.utils import simplify_line


@dataclass
class ApolloGeometry:
    s_offset: float
    x: float
    y: float
    z: float
    length: float

    line: LineString

    @cached_property
    def sim_line(self) -> LineString:
        return simplify_line(self.line)


@dataclass
class ApolloReference:
    id_: str
    start_offset: float
    end_offset: float

    @property
    def id(self) -> str:
        return self.id_
