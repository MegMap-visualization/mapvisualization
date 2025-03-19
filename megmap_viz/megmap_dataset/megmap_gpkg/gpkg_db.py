import json
import typing as t
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache

import pyogrio
import geopandas as gpd
import numpy as np
import numpy.typing as npt


from ..datatypes import MegMapLayer, MegMapLayerType
from .gpkg_datatypes import MegMapFileInfo, MayLayerMetadata


class GPKGDB:
    def __init__(self, root_path: str) -> None:
        self.root_path = Path(root_path).absolute()

    @property
    def all_megmap_file_info(self) -> t.List[MegMapFileInfo]:
        file_info = []
        for file_path in self.root_path.iterdir():
            if file_path.is_dir():
                continue
            if file_path.suffix != ".gpkg":
                continue
            remark, md5 = file_path.stem.rsplit("_", 1)
            file_info.append(MegMapFileInfo(remark=remark, md5=md5))
        return file_info

    def exists(self, info: MegMapFileInfo) -> bool:
        return (self.root_path / info.filename).exists()

    def delete(self, info: MegMapFileInfo) -> None:
        (self.root_path / info.filename).unlink(missing_ok=True)

    @lru_cache()
    def get_metadata(self, info: MegMapFileInfo) -> MayLayerMetadata:
        meta = pyogrio.read_info(str(self.root_path / info.filename))[
            "dataset_metadata"
        ]
        apollo_path: str = meta["map_s3_path"]
        apollo_md5: str = meta["map_md5"]
        remark: str = meta["map_remark"]
        available_layers: t.List[str] = json.loads(meta["available_layers"])
        layer_id_name_map: t.Dict[str, str] = json.loads(
            meta["layer_id_name_map"]
        )
        map_type: str = meta["map_type"]
        return MayLayerMetadata(
            map_s3_path=apollo_path,
            map_md5=apollo_md5,
            map_remark=remark,
            available_layers=available_layers,
            layer_id_name_map=layer_id_name_map,
            map_type=map_type,
        )

    @lru_cache()
    def load_map_layer(
        self, info: MegMapFileInfo, layer_name: str
    ) -> t.Optional[MegMapLayer]:
        try:
            map_layer = pyogrio.read_dataframe(
                str(self.root_path / info.filename),
                layer=layer_name,
                use_arrow=True,
            )
            return map_layer  # type: ignore
        except Exception:
            return None

    @lru_cache()
    def load_all_map_layer(
        self, info: MegMapFileInfo
    ) -> t.Dict[MegMapLayerType, MegMapLayer]:
        layer_datum = {}
        for layer_type in MegMapLayerType:
            try:
                layer_datum[layer_type] = self.load_map_layer(
                    info, layer_type.name
                )
            except Exception:
                continue
        return layer_datum
