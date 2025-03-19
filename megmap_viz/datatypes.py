import typing as t
from dataclasses import dataclass
from enum import Enum, auto

from flask import jsonify, Response


LogType = t.Tuple[
    str,
    str,
    t.Literal["warning", "error", "info"],
]


class BufferType(Enum):
    ALL_ROUTING = auto()
    ROUTING = auto()
    ParserResult = auto()


def to_camel_case(snake_str: str) -> str:
    components = snake_str.split("_")
    # Combine first word with capitalized version of subsequent words
    return components[0] + "".join(x.title() for x in components[1:])


def dict_keys_to_camel_case(
    d: t.Union[t.List, t.Dict]
) -> t.Union[t.List, t.Dict]:
    def recurse(item):
        if isinstance(item, dict):
            return {to_camel_case(k): recurse(v) for k, v in item.items()}
        elif isinstance(item, list):
            return [recurse(elem) for elem in item]
        else:
            return item

    return recurse(d)


@dataclass
class ResponseData:
    code: int
    status: t.Literal["success", "error", "warning"]
    message: str
    data: t.Optional[t.Union[t.List, t.Dict]] = None

    @property
    def json(self) -> Response:
        return jsonify(self.__dict__)
