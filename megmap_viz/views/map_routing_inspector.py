import json
import pickle
import os
from typing import Dict, Optional, Tuple

import portalocker
from flask import Blueprint, request, current_app

from map_routing_inspectors.all_routing_inspector import AllRoutingInspector
from map_routing_inspectors.map_reader import parse_apollo, ParserResult
from map_routing_inspectors.routing_inspector import RoutingInspector
from datatypes import ResponseData, BufferType
from utils.file_op import load_xml


bp = Blueprint(
    "map_routing_inspector", __name__, url_prefix="/map-routing-inspector"
)


ALL_ROUTING_BUFFER = {}
ROUTING_BUFFER = {}


ALL_ROUTING_LOCAL_BUFFER_PATH = os.path.join(
    current_app.instance_path, "all_routing_inspector"
)
ROUTING_LOCAL_BUFFER_PATH = os.path.join(
    current_app.instance_path, "routing_inspector"
)
PARSER_RESULT_LOCAL_BUFFER_PATH = os.path.join(
    current_app.instance_path, "parser_result"
)

os.makedirs(ALL_ROUTING_LOCAL_BUFFER_PATH, exist_ok=True)
os.makedirs(ROUTING_LOCAL_BUFFER_PATH, exist_ok=True)
os.makedirs(PARSER_RESULT_LOCAL_BUFFER_PATH, exist_ok=True)


def get_local_buffer_path(
    map_path: str, map_md5: str, buffer_type: BufferType
) -> str:
    buffer_name = f'{map_path.rsplit(".", 1)[0]}_{map_md5}'.replace("/", "_")
    if buffer_type == BufferType.ALL_ROUTING:
        buffer_path = os.path.join(ALL_ROUTING_LOCAL_BUFFER_PATH, buffer_name)
        return buffer_path
    elif buffer_type == BufferType.ROUTING:
        buffer_path = os.path.join(ROUTING_LOCAL_BUFFER_PATH, buffer_name)
        return buffer_path
    elif buffer_type == BufferType.ParserResult:
        buffer_path = os.path.join(
            PARSER_RESULT_LOCAL_BUFFER_PATH, buffer_name
        )
        return buffer_path
    else:
        return ""


def has_local_parser_result(map_path: str, map_md5: str) -> bool:
    buffer_path = get_local_buffer_path(
        map_path, map_md5, BufferType.ParserResult
    )
    return os.path.exists(buffer_path)


def store_local_parser_result(
    map_path: str, map_md5: str, result: Dict
) -> None:
    buffer_path = get_local_buffer_path(
        map_path, map_md5, BufferType.ParserResult
    )
    with portalocker.Lock(buffer_path, timeout=1):
        try:
            with open(buffer_path, "wb") as f:
                pickle.dump(result, f)
        except Exception:
            pass


def get_local_parser_result(map_path: str, map_md5: str) -> ParserResult:
    buffer_path = get_local_buffer_path(
        map_path, map_md5, BufferType.ParserResult
    )
    with open(buffer_path, "rb") as f:
        return pickle.load(f)


def has_local_all_routing_result(map_path: str, map_md5: str) -> bool:
    buffer_path = get_local_buffer_path(
        map_path, map_md5, BufferType.ALL_ROUTING
    )
    return os.path.exists(buffer_path)


def store_local_all_routing_result(
    map_path: str, map_md5: str, result: Dict
) -> None:
    buffer_path = get_local_buffer_path(
        map_path, map_md5, BufferType.ALL_ROUTING
    )
    with portalocker.Lock(buffer_path, timeout=1):
        try:
            with open(buffer_path, "w") as f:
                json.dump(result, f)
        except Exception:
            pass


def get_local_all_routing_result(map_path: str, map_md5: str) -> Dict:
    buffer_path = get_local_buffer_path(
        map_path, map_md5, BufferType.ALL_ROUTING
    )
    with open(buffer_path, "r") as f:
        return json.load(f)


@bp.route("/all-submaps")
def map_all_routing():
    map_path = request.args.get("map_path")
    map_md5 = request.args.get("map_md5")

    if map_path is None or map_md5 is None:
        return ResponseData(
            code=400, status="error", message="参数错误", data=None
        ).json

    if has_local_all_routing_result(map_path, map_md5):
        buffer_result = get_local_all_routing_result(map_path, map_md5)
        return ResponseData(
            code=200,
            status="success",
            message="获取地图所有最大子图成功（读取缓存）",
            data=buffer_result,
        ).json

    if has_local_parser_result(map_path, map_md5):
        parser_result = get_local_parser_result(map_path, map_md5)
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

        parser_result = parse_apollo(apollo_xml_root)

    inspector = AllRoutingInspector(parser_result)
    result = inspector.run()
    store_local_all_routing_result(map_path, map_md5, result)
    store_local_parser_result(map_path, map_md5, parser_result)

    return ResponseData(
        code=200, status="success", message="获取地图所有最大子图成功", data=result
    ).json


def has_local_routing_inspector(map_path: str, map_md5: str) -> bool:
    buffer_path = get_local_buffer_path(map_path, map_md5, BufferType.ROUTING)
    return os.path.exists(buffer_path)


def get_local_routing_inspector(
    map_path: str, map_md5: str
) -> RoutingInspector:
    buffer_path = get_local_buffer_path(map_path, map_md5, BufferType.ROUTING)
    with open(buffer_path, "rb") as f:
        return pickle.load(f)


def store_routing_inspector(
    map_path: str, map_md5: str, inspector: RoutingInspector
) -> None:
    buffer_path = get_local_buffer_path(map_path, map_md5, BufferType.ROUTING)
    with portalocker.Lock(buffer_path, timeout=1):
        try:
            with open(buffer_path, "wb") as f:
                pickle.dump(inspector, f)
        except Exception:
            pass


@bp.route("/routing")
def map_routing():
    map_path = request.args.get("map_path")
    map_md5 = request.args.get("map_md5")

    road_section_id_list = request.args.get("rsid_list")

    if map_path is None or map_md5 is None or road_section_id_list is None:
        return ResponseData(
            code=400, status="error", message="参数错误", data=None
        ).json

    road_section_id_list = road_section_id_list.split(",")
    if len(road_section_id_list) < 2:
        return ResponseData(
            code=400,
            status="error",
            message=f"传入数据rsid_list: {road_section_id_list}错误",
            data=None,
        ).json

    if has_local_routing_inspector(map_path, map_md5):
        inspector = get_local_routing_inspector(map_path, map_md5)
    elif has_local_parser_result(map_path, map_md5):
        parser_result = get_local_parser_result(map_path, map_md5)
        inspector = RoutingInspector(parser_result)
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

        parser_result = parse_apollo(apollo_xml_root)
        inspector = RoutingInspector(parser_result)
        store_routing_inspector(map_path, map_md5, inspector)
        store_local_parser_result(map_path, map_md5, parser_result)

    inspector.set_road_section_id_list(road_section_id_list)
    result = inspector.run()

    if isinstance(result, list):
        return ResponseData(
            code=400,
            status="error",
            message=f"获取routing失败: reference lane: {result}不存在！",
            data=None,
        ).json

    return ResponseData(
        code=200, status="success", message="获取routing成功", data=result
    ).json
