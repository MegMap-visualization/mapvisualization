from __future__ import annotations
import typing as t

from flask import Blueprint, request, current_app, logging
from shapely.geometry import Polygon

from megmap_viz.datatypes import ResponseData
from megmap_viz.megmap_dataset.megmap_gpkg import MegMapFileInfo
from megmap_viz.megmap_dataset.datatypes import MegMapLayerType
from megmap_viz.utils.coord_converter import wgs84_to_gcj02
from megmap_viz.megmap_dataset.utils import box_from_gcj02
from megmap_viz.megmap_dataset.utils import get_layer_type

if t.TYPE_CHECKING:
    from flask import Response
    from megmap_viz.megmap_dataset.megmap_manager import MegMapManager
    from megmap_viz.megmap_dataset.megmap_gpkg.gpkg_db import GPKGDB
    from megmap_viz.megmap_dataset.megmap import MegMap


megmap_manager: MegMapManager = current_app.extensions["megmap_manager"]
gpkg_db: GPKGDB = current_app.extensions["gpkg_db"]

bp = Blueprint("megmap_data_query", __name__, url_prefix="/megmap-dataset")

logger = logging.create_logger(current_app)


def get_megmap(map_remark: str, map_md5: str) -> MegMap:
    file_info = MegMapFileInfo(remark=map_remark, md5=map_md5)
    megmap = megmap_manager.build_map(file_info)
    return megmap


@bp.get("/")
def get_all_megmap_info() -> Response:
    megmap_file_infos = []

    for file_info in gpkg_db.all_megmap_file_info:
        # if file_info.remark == current_app.config["LOCAL_MAP_NAME"]:
        #     continue
        megmap_file_infos.append(gpkg_db.get_metadata(file_info).to_dict())

    return ResponseData(
        code=200,
        status="success",
        message="getting all megmap info successfully",
        data=megmap_file_infos,
    ).json


def handle_path_param(
    map_remark: str, map_md5: str, layer_name: str
) -> t.Optional[ResponseData]:
    layer_name = layer_name.upper()
    if layer_name not in MegMapLayerType.__members__:
        return ResponseData(
            code=400,
            status="error",
            message="Invalid layer name",
            data=None,
        )

    file_info = MegMapFileInfo(remark=map_remark, md5=map_md5)

    if not gpkg_db.exists(file_info):
        return ResponseData(
            code=404,
            status="error",
            message="MegMap don't exist",
            data=None,
        )


def parse_map_bounds_str(
    map_bounds_str: str,
) -> t.Optional[Polygon]:
    map_bounds = map_bounds_str.split(";")
    if len(map_bounds) != 4:
        return None
    try:
        bbox = box_from_gcj02(map_bounds)
    except Exception as e:
        logger.exception(e)
        return None
    else:
        return bbox


@bp.get(
    "/layer-datum/<string:map_remark>/<string:map_md5>/<string:layer_name>"
)
def get_layer_datum(
    map_remark: str, map_md5: str, layer_name: str
) -> Response:
    error_res = handle_path_param(map_remark, map_md5, layer_name)
    if error_res is not None:
        return error_res.json

    # 处理局部查询范围参数
    has_bbox = False
    map_bounds_str = request.args.get("map_bounds")
    bbox = None
    if map_bounds_str is not None:
        bbox = parse_map_bounds_str(map_bounds_str)
        if bbox is None:
            return ResponseData(
                code=400,
                status="error",
                message="Invalid map bounds",
                data=None,
            ).json
        has_bbox = True

    # 处理局部查询id参数
    has_ids = False
    ids_str = request.args.get("ids")
    ids = None
    if ids_str is not None:
        ids = ids_str.split(",")
        has_ids = True

    layer_type = get_layer_type(layer_name)
    megmap = get_megmap(map_remark, map_md5)

    if not has_ids and not has_bbox:  # 查询全部
        datum = megmap.get_all_objects(layer_type)
    elif has_ids and has_bbox:  # 查询局部，并限制id
        datum = megmap.get_map_objects_by_bbox(
            t.cast(Polygon, bbox),
            layer_type,
            t.cast(t.List[str], ids),
        )
    elif has_ids:  # 限制id
        datum = megmap.get_map_objects_by_ids(
            layer_type, t.cast(t.List[str], ids)
        )
    elif has_bbox:  # 查询局部
        datum = megmap.get_map_objects_by_bbox(
            t.cast(Polygon, bbox), layer_type
        )
    else:
        datum = None

    return ResponseData(
        code=200,
        status="success",
        message="Getting layer datum successfully",
        data=datum,
    ).json


@bp.get("/layer-ids/<string:map_remark>/<string:map_md5>/<string:layer_name>")
def get_layer_ids(map_remark: str, map_md5: str, layer_name: str) -> Response:
    error_res = handle_path_param(map_remark, map_md5, layer_name)
    if error_res is not None:
        return error_res.json

    # 处理局部查询范围参数
    has_bbox = False
    map_bounds_str = request.args.get("map_bounds")
    bbox = None
    if map_bounds_str is not None:
        bbox = parse_map_bounds_str(map_bounds_str)
        if bbox is None:
            return ResponseData(
                code=400,
                status="error",
                message="Invalid map bounds",
                data=None,
            ).json
        has_bbox = True

    layer_type = get_layer_type(layer_name)
    megmap = get_megmap(map_remark, map_md5)
    try:
        if has_bbox:
            ids = megmap.get_ids_by_bbox(t.cast(Polygon, bbox), layer_type)
        else:
            ids = megmap.get_all_ids(layer_type)
    #fix：错误处理，捕无图层数据情况
    except ValueError:
        return ResponseData(
            code=404,
            status="error",
            message=f"Layer {layer_name} not found in map",
            data=None,
        ).json

    return ResponseData(
        code=200,
        status="success",
        message="Getting ids successfully",
        data=ids,
    ).json


@bp.get("/map-bounds/<string:map_remark>/<string:map_md5>")
def get_map_bounds(map_remark: str, map_md5: str):
    error_res = handle_path_param(map_remark, map_md5, "LANE_GROUP_POLYGON")
    if error_res is not None:
        return error_res.json

    file_info = MegMapFileInfo(remark=map_remark, md5=map_md5)
    megmap = megmap_manager.build_map(file_info, wgs84_to_gcj02)
    bounds = megmap.get_total_bbox()

    return ResponseData(
        code=200,
        status="success",
        message="Getting map bounds successfully",
        data=bounds,
    ).json


@bp.delete("/<string:map_remark>/<string:map_md5>")
def delete_megmap(map_remark: str, map_md5: str) -> Response:
    file_info = MegMapFileInfo(remark=map_remark, md5=map_md5)
    gpkg_db.delete(file_info)
    return ResponseData(
        code=200,
        status="success",
        message="Deleting megmap successfully",
        data=None,
    ).json
