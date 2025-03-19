from __future__ import annotations
import typing as t
import datetime
import logging
import re

import numpy as np
import numpy.typing as npt
from shapely.geometry import Polygon, LineString

from megmap_viz.utils.file_op import (
    load_xml,
    load_json,
)
from megmap_viz.utils.coord_converter import GCJ02, WGS84
from .datatypes import MegMapLayer, RemarkInfo, MegMapLayerType

if t.TYPE_CHECKING:
    from lxml import etree
    from .megmap_gpkg.base_builder import MemoDataDict

logger = logging.getLogger(__name__)


def box_from_gcj02(points_str: t.List[str]) -> Polygon:
    points: t.List[t.Tuple[float, float]] = []
    for point_str in points_str:
        lon_str, lat_str = point_str.split(",")
        lon, lat = float(lon_str), float(lat_str)
        points.append((lon, lat))
    points.append(points[0])
    points_np = np.array(points)
    points_wgs84_lon, points_wgs84_lat = GCJ02.to_wgs84(
        points_np[:, 0], points_np[:, 1]
    )
    points_wgs84 = np.stack([points_wgs84_lon, points_wgs84_lat], axis=1)
    return Polygon(points_wgs84)


def get_map_local_layer(layer: MegMapLayer, bbox: Polygon) -> MegMapLayer:
    new_layer: MegMapLayer = layer.copy()  # type: ignore
    buffered_bbox = bbox.buffer(0.008)
    new_layer = new_layer.loc[layer.intersects(buffered_bbox)]  # type: ignore
    # new_layer["geometry"] = new_layer["geometry"].intersection(
    #     bbox
    # )
    return new_layer


def simplify_line(line_string: LineString) -> LineString:
    lon, lat = t.cast(
        t.Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]],
        line_string.coords.xy,
    )
    x, y, zone_number, zone_letter = WGS84.to_utm(
        np.asarray(lon), np.asarray(lat)
    )
    simplified: LineString = LineString(np.stack([x, y], axis=1)).simplify(0.5)
    sx, sy = t.cast(
        t.Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]],
        simplified.coords.xy,
    )
    lon, lat = WGS84.from_utm(
        np.asarray(sx), np.asarray(sy), zone_number, zone_letter
    )
    return LineString(np.stack([lon, lat], axis=1))


def is_safe_string(s: str) -> bool:
    return bool(re.fullmatch(r"[a-zA-Z0-9\-_. ~]*", s))


def get_remark_info(remark: str) -> RemarkInfo:
    try:
        name, date_str, version = remark.rsplit("_", 2)

        if not is_safe_string(name):
            raise ValueError(f"Invalid name: {name}")

        if not (len(date_str) == 8 and version.startswith("v")):
            raise ValueError(
                f"Invalid date_str: {date_str}, version: {version}"
            )

        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        map_date = datetime.date(year=year, month=month, day=day)
        curr_date = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=8))
        ).date()
        if not (curr_date >= map_date):
            raise ValueError(
                f"Invalid date_str: {date_str}, version: {version}"
            )
        version_num = int(version.replace("v", ""))
    except Exception as e:
        logger.exception(f"Failed to get remark info: {remark}, {e}")
        return RemarkInfo(is_true=False, remark=remark)
    else:
        return RemarkInfo(
            is_true=True,
            remark=remark,
            name=name,
            date=map_date,
            version=version_num,
        )


def get_layer_type(layer_name: str) -> MegMapLayerType:
    layer_type = MegMapLayerType.__members__[layer_name.upper()]
    return layer_type


def load_megmap_file(
    path: str, megmap_type: str
) -> t.Union[t.Tuple[etree._Element, str], t.Tuple[MemoDataDict, str], None]:
    try:
        if megmap_type == "apollo":
            return load_xml(path)
        elif megmap_type == "memo":
            return t.cast(t.Tuple["MemoDataDict", str], load_json(path))
        else:
            return None
    except Exception:
        return None
