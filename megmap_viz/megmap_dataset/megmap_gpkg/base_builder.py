from __future__ import annotations
import abc
import typing as t
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from pathlib import Path
import logging
from queue import Queue

import pyogrio
from lxml import etree

from megmap_viz.utils.datetime_str import get_datetime_str
from megmap_viz.datatypes import LogType

from ..megmap_apollo.apollo_parser import (
    ApolloParserResult,
    MultiApolloParser,
)
from ..megmap_memo.memo_data_parser import (
    MemoParser,
    MemoDataDict,
    MemoParserResult,
)
from ..datatypes import MegMapLayer, MegMapLayerType, BuilderType

if t.TYPE_CHECKING:
    from .gpkg_builder import BoundaryInfo

logger = logging.getLogger("megmap_viz.map_data_retriever")


BuilderDataType = t.Union[etree._Element, MemoDataDict]


LAYER_BUIDLERS: t.Dict[MegMapLayerType, t.Type[BaseLayerBuilder]] = {}


def register_layer_builder(cls: t.Type[BaseLayerBuilder]):
    LAYER_BUIDLERS.setdefault(cls.layer_type, cls)


class BuilderContext(abc.ABC):
    data: t.Any
    global_id: t.ClassVar[int] = 0
    builder_type: t.ClassVar[BuilderType]
    layer_datum: t.Dict[MegMapLayerType, MegMapLayer]
    lane_boundary_info: t.Dict[str, BoundaryInfo]

    connecting_road_ids: t.List[str]  # For Apollo
    boudary_layer: MegMapLayer
    lane_layer: MegMapLayer

    layer_id_name_map: t.ClassVar[t.Dict[str, str]]
    avaliable_layers: t.ClassVar[t.List[str]]

    logs: t.ClassVar[t.List[LogType]] = []

    def __init__(self) -> None:
        self.layer_datum: t.Dict[MegMapLayerType, MegMapLayer] = {}
        self.lane_boundary_info: t.Dict[str, BoundaryInfo] = {}

    @property
    def auto_id(self) -> int:
        BuilderContext.global_id += 1
        return BuilderContext.global_id

    @abc.abstractmethod
    def set_data(self, *args, **kwargs) -> None:
        pass

    def add_log(
        self, level: t.Literal["warning", "error", "info"], message: str
    ) -> None:
        self.logs.append((get_datetime_str(), message, level))


class ApolloBuilderContext(BuilderContext):
    data: ApolloParserResult
    builder_type = BuilderType.APOLLO

    layer_id_name_map = {
        MegMapLayerType.LANE.name.lower(): "lane_uid",
        MegMapLayerType.LANE_CONNECTOR.name.lower(): "lane_uid",
        MegMapLayerType.LANE_BOUNDARY.name.lower(): "gid",
        MegMapLayerType.REFERENCE_LINE.name.lower(): "road_section_id",
        MegMapLayerType.BASELINE_PATH.name.lower(): "lane_uid",
        MegMapLayerType.TRAFFIC_LIGHT.name.lower(): "self_id",
        MegMapLayerType.STOP_LINE.name.lower(): "self_id",
        MegMapLayerType.CROSSWALK.name.lower(): "self_id",
        MegMapLayerType.INTERSECTION.name.lower(): "junction_id",
        MegMapLayerType.LANE_GROUP_POLYGON.name.lower(): "road_section_id",
    }

    avaliable_layers = list(layer_id_name_map.keys())

    def __init__(self) -> None:
        super().__init__()

    def set_data(self, data: etree._Element) -> None:
        self.data = MultiApolloParser(data).run()

    @cached_property
    def connecting_road_ids(self) -> t.List[str]:
        rv: t.List[str] = []
        for apollo_junction in self.data.junction_datum.values():
            rv.extend(
                [
                    connection.connecting_road
                    for connection in apollo_junction.connections
                ]
            )
        return rv

    @property
    def boudary_layer(self) -> MegMapLayer:
        return self.layer_datum[MegMapLayerType.LANE_BOUNDARY]

    @property
    def lane_layer(self) -> MegMapLayer:
        return self.layer_datum[MegMapLayerType.LANE]


class MemoBuilderContext(BuilderContext):
    data: MemoParserResult
    builder_type = BuilderType.MEMO

    layer_id_name_map = {
        MegMapLayerType.LANE.name.lower(): "lane_id",
        MegMapLayerType.LANE_BOUNDARY.name.lower(): "line_id",
        MegMapLayerType.BASELINE_PATH.name.lower(): "lane_id",
        MegMapLayerType.LANE_GROUP_POLYGON.name.lower(): "road_id",
        MegMapLayerType.REFERENCE_LINE.name.lower(): "line_id",
        MegMapLayerType.STOP_LINE.name.lower(): "stop_line_id",
    }

    avaliable_layers = list(layer_id_name_map.keys())

    def __init__(self) -> None:
        super().__init__()

    def set_data(self, data: MemoDataDict) -> None:
        self.data = MemoParser(data).run()
        self.logs.extend(self.data.logs)


class BaseLayerBuilder(abc.ABC):
    layer_type: t.ClassVar[MegMapLayerType]
    context: t.ClassVar[BuilderContext]

    def build(self) -> None:
        build_func_map = {
            BuilderType.APOLLO: self.build_from_apollo,
            BuilderType.MEMO: self.build_from_memo,
        }
        build_func_map[self.context.builder_type]()

    @abc.abstractmethod
    def build_from_apollo(self) -> None:
        pass

    @abc.abstractmethod
    def build_from_memo(self) -> None:
        pass

# def build_all_map_layer(
#     data: BuilderDataType, builder_context_cls: t.Type[BuilderContext]
# ) -> t.Tuple[t.Dict[MegMapLayerType, MegMapLayer], t.List[LogType]]:
#     logger.info(f"开始构建地图图层: {builder_context_cls.__name__}")
    
#     try:
#         builder_context = builder_context_cls()
#         logger.info("创建构建器上下文成功")
        
#         try:
#             logger.debug("开始设置数据到上下文")
#             builder_context.set_data(data)
#             logger.info("数据设置成功")
#         except Exception as e:
#             logger.error(f"设置数据失败: {str(e)}", exc_info=True)
#             raise

#         for builder_cls in LAYER_BUIDLERS.values():
#             try:
#                 logger.info(f"开始构建图层: {builder_cls.__name__}")
#                 builder_cls.context = builder_context
#                 builder = builder_cls()
#                 builder.build()
#                 logger.info(f"图层构建成功: {builder_cls.__name__}")
#             except Exception as e:
#                 logger.error(f"图层构建失败 {builder_cls.__name__}: {str(e)}", exc_info=True)
#                 continue

#         logger.info("所有图层构建完成")
#         return builder_context.layer_datum, builder_context.logs
        
#     except Exception as e:
#         logger.error(f"构建过程发生致命错误: {str(e)}", exc_info=True)
#         raise

def build_all_map_layer(
    data: BuilderDataType, builder_context_cls: t.Type[BuilderContext]
) -> t.Tuple[t.Dict[MegMapLayerType, MegMapLayer], t.List[LogType]]:
    builder_context = builder_context_cls()
    builder_context.set_data(data)
    logger.info("Data parsed")

    builder_queue = Queue()
    for builder_cls in LAYER_BUIDLERS.values():
        builder_cls.context = builder_context
        builder_queue.put(builder_cls())

    failed_num: t.Dict[MegMapLayerType, int] = {}
    while not builder_queue.empty():
        layer_builder: BaseLayerBuilder = builder_queue.get()
        try:
            logger.info(f"Building layer {layer_builder.layer_type.name}")
            layer_builder.build()
            logger.info(f"Layer {layer_builder.layer_type.name} built")
        except KeyError or AttributeError as e:
            failed_num.setdefault(layer_builder.layer_type, 0)
            failed_num[layer_builder.layer_type] += 1
            if (
                failed_num[layer_builder.layer_type] >= 3
            ):  # Retrying more than three times indicates a problem
                logger.exception(e)
                logger.error(
                    f"Layer {layer_builder.layer_type.name} not built"
                )
                raise e
            builder_queue.put(layer_builder)
            logger.warning(f"Layer {layer_builder.layer_type.name} requeued")
            continue

    return builder_context.layer_datum, builder_context.logs


def write_map_layer_to_gpkg(
    layer_datum: t.Dict[MegMapLayerType, MegMapLayer],
    gpkg_path: str,
    matadata: t.Optional[t.Dict[str, str]] = None,
) -> None:
    layer_append = False
    logger.info("Writing map data to file")
    for idx, (layer_type, layer) in enumerate(layer_datum.items()):
        logger.info(f"Writing layer {layer_type.name}")
        if layer.empty:
            logger.warning(f"Layer {layer_type.name} is empty")
            continue
        if idx == 0:
            pyogrio.write_dataframe(
                layer,
                gpkg_path,
                layer=layer_type.name,
                append=layer_append,
                dataset_metadata=matadata,
            )
            layer_append = True
        else:
            pyogrio.write_dataframe(
                layer,
                gpkg_path,
                layer=layer_type.name,
                append=layer_append,
            )
        logger.info(f"Layer {layer_type.name} written")


def get_builder_context_cls(
    megmap_type: str,
) -> t.Type[BuilderContext]:
    builder_context_cls_map = {
        "apollo": ApolloBuilderContext,
        "memo": MemoBuilderContext,
    }
    return builder_context_cls_map[megmap_type]
