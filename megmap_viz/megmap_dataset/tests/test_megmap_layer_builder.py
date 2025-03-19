import json
import typing as t
import os
from pathlib import Path

from megmap_viz.megmap_dataset.megmap_gpkg import (
    build_all_map_layer,
    write_map_layer_to_gpkg,
    MemoBuilderContext,
    ApolloBuilderContext,
)
from megmap_viz.megmap_dataset.megmap_memo.memo_data_parser import MemoDataDict
from megmap_viz.utils.file_op import load_xml, load_json


def test_build_apollo_all_map_layer(test_apollo_xml_local_path: str) -> None:
    drv = load_xml(test_apollo_xml_local_path)
    assert drv is not None

    apollo_xml, md5 = drv
    save_path = Path(
        test_apollo_xml_local_path.replace(".xml", f"_{md5}.gpkg")
    )
    if save_path.exists():
        os.remove(str(save_path))

    rv = build_all_map_layer(apollo_xml, ApolloBuilderContext)
    write_map_layer_to_gpkg(
        rv,
        test_apollo_xml_local_path.replace(".xml", f"_{md5}.gpkg"),
        matadata={
            "file_md5": md5,
            "file_path": test_apollo_xml_local_path,
            "remark": Path(test_apollo_xml_local_path).stem,
        },
    )
    assert rv


def test_build_memo_all_map_layer(test_memo_local_path: str) -> None:
    drv = load_json(test_memo_local_path)
    assert drv is not None

    memo_json, md5 = drv
    save_path = Path(test_memo_local_path.replace(".json", f"_{md5}.gpkg"))
    if save_path.exists():
        os.remove(str(save_path))

    rv = build_all_map_layer(
        t.cast("MemoDataDict", memo_json), MemoBuilderContext
    )
    write_map_layer_to_gpkg(
        rv,
        test_memo_local_path.replace(".json", f"_{md5}.gpkg"),
        {
            "map_remark": Path(test_memo_local_path).stem,
            "map_md5": md5,
            "map_s3_path": test_memo_local_path,
            "available_layers": json.dumps(
                MemoBuilderContext.avaliable_layers
            ),
            "layer_id_name_map": json.dumps(
                MemoBuilderContext.layer_id_name_map
            ),
        },
    )
    assert rv
