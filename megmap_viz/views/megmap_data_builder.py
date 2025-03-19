from __future__ import annotations
import typing as t
from pathlib import Path

from flask import Blueprint, request, current_app
from celery.result import AsyncResult
from werkzeug.utils import secure_filename

from megmap_viz.megmap_dataset.datatypes import RemarkInfo, BuilderType
from megmap_viz.megmap_dataset.utils import get_remark_info
from megmap_viz.utils.file_op import has_file
from megmap_viz.utils.md5 import get_file_md5
from megmap_viz.megmap_dataset.megmap_gpkg.gpkg_datatypes import MegMapFileInfo
from megmap_viz.datatypes import ResponseData
from megmap_viz.tasks.build_map import build_map


if t.TYPE_CHECKING:
    from flask import Response

bp = Blueprint(
    "megmap_layer_builder", __name__, url_prefix="/megmap-layer-builder"
)

ALLOWED_EXTENSIONS = {"json", "xml"}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@bp.put("/builder-task")
def add_builder_task() -> Response:
    datum = request.get_json()
    apollo_path = datum.get("map_path")
    remark = datum.get("remark")
    map_type = datum.get("map_type")

    try:
        if remark is None:
            remark = Path(apollo_path).stem
    except Exception:
        return ResponseData(
            code=400, status="error", message="Invalid map_path"
        ).json

    if map_type is None:
        return ResponseData(
            code=400, status="error", message="Invalid map_type"
        ).json

    if map_type.upper() not in BuilderType.__members__:
        return ResponseData(
            code=400, status="error", message="Invalid map_type"
        ).json

    remark_info = get_remark_info(remark)
    if not remark_info.is_true:
        return ResponseData(
            code=400,
            status="error",
            message="Invalid remark, remark format: <map_name>_<date:YYYYMMDD>_v<version:int>(e.g. test_map_20230919_v1)",
        ).json

    if apollo_path is None:
        return ResponseData(
            code=400,
            status="error",
            message="apollo_s3_path is required",
            data={"task_id": ""},
        ).json

    if not apollo_path.startswith("s3://"):
        path = Path(apollo_path).absolute()
        if not (path.exists() and path.is_file()):
            return ResponseData(
                code=400,
                status="error",
                message=f"apollo_s3_path: {apollo_path} is not a valid file path",
                data={"task_id": ""},
            ).json
    else:
        if not has_file(apollo_path):
            return ResponseData(
                code=400,
                status="error",
                message=f"apollo_s3_path: {apollo_path} is not a valid file path",
                data={"task_id": ""},
            ).json

    task: AsyncResult = build_map.delay(apollo_path, remark, map_type)  # type: ignore

    return ResponseData(
        code=201,
        status="success",
        message="Builder Task added",
        data={"task_id": task.task_id},
    ).json


@bp.get("/builder-task/<uuid:task_id>")
def get_builder_task(task_id: t.Optional[str] = None) -> Response:
    task = AsyncResult(str(task_id))

    return ResponseData(
        code=200,
        status="success",
        message="Getting Builder Task Status",
        data=task.result,
    ).json


@bp.post("/upload-map")
def upload_map() -> Response:
    if "file" not in request.files:
        return ResponseData(
            code=400,
            status="error",
            message="No file part",
            data={"task_id": ""},
        ).json

    file = request.files["file"]

    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == "" or file.filename is None:
        return ResponseData(
            code=400,
            status="error",
            message="No selected file",
            data={"task_id": ""},
        ).json

    if not file and allowed_file(file.filename):
        return ResponseData(
            code=400,
            status="error",
            message="Invalid file",
            data={"task_id": ""},
        ).json

    map_type = request.form.get("map_type")
    if map_type is None:
        return ResponseData(
            code=400,
            status="error",
            message="Invalid map_type",
            data={"task_id": ""},
        ).json

    filename = secure_filename(file.filename)
    save_path = (
        Path(current_app.config["UPLOAD_FOLDER"]) / filename
    ).absolute()
    file.save(str(save_path.absolute()))

    file_md5 = get_file_md5(str(save_path))
    megmap_file_info = MegMapFileInfo(
        current_app.config["LOCAL_MAP_NAME"], file_md5
    )  # type: ignore
    has_file: bool = current_app.extensions["gpkg_db"].exists(megmap_file_info)

    if not has_file:
        rv: AsyncResult = build_map.delay(
            str(save_path.absolute()),
            current_app.config["LOCAL_MAP_NAME"],
            map_type,
        )  # type: ignore

        return ResponseData(
            code=201,
            status="success",
            message="File uploaded",
            data={
                "has_map": False,
                "task_id": rv.task_id,
                "file_md5": file_md5,
                "megmap_info": None,
            },
        ).json

    megmap_file_metadata = current_app.extensions["gpkg_db"].get_metadata(
        megmap_file_info
    )
    return ResponseData(
        code=200,
        status="success",
        message="File uploaded",
        data={
            "has_map": True,
            "task_id": "",
            "megmap_info": megmap_file_metadata,
            "file_md5": file_md5,
        },
    ).json


@bp.get("/local-map-info/<string:file_md5>")
def local_map_info(file_md5: str) -> Response:
    megmap_file_info = MegMapFileInfo(
        current_app.config["LOCAL_MAP_NAME"], file_md5
    )
    has_file: bool = current_app.extensions["gpkg_db"].exists(megmap_file_info)

    if has_file:
        megmap_file_metadata = current_app.extensions["gpkg_db"].get_metadata(
            megmap_file_info
        )
        return ResponseData(
            code=200,
            status="success",
            message="File exists",
            data={"has_map": True, "megmap_info": megmap_file_metadata},
        ).json

    return ResponseData(
        code=200,
        status="success",
        message="File does not exist",
        data={"has_map": False, "megmap_info": None},
    ).json
