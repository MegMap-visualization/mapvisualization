import datetime
import typing as t
from collections import defaultdict
from queue import Queue
import logging

import requests
from flask import current_app
from celery import shared_task

from megmap_viz.megmap_dataset.datatypes import RemarkInfo
from megmap_viz.megmap_dataset.utils import get_remark_info

if t.TYPE_CHECKING:
    from megmap_viz.megmap_dataset.megmap_gpkg.gpkg_db import GPKGDB


logger = logging.getLogger(__name__)


def get_map_remark_list() -> t.List[str]:
    gpkg_db: GPKGDB = current_app.extensions["gpkg_db"]
    return [file_info.remark for file_info in gpkg_db.all_megmap_file_info]


def del_map_data(remark: str) -> bool:
    gpkg_db: GPKGDB = current_app.extensions["gpkg_db"]

    file_info_list = [
        file_info
        for file_info in gpkg_db.all_megmap_file_info
        if file_info.remark == remark
    ]

    for file_info in file_info_list:
        gpkg_db.delete(file_info)
        logger.debug(f"Remove map data: {remark}")

    return True


@shared_task(ignore_result=True)
def remove_old_map_data() -> None:
    remarks_to_del_queue = Queue()

    map_remark_list = get_map_remark_list()
    logger.info(f"Get map remark list: {map_remark_list}")

    map_remark_info: t.List[RemarkInfo] = sorted(
        [get_remark_info(remark) for remark in map_remark_list], reverse=True
    )
    logger.info(msg=f"Get map remark info: {map_remark_info}")

    map_remark_map = defaultdict(list)
    for remark_info in map_remark_info:
        if remark_info.is_true:
            map_remark_map[remark_info.name].append(remark_info)
        else:
            if remark_info.remark in remarks_to_del_queue.queue:
                continue
            logger.info(
                f"Add map whose name is not standard "
                f"to remove queue: {remark_info.remark}"
            )
            remarks_to_del_queue.put(remark_info.remark)

    for name, remark_info_list in map_remark_map.items():
        if len(remark_info_list) <= 3:
            logger.info(f"Don't need to remove old maps: {name}")
            continue
        for remark_info in remark_info_list[3:]:
            if remark_info.remark in remarks_to_del_queue.queue:
                continue
            logger.info(f"Add old map to remove queue: {remark_info.remark}")
            remarks_to_del_queue.put(remark_info.remark)

    while not remarks_to_del_queue.empty():
        remark = remarks_to_del_queue.get()
        logger.info(f"Start to remove map data: {remark}")
        if not del_map_data(remark):
            logger.warning(f"Failed to remove map data: {remark}")
            remarks_to_del_queue.put(remark)
            continue
        logger.info(f"Finish to remove map data: {remark}")

    logger.info("Finish to remove all old maps datum.")
