import typing as t

from dataclasses import dataclass

from shapely.geometry import Polygon, LineString

ObjectType = t.Literal["crosswalk", "speedBump", "stopline", "parkingSpace"]


@dataclass
class ApolloObject:
    id_: str
    type_: ObjectType

    outline: t.Union[Polygon, LineString]

    @property
    def id(self) -> str:
        return self.id_

    @property
    def type(self) -> str:
        return self.type_
