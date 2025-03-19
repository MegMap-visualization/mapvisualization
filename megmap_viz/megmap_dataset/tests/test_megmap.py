import typing as t
from pathlib import Path

from megmap_viz.megmap_dataset.megmap_gpkg.gpkg_db import (
    MegMapFileInfo,
    GPKGDB,
)
from megmap_viz.megmap_dataset.utils import box_from_gcj02
from megmap_viz.megmap_dataset.datatypes import MegMapLayerType
from megmap_viz.megmap_dataset.megmap import MegMap
from megmap_viz.utils.coord_converter import wgs84_to_gcj02


def test_megmap_all(
    test_apollo_gpkg_root_path: str,
    test_map_layer_data_info: MegMapFileInfo,
) -> None:
    gpkg_db = GPKGDB(test_apollo_gpkg_root_path)
    megmap = MegMap(gpkg_db, test_map_layer_data_info)
    for layer_type in MegMapLayerType:
        ids = megmap.get_all_ids(layer_type)
        datum = megmap.get_map_objects_by_ids(layer_type, ids)[layer_type.name]
        assert len(ids) == len(datum)


def test_megmap_local(
    test_apollo_gpkg_root_path: str,
    test_map_layer_data_info: MegMapFileInfo,
    test_hzw_map_bounds: t.List[str],
) -> None:
    gpkg_db = GPKGDB(test_apollo_gpkg_root_path)
    megmap = MegMap(
        gpkg_db, test_map_layer_data_info, coord_transform=wgs84_to_gcj02
    )
    megmap.get_total_bbox()
    for layer_type in MegMapLayerType:
        data = megmap.get_map_objects_by_bbox(
            box_from_gcj02(test_hzw_map_bounds), layer_type
        )
        ids = megmap.get_ids_by_bbox(
            box_from_gcj02(test_hzw_map_bounds), layer_type
        )
        assert len(ids) == len(data[layer_type.name])
