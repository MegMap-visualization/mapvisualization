import typing as t
from dataclasses import dataclass

from shapely.geometry import Polygon

ContactPointType = t.Literal["start", "end"]


@dataclass
class ApolloJunctionConnection:
    id_: int

    incoming_road: str
    connecting_road: str

    contact_point: ContactPointType

    @property
    def id(self) -> int:
        return self.id_


@dataclass
class ApolloJunction:
    id_: str
    outline: Polygon
    connections: t.List[ApolloJunctionConnection]

    @property
    def id(self) -> str:
        return self.id_
