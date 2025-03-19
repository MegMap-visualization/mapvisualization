import os
import pickle
from typing import Dict

import portalocker
from flask import Blueprint, request, current_app

from utils.file_op import load_xml
from datatypes import ResponseData
from lane_key_point_extracter.lane_key_point_extracter import (
    LaneKeyPointExtracter,
)


bp = Blueprint(
    "lane_key_point_extracter",
    __name__,
    url_prefix="/lane-key-point",
)


LANE_KEYPOINTS_LOCAL_BUFFER_PATH = os.path.join(
    current_app.instance_path, "lane_key_point"
)

os.makedirs(LANE_KEYPOINTS_LOCAL_BUFFER_PATH, exist_ok=True)


def get_local_buffer_path(map_path: str, map_md5: str) -> str:
    buffer_name = f'{map_path.rsplit(".", 1)[0]}_{map_md5}'.replace("/", "_")
    buffer_path = os.path.join(LANE_KEYPOINTS_LOCAL_BUFFER_PATH, buffer_name)
    return buffer_path


def has_local_lane_key_point_extracter(map_path: str, map_md5: str) -> bool:
    buffer_path = get_local_buffer_path(map_path, map_md5)
    return os.path.exists(buffer_path)


def store_local_lane_key_point_extracter(
    map_path: str,
    map_md5: str,
    lane_key_point_extracter: LaneKeyPointExtracter,
) -> None:
    buffer_path = get_local_buffer_path(map_path, map_md5)
    with portalocker.Lock(buffer_path, timeout=1):
        try:
            with open(buffer_path, "wb") as f:
                pickle.dump(lane_key_point_extracter, f)
        except Exception:
            pass


def get_local_lane_key_point_extracter(
    map_path: str, map_md5: str
) -> LaneKeyPointExtracter:
    buffer_path = get_local_buffer_path(map_path, map_md5)
    with open(buffer_path, "rb") as f:
        return pickle.load(f)


@bp.route("/")
def map_routing():
    map_path = request.args.get("map_path")
    map_md5 = request.args.get("map_md5")

    lane_uid_list = request.args.get("lane_uid_list")
    idx = request.args.get("idx")

    if map_path is None or map_md5 is None or lane_uid_list is None:
        return ResponseData(
            code=400, status="error", message="参数不全", data=None
        ).json

    lane_uid_list = lane_uid_list.split(",")
    if len(lane_uid_list) < 1:
        return ResponseData(
            code=400,
            status="error",
            message=f"传入数据lane_uid_list: {lane_uid_list}错误",
            data=None,
        ).json

    if idx is not None:
        try:
            idx = int(idx)  # type: ignore
            if idx > 5:
                return ResponseData(
                    code=400,
                    status="error",
                    message=f"传入数据idx错误,必须小于5",
                    data=None,
                ).json
        except Exception:
            return ResponseData(
                code=400,
                status="error",
                message=f"传入数据idx错误,必须为整数",
                data=None,
            ).json
    else:
        idx = 3

    if has_local_lane_key_point_extracter(map_path, map_md5):
        extracter = get_local_lane_key_point_extracter(map_path, map_md5)
    else:
        apllo_data = load_xml(map_path)

        if apllo_data is None:
            return ResponseData(
                code=404, status="error", message="无法加载地图", data=None
            ).json

        apollo_xml_root, md5 = apllo_data

        if md5 != map_md5:
            return ResponseData(
                code=404,
                status="error",
                message=f"加载地图md5: {md5} 与 传入md5: {map_md5} 不符！",
                data=None,
            ).json

        extracter = LaneKeyPointExtracter()
        extracter.extract(apollo_xml_root)
        store_local_lane_key_point_extracter(map_path, map_md5, extracter)

    result = {}
    for lane_uid in lane_uid_list:
        result[lane_uid] = extracter.get_lane_key_points(lane_uid, idx)

    return ResponseData(
        code=200, status="success", message="获取lane关键点成功", data=result
    ).json
