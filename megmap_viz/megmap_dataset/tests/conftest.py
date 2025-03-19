import typing as t
import os
import pytest

from megmap_viz import BASE_DIR
from megmap_viz.megmap_dataset.megmap_gpkg.gpkg_db import (
    MegMapFileInfo,
)


@pytest.fixture
def test_memo_local_path() -> str:
    return str(
        BASE_DIR
        / "megmap_dataset"
        / "megmap_memo"
        / "tests"
        / "data"
        / "xibeiwang_right.json"
    )


@pytest.fixture
def test_apollo_xml_local_path() -> str:
    return str(BASE_DIR / "tests" / "data" / "hangzhouwan_20231215_v0.xml")


@pytest.fixture
def test_apollo_xml_s3_path() -> str:
    return (
        "s3://megmap-data/apollo_files/hangzhouwan/hangzhouwan_20230901_v0.xml"
    )


@pytest.fixture
def test_apollo_gpkg_root_path() -> str:
    return str(BASE_DIR / "tests" / "data")


@pytest.fixture
def test_map_layer_data_info() -> MegMapFileInfo:
    return MegMapFileInfo(
        remark="hangzhouwan_20230901_v0",
        md5="5227314535758f75dcdad83eb0feb590",
    )


@pytest.fixture
def test_beijing_map_bounds() -> t.List[str]:
    return [
        "116.365924,39.990997",
        "116.365924,39.986473",
        "116.393918,39.986473",
        "116.393918,39.990997",
    ]


@pytest.fixture
def test_hzw_map_bounds() -> t.List[str]:
    return [
        "121.269425,30.282257",
        "121.269425,30.252664",
        "121.422237,30.252664",
        "121.422237,30.282257",
    ]
