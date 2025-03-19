import typing as t

from dataclasses import dataclass

from .lane import ApolloLaneSection
from .object import ApolloObject
from .signal import ApolloSignal


@dataclass
class ApolloRoad:
    id_: str
    type_: str
    junction: str

    lanes: t.List[ApolloLaneSection]
    signals: t.List[ApolloSignal]
    objects: t.List[ApolloObject]

    @property
    def id(self) -> str:
        return self.id_

    @property
    def type(self) -> str:
        return self.type_
