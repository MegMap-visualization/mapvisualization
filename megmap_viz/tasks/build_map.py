from __future__ import annotations
import json
import time
import datetime
import typing as t
from pathlib import Path
import traceback
import logging
import gc
import os

from celery import shared_task
from celery.exceptions import Ignore
from celery.utils.log import get_task_logger
from flask import current_app

from megmap_viz.megmap_dataset.megmap_gpkg import (
    build_all_map_layer,
    write_map_layer_to_gpkg,
    ApolloBuilderContext,
    MemoBuilderContext,
    get_builder_context_cls,
)
from megmap_viz.utils.file_op import (
    download_from_oss,
    get_file_size,
)
from megmap_viz.megmap_dataset.utils import load_megmap_file
from megmap_viz.utils.datetime_str import get_datetime_str
from megmap_viz.datatypes import LogType

logger = get_task_logger(__name__)


BuildMapTaskStatusType = t.Literal["error", "success", "running"]


class BuildMapTaskStateMeta(t.TypedDict):
    file_md5: str
    path: str
    status: BuildMapTaskStatusType
    messages: t.List[LogType]


@shared_task(bind=True, ignored_result=True)
def build_map(self, megmap_path: str, remark: str, megmap_type: str) -> None:
    map_cache_dir = Path(current_app.config["CACHE"]["map_layer_cache_dir"])
    map_file_cache_dir = Path(
        current_app.config["CACHE"]["map_file_cache_dir"]
    )
    logs: t.List[LogType] = []

    is_s3 = True
    if not megmap_path.startswith("s3://"):
        local_apollo_path = Path(megmap_path).absolute()
        is_s3 = False
    else:
        local_apollo_path = map_file_cache_dir / Path(megmap_path).name

    start_time = time.time()
    if is_s3:
        file_size = get_file_size(megmap_path) / 1024 / 1024
        logs.append(
            (
                get_datetime_str(),
                f"Start to download apollo xml, "
                f"File size: {file_size:.2f} MB",
                "info",
            )
        )
        logger.info(logs[-1][1])
        self.update_state(
            state="RUNNING",
            meta=BuildMapTaskStateMeta(
                status="running",
                messages=logs,
                path=megmap_path,
                file_md5="",
            ),
        )

        downloaed_size = 0
        task_id = self.request.id
        task_backend = self.backend
        task_request = self.request

        local_logger = logging.getLogger(
            f"{__name__}[{task_id}].download_stat_callback"
        )

        def download_stat_callback(current_size: int) -> None:
            nonlocal downloaed_size
            nonlocal file_size
            downloaed_size += current_size / 1024 / 1024
            logs.append(
                (
                    get_datetime_str(),
                    f"Downloaded {(downloaed_size / file_size) * 100:.2f}%. "
                    f"Remaining Size: {file_size - downloaed_size:.2f} MB",
                    "info",
                )
            )
            local_logger.info(logs[-1][1])
            task_backend.store_result(
                task_id,
                BuildMapTaskStateMeta(
                    status="running",
                    messages=logs,
                    file_md5="",
                    path=megmap_path,
                ),
                "RUNNING",
                request=task_request,
            )

        try:
            download_from_oss(
                megmap_path, str(local_apollo_path), download_stat_callback
            )
            logs.append(
                (
                    get_datetime_str(),
                    f"Finish downloading apollo xml. "
                    f"Start to load apollo xml. "
                    f"Current Total Cost Time: "
                    f"{time.time() - start_time:.2f} s",
                    "info",
                )
            )
            logger.info(logs[-1][1])
            self.update_state(
                state="RUNNING",
                meta=BuildMapTaskStateMeta(
                    status="running",
                    messages=logs,
                    path=megmap_path,
                    file_md5="",
                ),
            )
        except Exception:
            logs.append(
                (
                    get_datetime_str(),
                    f"Failed to download megmap file\n"
                    f"{traceback.format_exc()}",
                    "error",
                )
            )
            logger.error(logs[-1][1])
            self.update_state(
                state="FAILED",
                meta=BuildMapTaskStateMeta(
                    status="error",
                    messages=logs,
                    path=megmap_path,
                    file_md5="",
                ),
            )
            raise Ignore()

    rv = load_megmap_file(str(local_apollo_path), megmap_type)

    if rv is None:
        logs.append((get_datetime_str(), "Failed to load map data", "error"))
        logger.error(logs[-1][1])
        self.update_state(
            state="FAILED",
            meta=BuildMapTaskStateMeta(
                status="error",
                path=megmap_path,
                file_md5="",
                messages=logs,
            ),
        )
        raise Ignore()

    megmap_data, file_md5 = rv
    logs.append(
        (
            get_datetime_str(),
            f"Finishing loading map data, Start to build map layer. "
            f"Current Total Cost Time: {time.time() - start_time:.2f} s",
            "info",
        )
    )
    logger.info(logs[-1][1])
    self.update_state(
        state="RUNNING",
        meta=BuildMapTaskStateMeta(
            status="running",
            messages=logs,
            path=megmap_path,
            file_md5=file_md5,
        ),
    )

    metadata = {
        "map_remark": remark,
        "map_md5": file_md5,
        "map_s3_path": megmap_path,
    }
    try:
        builder_ctx_cls = get_builder_context_cls(megmap_type)
        metadata["map_type"] = builder_ctx_cls.builder_type.name.lower()
        metadata["available_layers"] = json.dumps(
            builder_ctx_cls.avaliable_layers
        )
        metadata["layer_id_name_map"] = json.dumps(
            builder_ctx_cls.layer_id_name_map
        )
        layer_datum, building_logs = build_all_map_layer(
            megmap_data, builder_ctx_cls
        )
        logs.extend(building_logs)
        del megmap_data
        logs.append(
            (
                get_datetime_str(),
                f"Finish building map layer, "
                f"Start to write map layer datum to gpkg. "
                f"Current Total Cost Time: {time.time() - start_time:.2f} s",
                "info",
            )
        )
        logger.info(logs[-1][1])
        self.update_state(
            state="RUNNING",
            meta=BuildMapTaskStateMeta(
                status="running",
                messages=logs,
                path=megmap_path,
                file_md5=file_md5,
            ),
        )
    except Exception:
        logs.append(
            (
                get_datetime_str(),
                f"""Failed to build map layer\n"""
                f"""{traceback.format_exc()}""",
                "error",
            )
        )
        logger.error(logs[-1][1])
        self.update_state(
            state="FAILED",
            meta=BuildMapTaskStateMeta(
                status="error",
                messages=logs,
                path=megmap_path,
                file_md5=file_md5,
            ),
        )
        raise Ignore()

    try:
        logs.append(
            (
                get_datetime_str(),
                f"Finish writing map layer datum to gpkg "
                f"Current Total Cost Time: {time.time() - start_time:.2f} s",
                "info",
            )
        )
        logger.info(logs[-1][1])
        write_map_layer_to_gpkg(
            layer_datum,
            str(map_cache_dir / f"{remark}_{file_md5}.gpkg"),
            matadata=metadata,
        )
        self.update_state(
            state="SUCCESS",
            meta=BuildMapTaskStateMeta(
                status="success",
                messages=logs,
                path=megmap_path,
                file_md5=file_md5,
            ),
        )
    except Exception:
        logs.append(
            (
                get_datetime_str(),
                f"Failed to write map layer datum to gpkg"
                f"\n{traceback.format_exc()}",
                "error",
            )
        )
        logger.error(logs[-1][1])
        self.update_state(
            state="FAILED",
            meta=BuildMapTaskStateMeta(
                status="error",
                messages=logs,
                path=megmap_path,
                file_md5=file_md5,
            ),
        )
        raise Ignore()
