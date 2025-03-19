import json

from flask import Blueprint, request

from log_extracter import LogExtracter
from datatypes import ResponseData
from utils.file_op import smart_read


bp = Blueprint("log_extracter", __name__, url_prefix="/log-extracter")

log_extracter = LogExtracter()


@bp.route("/")
def log_extracter_api():
    log_s3_path = request.args.get("log_s3_path")
    auxilary_point = request.args.get("auxilary_point")

    if auxilary_point is None or log_s3_path is None:
        return ResponseData(
            code=400, status="error", message="参数错误", data=None
        ).json
    try:
        lon, lat = auxilary_point.split(",")
        auxilary_point = (float(lat), float(lon))
    except Exception:
        return ResponseData(
            code=400, status="error", message="参数错误", data=None
        ).json

    log_str = smart_read(log_s3_path)

    if log_str is None:
        return ResponseData(
            code=400, status="error", message="日志不存在", data=None
        ).json

    log_data = json.loads(log_str)

    extraced_data = log_extracter.run(log_data, auxilary_point)

    return ResponseData(
        code=200, status="success", message="提取日志信息成功", data=extraced_data
    ).json
