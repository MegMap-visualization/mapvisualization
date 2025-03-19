import logging
import typing as t
import json
from pathlib import Path
import datetime

from flask import Blueprint, request
from flask import Response
from flask import current_app
import numpy as np

from refile.smart import SmartPath
from refile import smart_sync

from megmap_viz.utils.coord_converter import GCJ02, WGS84
from megmap_viz.datatypes import ResponseData


logger = logging.getLogger(__name__)

bp = Blueprint("wanlixing-trajectory-vis", __name__, url_prefix="/wlx")


class QueryTypedDict(t.TypedDict):
    date_ranges: t.List[t.Tuple[datetime.datetime, datetime.datetime]]
    dates: t.List[datetime.datetime]


def isInteresting(
    date: datetime.datetime,
    query: QueryTypedDict,
) -> bool:
    if date in query["dates"]:
        return True

    for date_range in query["date_ranges"]:
        if date_range[0] <= date <= date_range[1]:
            return True

    return False


def filter_by_date(rs: t.Dict, query: QueryTypedDict) -> t.Dict:
    filtered_data = {}

    all_count = 0
    min_count = np.inf
    min_count_road_id = ""
    max_count = -np.inf
    max_count_road_id = ""
    for road_id, rv in rs["data"].items():
        localizations = []
        timestamps = []
        bag_names = []

        for ti, l, b in zip(
            rv["timestamp"], rv["localization"], rv["bag_names"]
        ):
            curr_date = datetime.datetime.fromtimestamp(ti)

            if not isInteresting(
                datetime.datetime(
                    year=curr_date.year,
                    month=curr_date.month,
                    day=curr_date.day,
                ),
                query,
            ):
                continue

            timestamps.append(ti)
            localizations.append(l)
            bag_names.append(b)

        if len(timestamps) == 0:
            continue

        if min_count > len(timestamps):
            min_count = len(timestamps)
            min_count_road_id = road_id
        if max_count < len(timestamps):
            max_count = len(timestamps)
            max_count_road_id = road_id
        all_count += len(timestamps)

        filtered_data[road_id] = dict(
            bag_names=bag_names,
            road_id=road_id,
            count=len(timestamps),
            timestamp=timestamps,
            localization=localizations,
            points=rv["points"],
            utm_zone_id=rv["utm_zone_id"],
        )

    if all_count == 0:
        return {}

    return dict(
        data=filtered_data,
        all_count=all_count,
        min_count=int(min_count),
        max_count=int(max_count),
        max_count_road_id=max_count_road_id,
        min_count_road_id=min_count_road_id,
    )


def download_last_data(cache_dir: Path):
    smart_sync(
        current_app.config["CACHE"]["wanlixing_s3_path"], str(cache_dir)
    )


@bp.get("/vis-data")
def get_vis_data() -> Response:
    filter_str = request.args.get("filter")

    cache_dir = Path(
        current_app.config["CACHE"]["wanlixing_vis_data_cache_dir"]
    )
    metadata_file_path = cache_dir / "metadata.json"

    if not metadata_file_path.exists():
        download_last_data(cache_dir)
    else:
        with metadata_file_path.open() as f:
            metadata = json.load(f)

        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        if metadata["date"] != yesterday.strftime("%Y-%m-%d"):
            download_last_data(cache_dir)

    with metadata_file_path.open() as f:
        metadata = json.load(f)
    with (cache_dir / metadata["file_name"]).open() as f:
        heatmap_data = json.load(f)

    if filter_str is None:
        return ResponseData(
            code=200, status="success", message="", data=heatmap_data
        ).json

    date_filters = filter_str.split(";")
    if len(date_filters) == 0:
        return ResponseData(
            code=200, status="success", message="", data=heatmap_data
        ).json

    date_ranges = []
    dates = []
    for date_filter in date_filters:
        if "-" not in date_filter:
            dates.append(datetime.datetime.strptime(date_filter, "%Y%m%d"))
            continue

        try:
            start_date, end_date = date_filter.split("-")
            start_date_obj = datetime.datetime.strptime(start_date, "%Y%m%d")
            end_date_obj = datetime.datetime.strptime(end_date, "%Y%m%d")

            if start_date_obj > end_date_obj:
                return ResponseData(
                    code=400,
                    status="error",
                    message=f"Invalid date range: {date_filter}",
                    data=None,
                ).json

            date_ranges.append((start_date_obj, end_date_obj))
        except Exception:
            return ResponseData(
                code=400,
                status="error",
                message=f"Invalid date range: {date_filter}",
                data=None,
            ).json

    heatmap_data = filter_by_date(
        heatmap_data, QueryTypedDict(date_ranges=date_ranges, dates=dates)
    )

    return ResponseData(
        code=200, status="success", message="", data=heatmap_data
    ).json
