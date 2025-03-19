from __future__ import annotations
import dataclasses
import typing as t
import logging
import json
from typing import Any

import geopandas as gpd
from shapely.geometry import Polygon, LineString

from .datatypes import MegMapLayer, MegMapLayerType
from .utils import get_map_local_layer, get_layer_type

if t.TYPE_CHECKING:
    from megmap_viz.megmap_dataset.megmap_gpkg.gpkg_db import GPKGDB
    from .megmap_gpkg.gpkg_db import MegMapFileInfo

logger = logging.getLogger(__name__)


PointsType = t.List[t.Tuple[float, float]]


class BaseData(dict):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.update(*args, **kwargs)

    def __setitem__(self, key, value):
        self._set_json_value(key, value)

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).items():
            self._set_json_value(k, v)

    def _set_json_value(self, __name, __value):
        try:
            if isinstance(__value, str):
                __value = __value.replace("'", '"')
            parsed_value = json.loads(__value)
            super().__setitem__(__name, parsed_value)
        except (json.JSONDecodeError, TypeError):
            if str(__value) == "nan":
                super().__setitem__(__name, None)
            else:
                super().__setitem__(__name, __value)


class MegMap:
    def __init__(
        self,
        megmap_gpkg: GPKGDB,
        megmap_file_info: MegMapFileInfo,
        coord_transform: t.Callable[[PointsType], PointsType] = lambda x: x,
    ) -> None:
        self.megmap_gpkg = megmap_gpkg
        self.megmap_file_info = megmap_file_info
        self.coord_transform = coord_transform

        self._map_layer: t.Dict[MegMapLayerType, MegMapLayer] = {}
        self.megmap_metadata = self.megmap_gpkg.get_metadata(megmap_file_info)
        self._map_layer_id_name_mapping = {
            get_layer_type(k): v
            for k, v in self.megmap_metadata.layer_id_name_map.items()
        }

    def initialize_all_layers(self) -> None:
        for layer_type in MegMapLayerType:
            self._load_megmap_layer(layer_type.name)

    def get_map_objects_by_bbox(
        self,
        bbox: Polygon,
        layer_type: MegMapLayerType,
        layer_ids: t.Optional[t.List[str]] = None,
    ) -> t.Dict[str, t.Dict[str, Any]]:
        layer = self._get_megmap_layer(layer_type)
        local_layer = get_map_local_layer(layer, bbox)
        if layer_ids is not None:
            local_layer = t.cast(
                gpd.GeoDataFrame,
                local_layer[
                    t.cast(
                        gpd.GeoSeries,
                        local_layer[
                            self._map_layer_id_name_mapping[layer_type]
                        ],
                    ).isin(layer_ids)
                ],
            )
        return self._convert_layer_to_base_data(
            layer_type,
            local_layer,
            self._map_layer_id_name_mapping[layer_type],
        )

    def get_map_objects_by_ids(
        self, layer_type: MegMapLayerType, layer_ids: t.List[str]
    ) -> t.Dict[str, t.Dict[str, Any]]:
        layer = self._get_megmap_layer(layer_type)

        local_layer: MegMapLayer = t.cast(
            gpd.GeoDataFrame,
            layer[
                t.cast(
                    gpd.GeoSeries,
                    layer[self._map_layer_id_name_mapping[layer_type]],
                ).isin(layer_ids)
            ],
        )

        return self._convert_layer_to_base_data(
            layer_type,
            local_layer,
            self._map_layer_id_name_mapping[layer_type],
        )

    def get_all_objects(
        self, layer_type: MegMapLayerType
    ) -> t.Dict[str, t.Dict[str, Any]]:
        layer = self._get_megmap_layer(layer_type)
        return self._convert_layer_to_base_data(
            layer_type, layer, self._map_layer_id_name_mapping[layer_type]
        )

    def get_all_ids(self, layer_type: MegMapLayerType) -> t.List[str]:
        layer = self._get_megmap_layer(layer_type)
        return t.cast(
            gpd.GeoSeries, layer[self._map_layer_id_name_mapping[layer_type]]
        ).to_list()

    def get_ids_by_bbox(
        self, bbox: Polygon, layer_type: MegMapLayerType
    ) -> t.List[str]:
        layer = self._get_megmap_layer(layer_type)
        local_layer = get_map_local_layer(layer, bbox)
        return t.cast(
            gpd.GeoSeries,
            local_layer[self._map_layer_id_name_mapping[layer_type]],
        ).to_list()

    def get_total_bbox(self) -> t.List[t.Tuple[float, float]]:
        layer = self._get_megmap_layer(MegMapLayerType.LANE_GROUP_POLYGON)
        min_x, min_y, max_x, max_y = layer.total_bounds.tolist()
        min_x, min_y, max_x, max_y = list(
            Polygon(
                [
                    (min_x, min_y),
                    (max_x, min_y),
                    (max_x, max_y),
                    (min_x, max_y),
                ]
            )
            .buffer(0.001)
            .bounds
        )
        return self.coord_transform(
            [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)]
        )

    def get_available_layers(self) -> t.List[str]:
        return self.megmap_metadata.available_layers

    def _load_megmap_layer(self, layer_name: str) -> None:
        layer_type = MegMapLayerType.__members__[layer_name]
        if layer_type in self._map_layer:
            return
        layer = self.megmap_gpkg.load_map_layer(self.megmap_file_info, layer_name)
        # fix:判空处理无图层数据情况
        if layer is not None:
            self._map_layer[layer_type] = layer

    def _get_megmap_layer(self, layer_type: MegMapLayerType) -> MegMapLayer:
        if layer_type not in self._map_layer:
            self._load_megmap_layer(layer_type.name)
            # fix:判空处理无图层数据情况
            if self._map_layer.get(layer_type) is None:
                raise ValueError()
        return self._map_layer[layer_type]

    def _convert_layer_to_base_data(
        self,
        layer_type: MegMapLayerType,
        local_layer: MegMapLayer,
        id_name: str,
    ) -> t.Dict[str, t.Dict[str, Any]]:
        raw_datum: t.List[t.Dict[t.Hashable, t.Any]] = local_layer.to_dict(
            "records"
        )

        points_list = self._get_points_data(raw_datum)

        rv = {}
        for datum, points in zip(raw_datum, points_list):
            rv[datum[id_name]] = BaseData(
                points=points,
                **t.cast(t.Dict[str, t.Any], datum),
            )
        return rv

    def _get_points_data(
        self,
        datum: t.List[t.Dict[t.Hashable, t.Any]],
    ) -> t.List[PointsType]:
        if not datum:
            return []

        try:
            geometries: t.Union[t.List[Polygon], t.List[LineString]] = [
                dat.pop("geometry") for dat in datum
            ]
        except Exception:
            logger.error("Failed to get geometry from datum")
            return []

        warmup = geometries[0]
        if warmup.geom_type == "Polygon":
            points_list = [
                self.coord_transform(
                    t.cast(
                        PointsType, list(t.cast(Polygon, geom).exterior.coords)
                    )
                )
                for geom in geometries
            ]
        elif warmup.geom_type == "LineString":
            points_list = [
                self.coord_transform(
                    t.cast(PointsType, list(t.cast(LineString, geom).coords))
                )
                for geom in geometries
            ]
        else:
            logger.error("Unknown geometry type")
            points_list = []

        return points_list
