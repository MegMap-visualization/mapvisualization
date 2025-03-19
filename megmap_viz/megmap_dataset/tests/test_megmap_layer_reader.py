import typing as t
from pathlib import Path

from shapely.geometry import box

from megmap_viz.megmap_dataset.megmap_gpkg.gpkg_db import (
    GPKGDB,
    MegMapFileInfo,
)
from megmap_viz.megmap_dataset.utils import (
    box_from_gcj02,
    get_map_local_layer,
)


def test_gpkg_db(
    test_apollo_gpkg_root_path: str,
    test_map_layer_data_info: MegMapFileInfo,
    test_hzw_map_bounds: t.List[str],
):
    gpkg_db = GPKGDB(Path(test_apollo_gpkg_root_path))

    assert gpkg_db.exists(test_map_layer_data_info)
    assert (
        gpkg_db.get_metadata(test_map_layer_data_info).map_remark
        == test_map_layer_data_info.remark
    )

    layer_datum = gpkg_db.load_all_map_layer(test_map_layer_data_info)
    assert layer_datum

    bbox = box_from_gcj02(test_hzw_map_bounds)
    layer_intersection_dautm = {}
    for layer_type, layer in layer_datum.items():
        layer_intersection = get_map_local_layer(layer, bbox)
        if layer_intersection.empty:
            continue
        layer_intersection_dautm[layer_type] = layer_intersection
        assert box(
            layer.total_bounds[0],
            layer.total_bounds[1],
            layer.total_bounds[2],
            layer.total_bounds[3],
        ).intersects(
            box(
                layer_intersection.total_bounds[0],
                layer_intersection.total_bounds[1],
                layer_intersection.total_bounds[2],
                layer_intersection.total_bounds[3],
            )
        )
