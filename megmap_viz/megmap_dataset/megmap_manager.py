import typing as t
from functools import lru_cache

from megmap_viz.megmap_dataset.megmap_gpkg.gpkg_db import MegMapFileInfo
from megmap_viz.megmap_dataset.megmap import MegMap, PointsType
from megmap_viz.megmap_dataset.megmap_gpkg.gpkg_db import GPKGDB


class MegMapManager:
    def __init__(self, gpkg_db: GPKGDB) -> None:
        self.gpkg_db = gpkg_db

    @lru_cache()
    def build_map(
        self,
        file_info: MegMapFileInfo,
        coord_transform: t.Callable[[PointsType], PointsType] = lambda x: x,
    ) -> MegMap:
        return MegMap(self.gpkg_db, file_info, coord_transform)
