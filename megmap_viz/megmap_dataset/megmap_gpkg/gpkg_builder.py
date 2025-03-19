from __future__ import annotations
import abc
import typing as t
import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon, MultiPoint, box
from dataclasses import asdict

from .base_builder import BaseLayerBuilder, register_layer_builder
from ..datatypes import MegMapLayerType
from .gpkg_datatypes import DataRow, LaneProperty, BoundaryInfo

if t.TYPE_CHECKING:
    from ..datatypes import MegMapLayer
    from ..megmap_apollo.lane import (
        ApolloLane,
        ApolloLaneSection,
        ApolloLaneBorder,
    )
    from ..megmap_apollo.apollo_parser import ApolloParserResult
    from ..megmap_memo.memo_data_parser import MemoParserResult


def build_gdf(datum: t.Any) -> MegMapLayer:
    gdf = gpd.GeoDataFrame(data=datum, crs=4326)  # type: ignore
    gdf.set_geometry("geometry", inplace=True)
    # gdf["geometry_albers"] = gdf.to_crs(
    #     "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 "
    #     f"+lon_0=105 +x_0=0 +y_0=0 +ellps=GRS80 +units=m +no_defs",
    #     inplace=False,
    # ).geometry  # type: ignore
    # gdf.set_geometry("geometry_albers", inplace=True)
    return gdf


def get_pre_and_suc_road_section_ids(
    builder: BaseLayerBuilder,
    apollo_lane_section: ApolloLaneSection,
    side: t.Literal["left", "right"],
) -> t.Tuple[t.List[str], t.List[str]]:
    if side == "left":
        lanes = apollo_lane_section.left_lanes
    elif side == "right":
        lanes = apollo_lane_section.right_lanes
    else:
        return [], []

    pre_road_section_ids = set()
    suc_road_section_ids = set()

    for lane in lanes:
        for pre in lane.link.predecessors:
            if pre.lane_uid not in builder.context.data.lane_datum:
                continue
            pre_road_section_ids.add(
                builder.context.data.lane_datum[pre.lane_uid].road_section_id
            )
        for suc in lane.link.successors:
            if suc.lane_uid not in builder.context.data.lane_datum:
                continue
            suc_road_section_ids.add(
                builder.context.data.lane_datum[suc.lane_uid].road_section_id
            )

    return list(pre_road_section_ids), list(suc_road_section_ids)


def get_lane_group_boundary(
    apollo_lane_section: ApolloLaneSection, side: t.Literal["right", "left"]
) -> Polygon:
    if side == "left":
        left_line = apollo_lane_section.ref_line.border.geometry.sim_line
        right_line = apollo_lane_section.left_lanes[
            -1
        ].border.geometry.sim_line
    elif side == "right":
        left_line = apollo_lane_section.ref_line.border.geometry.sim_line
        right_line = apollo_lane_section.right_lanes[
            -1
        ].border.geometry.sim_line
    else:
        raise ValueError(f"Invalid side: {side}")

    return Polygon(list(left_line.reverse().coords) + list(right_line.coords))


def get_lane_uids(
    apollo_lane_section: ApolloLaneSection, side: t.Literal["right", "left"]
) -> t.List[str]:
    if side == "left":
        return [lane.uid for lane in apollo_lane_section.left_lanes]
    elif side == "right":
        return [lane.uid for lane in apollo_lane_section.right_lanes]
    else:
        return []


def get_lane_section_boundary(
    apollo_lane_section: ApolloLaneSection,
) -> Polygon:
    if apollo_lane_section.left_lanes and apollo_lane_section.right_lanes:
        # The reason why this is done is because
        # it is sorted during parsing.
        left_line = apollo_lane_section.left_lanes[-1].border.geometry.sim_line
        right_line = apollo_lane_section.right_lanes[
            -1
        ].border.geometry.sim_line
    elif (
        not apollo_lane_section.left_lanes and apollo_lane_section.right_lanes
    ):
        left_line = apollo_lane_section.ref_line.border.geometry.sim_line
        right_line = apollo_lane_section.right_lanes[
            -1
        ].border.geometry.sim_line
    elif (
        apollo_lane_section.left_lanes and not apollo_lane_section.right_lanes
    ):
        left_line = apollo_lane_section.ref_line.border.geometry.sim_line
        right_line = apollo_lane_section.left_lanes[
            -1
        ].border.geometry.sim_line
    else:
        # This situation will not happen
        # because it was checked during parsing.
        raise ValueError("Invalid lane section")

    return Polygon(list(left_line.reverse().coords) + list(right_line.coords))


def get_boundary_geom(
    boundary_gid: int, boundaries_layer: MegMapLayer
) -> LineString:
    geom_df = boundaries_layer.loc[
        boundaries_layer["gid"] == boundary_gid, "geometry"
    ]  # type: ignore
    return geom_df.iloc[0]


def get_lane_polygon(
    boundary_info: BoundaryInfo, boundaries_layer: MegMapLayer
) -> Polygon:
    left_bdry_gid = boundary_info.left_line_gid
    right_bdry_gid = boundary_info.right_line_gid

    left_bdry_geo: LineString = get_boundary_geom(
        left_bdry_gid, boundaries_layer
    )
    right_bdry_geo: LineString = get_boundary_geom(
        right_bdry_gid, boundaries_layer
    )

    rlbg: LineString = left_bdry_geo.reverse()
    return Polygon(list(right_bdry_geo.coords) + list(rlbg.coords))


def get_lane_data_row(
    gid: int,
    apollo_lane: ApolloLane,
    boundary_info: BoundaryInfo,
    boundaries_layer: MegMapLayer,
) -> DataRow:
    boundary_geo = get_lane_polygon(boundary_info, boundaries_layer)

    if apollo_lane.border.border_type is None:
        is_virtual: bool = False
    else:
        is_virtual: bool = apollo_lane.border.border_type.type == "virtual"

    lane_property: LaneProperty = {
        "road_id": apollo_lane.road_id,
        "road_section_id": apollo_lane.road_section_id,
        "lane_id": apollo_lane.id,
        "lane_uid": apollo_lane.uid,
        "lane_type": apollo_lane.type,
        "turn_type": apollo_lane.turn_type,
        "direction": apollo_lane.direction,
        "is_virtual": is_virtual,
        "length": apollo_lane.center_line.length,
        "color": apollo_lane.color,
        "border_type": apollo_lane.border_type,
        "speed_limit": "unkown",
        "predecessor_lane_uids": [],
        "successor_lane_uids": [],
        "left_same_neighbor_lane_uids": [],
        "right_same_neighbor_lane_uids": [],
        "left_opposite_neighbor_lane_uids": [],
        "right_opposite_neighbor_lane_uids": [],
        "signal_references": [],
        "object_references": [],
        "junction_references": [],
        "lane_references": [],
        "left_boundary_gid": boundary_info.left_line_gid,
        "right_boundary_gid": boundary_info.right_line_gid,
    }

    # add speed limit
    if apollo_lane.speed_limit:
        lane_property["speed_limit"] = str(apollo_lane.speed_limit.max)

    # add lane links
    for predecessor in apollo_lane.link.predecessors:
        t.cast(t.List[str], lane_property["predecessor_lane_uids"]).append(
            predecessor.lane_uid
        )
    for successor in apollo_lane.link.successors:
        t.cast(t.List[str], lane_property["successor_lane_uids"]).append(
            successor.lane_uid
        )
    for neighbor in apollo_lane.link.neighbors:
        if neighbor.direction != "same":
            t.cast(
                t.List[str],
                lane_property[
                    f"{neighbor.side}_opposite_neighbor_lane_uids"
                ],  # type: ignore
            ).append(neighbor.lane_uid)
        else:
            t.cast(
                t.List[str],
                lane_property[
                    f"{neighbor.side}_same_neighbor_lane_uids"
                ],  # type: ignore
            ).append(neighbor.lane_uid)

    # add signal overlap group
    for signal_ref in apollo_lane.signal_overlap_group:
        t.cast(t.Dict[str, t.List[str]], lane_property).setdefault(
            "signal_references", []
        ).append(signal_ref.id)
    # add object overlap group
    for object_ref in apollo_lane.object_overlap_group:
        t.cast(t.Dict[str, t.List[str]], lane_property).setdefault(
            "object_references", []
        ).append(object_ref.id)
    # add junction overlap group
    for junction_ref in apollo_lane.junction_overlap_group:
        t.cast(t.Dict[str, t.List[str]], lane_property).setdefault(
            "junction_references", []
        ).append(junction_ref.id)
    # add lane overlap group
    for lane_ref in apollo_lane.lane_overlap_group:
        t.cast(t.Dict[str, t.List[str]], lane_property).setdefault(
            "lane_references", []
        ).append(lane_ref.id)

    return DataRow(gid=gid, geometry=boundary_geo, **lane_property)


@register_layer_builder
class LaneBuilder(BaseLayerBuilder):
    layer_type = MegMapLayerType.LANE

    def build_from_apollo(self) -> None:
        self.context.data = t.cast("ApolloParserResult", self.context.data)
        lane_datum = []

        for apollo_lane in self.context.data.lane_datum.values():
            # virtual lanes are handled separately
            if apollo_lane.road_id in self.context.connecting_road_ids:
                continue

            # ignore reference lanes
            if apollo_lane.id == 0:
                continue

            lane_datum.append(
                get_lane_data_row(
                    self.context.auto_id,
                    apollo_lane,
                    self.context.lane_boundary_info[apollo_lane.uid],
                    self.context.boudary_layer,
                )
            )

        self.context.layer_datum[self.layer_type] = build_gdf(lane_datum)

        return None

    def build_from_memo(self) -> None:
        self.context.data = t.cast("MemoParserResult", self.context.data)
        datum = []

        for road_rv in self.context.data.roads.values():
            for lane_id in road_rv.raw_data["lane_ids"]:
                lane_rv = self.context.data.lanes[lane_id]
                datum.append(
                    DataRow(
                        gid=self.context.auto_id,
                        geometry=lane_rv.polygon,
                        lane_id=lane_id,
                        **lane_rv.raw_data,
                    )
                )

        if len(datum) == 0:
            return

        self.context.layer_datum[self.layer_type] = build_gdf(datum)


@register_layer_builder
class LaneConnectorBuilder(BaseLayerBuilder):
    layer_type = MegMapLayerType.LANE_CONNECTOR

    def build_from_apollo(self) -> None:
        self.context.data = t.cast("ApolloParserResult", self.context.data)
        lane_datum = []

        for apollo_lane in self.context.data.lane_datum.values():
            if apollo_lane.road_id not in self.context.connecting_road_ids:
                continue

            # ignore reference lanes
            if apollo_lane.id == 0:
                continue

            lane_datum.append(
                get_lane_data_row(
                    self.context.auto_id,
                    apollo_lane,
                    self.context.lane_boundary_info[apollo_lane.uid],
                    self.context.boudary_layer,
                )
            )
        if len(lane_datum) == 0:
            return
        
        self.context.layer_datum[self.layer_type] = build_gdf(lane_datum)

    def build_from_memo(self) -> None:
        pass


@register_layer_builder
class LaneBoundariesBuilder(BaseLayerBuilder):
    layer_type = MegMapLayerType.LANE_BOUNDARY

    def build_from_apollo(self) -> None:
        self.context.data = t.cast("ApolloParserResult", self.context.data)
        border_datum: t.List[DataRow] = []

        for (
            apollo_lane_section
        ) in self.context.data.lane_section_datum.values():
            ref_line = apollo_lane_section.ref_line

            for side in ["right", "left"]:
                if side == "left":
                    side_lanes = apollo_lane_section.left_lanes
                elif side == "right":
                    side_lanes = apollo_lane_section.right_lanes
                else:
                    continue

                if not side_lanes:
                    continue

                lanes = [ref_line] + side_lanes
                tmp_border_datum = []
                used_gids = set()
                lane_gids = []
                for idx, lane in enumerate(lanes):
                    if idx == 0:
                        lane_geom = (
                            lane.border.geometry.sim_line
                            if side == "right"
                            else lane.border.geometry.sim_line.reverse()
                        )
                    lane_geom = lane.border.geometry.sim_line
                    tmp_border_datum.append(
                        DataRow(
                            gid=self.context.auto_id,
                            geometry=lane_geom,
                            color=lane.color,
                            is_virtual=lane.border.is_virtual,
                            border_type=lane.border_type,
                            length=lane.border.geometry.line.length,
                            on_lane_uid=lane.uid,
                            is_left_border=False,
                        )
                    )
                    lane_gids.append(tmp_border_datum[-1].gid)

                lane_groups = [
                    lane_gids[i : i + 2] for i in range(len(lane_gids) - 1)
                ]
                for idx, lane_group in enumerate(lane_groups, start=1):
                    left_line_gid, right_line_gid = lane_group
                    if lanes[idx].left_border is not None:
                        left_border = t.cast(
                            "ApolloLaneBorder", lanes[idx].left_border
                        )
                        tmp_border_datum.append(
                            DataRow(
                                gid=self.context.auto_id,
                                geometry=left_border.geometry.sim_line,
                                color=left_border.color,
                                border_type=left_border.type,
                                is_virtual=left_border.is_virtual,
                                length=left_border.geometry.line.length,
                                on_lane_uid=lanes[idx].uid,
                                is_left_border=True,
                            )
                        )
                        left_line_gid = tmp_border_datum[-1].gid
                    used_gids.update((left_line_gid, right_line_gid))
                    self.context.lane_boundary_info[lanes[idx].uid] = (
                        BoundaryInfo(
                            left_line_gid=left_line_gid,
                            right_line_gid=right_line_gid,
                        )
                    )

                for bd in tmp_border_datum:
                    if bd.gid in used_gids:
                        border_datum.append(bd)

        self.context.layer_datum[self.layer_type] = build_gdf(border_datum)

    def build_from_memo(self) -> None:
        self.context.data = t.cast("MemoParserResult", self.context.data)
        datum = []

        line_ids = set()
        for road_rv in self.context.data.roads.values():
            for lane_id in road_rv.raw_data["lane_ids"]:
                lane_rv = self.context.data.lanes[lane_id]
                line_ids.add(lane_rv.raw_data["left_border"])
                line_ids.add(lane_rv.raw_data["right_border"])

        for line_id, line_rv in self.context.data.lines.items():
            if line_id in line_ids:
                datum.append(
                    DataRow(
                        gid=self.context.auto_id,
                        geometry=line_rv.geometry,
                        line_id=line_id,
                        **line_rv.raw_data,
                    )
                )

        if len(datum) == 0:
            return

        self.context.layer_datum[self.layer_type] = build_gdf(datum)


@register_layer_builder
class TrafficLightBuilder(BaseLayerBuilder):
    layer_type = MegMapLayerType.TRAFFIC_LIGHT

    def build_from_apollo(self) -> None:
        self.context.data = t.cast("ApolloParserResult", self.context.data)
        traffic_light_datum = []

        for apollo_signal in self.context.data.signal_datum.values():
            if apollo_signal.type.lower() != "trafficlight":
                continue
            signal_id = apollo_signal.id
            outline_geom = box(*apollo_signal.outline.bounds)

            subsignal_info = [
                {
                    "self_id": f"{signal_id}_{sub_signal.id}",
                    "sub_signal_type": sub_signal.type,
                    "center_point": f"{sub_signal.center_point.x},"
                    f"{sub_signal.center_point.y},{sub_signal.center_point.z}",
                }
                for sub_signal in apollo_signal.sub_signals
            ]

            traffic_light_datum.append(
                DataRow(
                    gid=self.context.auto_id,
                    geometry=outline_geom,
                    self_id=signal_id,
                    stopline_ref_ids=apollo_signal.stop_line_refs,
                    layout_type=apollo_signal.layout_type,
                    sub_signals_info=subsignal_info,
                )
            )

        if len(traffic_light_datum) == 0:
            return

        self.context.layer_datum[self.layer_type] = build_gdf(
            traffic_light_datum
        )

    def build_from_memo(self) -> None:
        pass


@register_layer_builder
class StopLineBuilder(BaseLayerBuilder):
    layer_type = MegMapLayerType.STOP_LINE

    def build_from_apollo(self) -> None:
        self.context.data = t.cast("ApolloParserResult", self.context.data)
        datum = []

        for apollo_object in self.context.data.object_datum.values():
            if apollo_object.type.lower() != "stopline":
                continue
            object_id = apollo_object.id
            geom = t.cast(LineString, apollo_object.outline)
            datum.append(
                DataRow(
                    gid=self.context.auto_id,
                    geometry=geom,
                    self_id=object_id,
                )
            )

        if len(datum) == 0:
            return

        self.context.layer_datum[self.layer_type] = build_gdf(datum)

    def build_from_memo(self) -> None:
        self.context.data = t.cast("MemoParserResult", self.context.data)
        datum = []
        for oid, obj in self.context.data.objects.items():
            if obj.raw_data["type"] != "stopline":
                continue
            datum.append(
                DataRow(
                    gid=self.context.auto_id,
                    geometry=obj.geometry,
                    stop_line_id=oid,
                    **obj.raw_data,
                )
            )

        if len(datum) == 0:
            return

        self.context.layer_datum[self.layer_type] = build_gdf(datum)


@register_layer_builder
class CrosswalkBuilder(BaseLayerBuilder):
    layer_type = MegMapLayerType.CROSSWALK

    def build_from_apollo(self) -> None:
        self.context.data = t.cast("ApolloParserResult", self.context.data)
        datum = []

        for apollo_object in self.context.data.object_datum.values():
            if apollo_object.type.lower() != "crosswalk":
                continue
            object_id = apollo_object.id
            geom = t.cast(Polygon, apollo_object.outline)
            datum.append(
                DataRow(
                    gid=self.context.auto_id,
                    geometry=geom,
                    self_id=object_id,
                )
            )

        if len(datum) == 0:
            return

        self.context.layer_datum[self.layer_type] = build_gdf(datum)

    def build_from_memo(self) -> None:
        pass


@register_layer_builder
class IntersectionBuilder(BaseLayerBuilder):
    layer_type = MegMapLayerType.INTERSECTION

    def build_from_apollo(self) -> None:
        self.context.data = t.cast("ApolloParserResult", self.context.data)

        # 检查是否有交叉路口数据(处理新地图字段修改情况)
        if not hasattr(self.context.data, 'junction_datum') or not self.context.data.junction_datum:
            return
        
        datum = []

        for apollo_junction in self.context.data.junction_datum.values():
            junct_id = apollo_junction.id
            geom = apollo_junction.outline

            connecting_road_ids = []
            incomming_lane_uids = []
            for conn in apollo_junction.connections:
                connecting_road_ids.append(conn.connecting_road)
                incomming_lane_uids.append(conn.incoming_road)

            datum.append(
                DataRow(
                    gid=self.context.auto_id,
                    geometry=geom,
                    junction_id=junct_id,
                    connecting_road_ids=connecting_road_ids,
                    incomming_lane_uids=incomming_lane_uids,
                )
            )

        self.context.layer_datum[self.layer_type] = build_gdf(datum)

    def build_from_memo(self) -> None:
        pass


@register_layer_builder
class BaselinePathsBuilder(BaseLayerBuilder):
    layer_type = MegMapLayerType.BASELINE_PATH

    def build_from_apollo(self) -> None:
        self.context.data = t.cast("ApolloParserResult", self.context.data)
        datum = []

        for apollo_lane in self.context.data.lane_datum.values():
            geom = apollo_lane.center_line.sim_line
            lane_uid = apollo_lane.uid

            if apollo_lane.border.border_type is None:
                is_virtual: bool = False
            else:
                is_virtual: bool = (
                    apollo_lane.border.border_type.type == "virtual"
                )

            datum.append(
                DataRow(
                    gid=self.context.auto_id,
                    geometry=geom,
                    lane_uid=lane_uid,
                    is_virtual=is_virtual,
                )
            )

        self.context.layer_datum[self.layer_type] = build_gdf(datum)

    def build_from_memo(self) -> None:
        self.context.data = t.cast("MemoParserResult", self.context.data)
        datum = []

        for road_rv in self.context.data.roads.values():
            for lane_id in road_rv.raw_data["lane_ids"]:
                lane_rv = self.context.data.lanes[lane_id]
                datum.append(
                    DataRow(
                        gid=self.context.auto_id,
                        geometry=lane_rv.centerline,
                        lane_id=lane_id,
                        **lane_rv.raw_data,
                    )
                )

        if len(datum) == 0:
            return

        self.context.layer_datum[self.layer_type] = build_gdf(datum)


@register_layer_builder
class LaneGroupPolygonBuilder(BaseLayerBuilder):
    layer_type = MegMapLayerType.LANE_GROUP_POLYGON

    def build_from_apollo(self) -> None:
        self.context.data = t.cast("ApolloParserResult", self.context.data)

        datum = []

        for apollo_road in self.context.data.road_datum.values():
            road_id = apollo_road.id

            for apollo_lane_section in apollo_road.lanes:
                lane_section_id = apollo_lane_section.id
                sides = []
                if apollo_lane_section.left_lanes:
                    sides.append("left")
                if apollo_lane_section.right_lanes:
                    sides.append("right")

                for side in sides:
                    bdry_polygon = get_lane_group_boundary(
                        apollo_lane_section, side
                    )
                    (
                        pre_road_section_ids,
                        suc_road_section_ids,
                    ) = get_pre_and_suc_road_section_ids(
                        self, apollo_lane_section, side
                    )
                    datum.append(
                        DataRow(
                            gid=self.context.auto_id,
                            geometry=bdry_polygon,
                            road_section_id=f"{road_id}_{lane_section_id}",
                            road_type=apollo_road.type,
                            lane_uids=get_lane_uids(apollo_lane_section, side),
                            side_on_ref_line=side,
                            junction_id=(
                                apollo_road.junction
                                if apollo_road.junction != "-1"
                                else None
                            ),
                            pre_road_section_ids=pre_road_section_ids,
                            suc_road_section_ids=suc_road_section_ids,
                        )
                    )

        self.context.layer_datum[self.layer_type] = build_gdf(datum)

    def build_from_memo(self) -> None:
        self.context.data = t.cast("MemoParserResult", self.context.data)
        datum = []

        for road_id, road_rv in self.context.data.roads.items():
            datum.append(
                DataRow(
                    gid=self.context.auto_id,
                    geometry=road_rv.polygon,
                    road_id=road_id,
                    **road_rv.raw_data,
                )
            )

        if len(datum) == 0:
            return

        self.context.layer_datum[self.layer_type] = build_gdf(datum)


@register_layer_builder
class ReferenceLineBuilder(BaseLayerBuilder):
    layer_type = MegMapLayerType.REFERENCE_LINE

    def get_pre_and_suc_road_section_ids(
        self, apollo_lane_section: ApolloLaneSection
    ) -> t.Tuple[t.List[str], t.List[str]]:
        pre_road_section_ids = set()
        suc_road_section_ids = set()

        lanes = (
            apollo_lane_section.left_lanes + apollo_lane_section.right_lanes
        )
        for lane in lanes:
            for pre in lane.link.predecessors:
                if pre.lane_uid not in self.context.data.lane_datum:
                    continue
                pre_road_section_ids.add(
                    self.context.data.lane_datum[pre.lane_uid].road_section_id
                )
            for suc in lane.link.successors:
                if suc.lane_uid not in self.context.data.lane_datum:
                    continue
                suc_road_section_ids.add(
                    self.context.data.lane_datum[suc.lane_uid].road_section_id
                )

        return list(pre_road_section_ids), list(suc_road_section_ids)

    def build_from_apollo(self) -> None:
        self.context.data = t.cast("ApolloParserResult", self.context.data)

        datum = []

        for apollo_road in self.context.data.road_datum.values():
            road_id = apollo_road.id

            for apollo_lane_section in apollo_road.lanes:
                lane_section_id = apollo_lane_section.id

                left_lane_uids = [
                    apollo_lane.uid
                    for apollo_lane in apollo_lane_section.left_lanes
                ]
                right_lane_uids = [
                    apollo_lane.uid
                    for apollo_lane in apollo_lane_section.right_lanes
                ]

                (
                    pre_road_section_ids,
                    suc_road_section_ids,
                ) = self.get_pre_and_suc_road_section_ids(apollo_lane_section)

                reference_line = (
                    apollo_lane_section.ref_line.border.geometry.sim_line
                )
                datum.append(
                    DataRow(
                        gid=self.context.auto_id,
                        geometry=reference_line,
                        road_section_id=f"{road_id}_{lane_section_id}",
                        left_backward_lane_uids=left_lane_uids,
                        right_forward_lane_uids=right_lane_uids,
                        road_type=apollo_road.type,
                        junction_id=(
                            apollo_road.junction
                            if apollo_road.junction != "-1"
                            else None
                        ),
                        pre_road_section_ids=pre_road_section_ids,
                        suc_road_section_ids=suc_road_section_ids,
                    )
                )

        self.context.layer_datum[self.layer_type] = build_gdf(datum)

    def build_from_memo(self) -> None:
        self.context.data = t.cast("MemoParserResult", self.context.data)
        datum = []

        for line_id, line_rv in self.context.data.lines.items():
            if line_rv.raw_data.get("border_type") == "ins":
                if not line_rv.raw_data.get("length"):
                    line_rv.raw_data["length"] = -1
                datum.append(
                    DataRow(
                        gid=self.context.auto_id,
                        geometry=line_rv.sim_geometry,
                        line_id=line_id,
                        **line_rv.raw_data,
                    )
                )

        if len(datum) == 0:
            return

        self.context.layer_datum[self.layer_type] = build_gdf(datum)
