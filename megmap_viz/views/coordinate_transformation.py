import logging
import typing as t

import utm
import numpy as np
from numpy import typing as npt
from flask import Blueprint, request

from megmap_viz.utils.coord_converter import GCJ02, WGS84
from megmap_viz.datatypes import ResponseData

logger = logging.getLogger(__name__)
bp = Blueprint("coordinate_trasformation", __name__, url_prefix="/ct")


def parse_coords(
    coords: str,
) -> t.Optional[t.Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]]:
    coord_list = coords.split(",")

    if len(coord_list) % 2 != 0:
        return None

    try:
        coord_array = np.array(coord_list, dtype=np.float64)
        coord_array = coord_array.reshape(-1, 2)
        return coord_array[:, 0], coord_array[:, 1]
    except Exception:
        return None


@bp.get("/gcj2wgs2utm")
def gcj2wgs84utm():
    gcj_coords = request.args.get("coords")

    if gcj_coords is None:
        return ResponseData(
            code=400, status="error", message="coords is required", data=None
        ).json

    coords_parsed = parse_coords(gcj_coords)
    if coords_parsed is None:
        return ResponseData(
            code=400, status="error", message="coords is invalid", data=None
        ).json

    wgs84_lon_array, wgs84_lat_array = GCJ02.to_wgs84(
        coords_parsed[0], coords_parsed[1]
    )
    wgs84_array = np.stack([wgs84_lon_array, wgs84_lat_array], axis=1)

    utm_x_array, utm_y_array, utm_zone, utm_letter = WGS84.to_utm(
        wgs84_lon_array, wgs84_lat_array
    )
    utm_array = np.stack([utm_x_array, utm_y_array], axis=1)

    return ResponseData(
        code=200,
        status="success",
        message="",
        data={
            "wgs84": wgs84_array.tolist(),
            "utm": {
                "data": utm_array.tolist(),
                "zone": utm_zone,
                "letter": utm_letter,
            },
        },
    ).json


@bp.get("/utm2wgs2gcj")
def utm2wgs():
    utm_coords = request.args.get("coords")
    secondary_coord = request.args.get("secondary_coord")
    utm_zone = request.args.get("utm_zone")
    utm_letter = request.args.get("utm_letter")
    northern = request.args.get("northern")

    if utm_coords is None:
        return ResponseData(
            code=400, status="error", message="coords is required", data=None
        ).json

    def get_coords(utm_zone_num, utm_letter=None, northern=None):
        coords_parsed = parse_coords(utm_coords)
        if coords_parsed is None:
            return ResponseData(
                code=400,
                status="error",
                message="failed to parse coords",
                data=None,
            ).json

        try:
            if utm_letter is not None:
                wgs84_lon_array, wgs84_lat_array = WGS84.from_utm(
                    coords_parsed[0],
                    coords_parsed[1],
                    utm_zone_num,
                    utm_letter,
                )
            elif northern is not None:
                wgs84_lon_array, wgs84_lat_array = WGS84.from_utm(
                    coords_parsed[0],
                    coords_parsed[1],
                    utm_zone_num,
                    northern=northern,
                )
            else:
                return ResponseData(
                    code=400,
                    status="error",
                    message="utm_letter or northern is required",
                    data=None,
                ).json
        except Exception as e:
            return ResponseData(
                code=400,
                status="error",
                message=f"failed to convert coords: {e}",
            ).json
        else:
            wgs84_array = np.stack([wgs84_lon_array, wgs84_lat_array], axis=1)

            gcj_lon_array, gcj_lat_array = GCJ02.from_wgs84(
                wgs84_lon_array, wgs84_lat_array
            )
            gcj_array = np.stack([gcj_lon_array, gcj_lat_array], axis=1)

            return ResponseData(
                code=200,
                status="success",
                message="",
                data={
                    "wgs84": wgs84_array.tolist(),
                    "gcj02": gcj_array.tolist(),
                    "utm_zone_number": utm_zone_num,
                    "utm_zone_letter": utm_letter,
                },
            ).json

    if utm_zone is not None and utm_letter is not None:
        try:
            utm_zone_num = int(utm_zone)
        except Exception:
            return ResponseData(
                code=400,
                status="error",
                message="``utm_zone`` is invalid",
                data=None,
            ).json
        return get_coords(utm_zone_num, utm_letter=utm_letter)

    if secondary_coord is not None:
        coords_parsed = parse_coords(secondary_coord)
        if coords_parsed is None:
            return ResponseData(
                code=400,
                status="error",
                message="secondary coordinate is invalid",
                data=None,
            ).json
        utm_zone_num = utm.latlon_to_zone_number(
            coords_parsed[1][0], coords_parsed[0][0]
        )
        utm_letter = utm.latitude_to_zone_letter(coords_parsed[1][0])
        if utm_letter is None:
            return ResponseData(
                code=400,
                status="error",
                message="secondary coordinate is invalid",
                data=None,
            ).json
        return get_coords(utm_zone_num, utm_letter=utm_letter)

    if utm_zone is not None and northern is not None:
        try:
            utm_zone_num = int(utm_zone)
        except Exception:
            return ResponseData(
                code=400,
                status="error",
                message="``utm_zone`` is invalid",
                data=None,
            ).json
        if northern.lower() == "true":
            northern = True
        elif northern.lower() == "false":
            northern = False
        else:
            return ResponseData(
                code=400,
                status="error",
                message="``northern`` is invalid",
                data=None,
            ).json

        return get_coords(utm_zone_num, northern=northern)

    return ResponseData(
        code=400,
        status="error",
        message="``secondary_coord`` or ``utm_zone`` and ``utm_letter`` or ``utm_zone`` and ``northern``is required",
        data=None,
    ).json


@bp.get("/wgs2gcj-utm")
def wgs2gcj_utm():
    wgs_coords = request.args.get("coords")

    if wgs_coords is None:
        return ResponseData(
            code=400, status="error", message="coords is required", data=None
        ).json

    coords_parsed = parse_coords(wgs_coords)
    if coords_parsed is None:
        return ResponseData(
            code=400, status="error", message="coords is invalid", data=None
        ).json

    gcj02_lon_array, gcj02_lat_array = GCJ02.from_wgs84(
        coords_parsed[0], coords_parsed[1]
    )
    gcj02_array = np.stack([gcj02_lon_array, gcj02_lat_array], axis=1)

    utm_x_array, utm_y_array, utm_zone, utm_letter = WGS84.to_utm(
        coords_parsed[0], coords_parsed[1]
    )
    utm_array = np.stack([utm_x_array, utm_y_array], axis=1)

    return ResponseData(
        code=200,
        status="success",
        message="",
        data={
            "gcj02": gcj02_array.tolist(),
            "utm": {
                "data": utm_array.tolist(),
                "zone": utm_zone,
                "letter": utm_letter,
            },
        },
    ).json
