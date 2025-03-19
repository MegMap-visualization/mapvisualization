import typing as t
from dataclasses import dataclass

from shapely.geometry import MultiPoint, Point


SubSignalType = t.Literal[
    "unknown",
    "circle",
    "arrowLeft",
    "arrowRight",
    "arrowForward",
    "arrowLeftAndForward",
    "arrowRightAndForward",
    "arrowUTurn",
]
SignalType = t.Literal["trafficLight"]


@dataclass
class ApolloSubSignal:
    id_: str
    type_: SubSignalType
    center_point: Point

    @property
    def id(self) -> str:
        return self.id_

    @property
    def type(self) -> SubSignalType:
        return self.type_


@dataclass
class ApolloSignal:
    id_: str
    type_: str
    layout_type: str

    outline: MultiPoint
    stop_line_refs: t.List[str]
    sub_signals: t.List[ApolloSubSignal]

    @property
    def id(self) -> str:
        return self.id_

    @property
    def type(self) -> str:
        return self.type_
