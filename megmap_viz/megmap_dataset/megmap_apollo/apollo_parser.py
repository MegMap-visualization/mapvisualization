from __future__ import annotations
import os
import logging
import typing as t
from functools import reduce
from itertools import zip_longest
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import gc

from lxml import etree
from shapely.geometry import Polygon, Point, LineString, MultiPoint

from .base import ApolloGeometry, ApolloReference
from .juntion import (
    ApolloJunction,
    ApolloJunctionConnection,
    ContactPointType,
)
from .lane import (
    ApolloLane,
    ApolloLanePredecessor,
    ApolloLaneNeighbor,
    ApolloLaneSuccessor,
    ApolloLaneSpeedLimit,
    ApolloLaneLink,
    ApolloLaneBorderType,
    ApolloLaneBorder,
    ApolloLaneRoadSampleAssociation,
    ApolloLaneSampleAssociate,
    ApolloLaneSection,
    ApolloLaneBoundary,
)
from .object import ApolloObject, ObjectType
from .road import ApolloRoad
from .signal import (
    ApolloSignal,
    SubSignalType,
    SignalType,
    ApolloSubSignal,
)

if t.TYPE_CHECKING:
    from concurrent.futures import Future


logger = logging.getLogger(__name__)


@dataclass
class ApolloParserResult:
    road_datum: t.Dict[str, ApolloRoad]
    lane_section_datum: t.Dict[str, ApolloLaneSection]
    lane_datum: t.Dict[str, ApolloLane]
    object_datum: t.Dict[str, ApolloObject]
    signal_datum: t.Dict[str, ApolloSignal]
    junction_datum: t.Dict[str, ApolloJunction]

    def __iadd__(self, o: ApolloParserResult) -> ApolloParserResult:
        self.road_datum.update(o.road_datum)
        self.lane_section_datum.update(o.lane_section_datum)
        self.lane_datum.update(o.lane_datum)
        self.object_datum.update(o.object_datum)
        self.signal_datum.update(o.signal_datum)
        self.junction_datum.update(o.junction_datum)
        return self


class ApolloParser:
    def __init__(self, apollo_xml: t.Union[str, etree._Element]) -> None:
        self.road_datum: t.Dict[str, ApolloRoad] = {}
        self.lane_datum: t.Dict[str, ApolloLane] = {}
        self.lane_section_datum: t.Dict[str, ApolloLaneSection] = {}
        self.object_datum: t.Dict[str, ApolloObject] = {}
        self.signal_datum: t.Dict[str, ApolloSignal] = {}
        self.junction_datum: t.Dict[str, ApolloJunction] = {}

        self._curr_road_id: t.Optional[str] = None
        self._curr_sec_id: t.Optional[int] = None
        self._curr_lane_id: t.Optional[int] = None
        self._curr_lane_uid: t.Optional[str] = None

        self.apollo_xml = apollo_xml

    def get_result(self) -> ApolloParserResult:
        if isinstance(self.apollo_xml, str):
            apollo_xml = etree.fromstring(self.apollo_xml)
        else:
            apollo_xml = self.apollo_xml

        road_eles = apollo_xml.findall("road")
        junction_eles = apollo_xml.findall("junction")
        self.parse_roads(road_eles)
        self.parse_junctions(junction_eles)

        return ApolloParserResult(
            road_datum=self.road_datum,
            lane_datum=self.lane_datum,
            lane_section_datum=self.lane_section_datum,
            object_datum=self.object_datum,
            signal_datum=self.signal_datum,
            junction_datum=self.junction_datum,
        )

    @classmethod
    def run(cls, apollo_xml_str: str) -> ApolloParserResult:
        return cls(apollo_xml_str).get_result()

    def parse_roads(self, road_eles: t.List[etree._Element]) -> None:
        for road_ele in road_eles:
            self._curr_road_id = str(road_ele.attrib["id"])
            road_type = str(road_ele.attrib["type"])
            junction = str(road_ele.attrib["junction"])

            # lane sections
            lanes_ele = road_ele.find("lanes")
            if lanes_ele is None:
                logger.warning("Road %s has no lanes", road_ele.attrib["id"])
                continue
            lane_section_eles = lanes_ele.findall("laneSection")
            apollo_lane_sections = self._parse_lane_sections(lane_section_eles)

            signal_eles = list(road_ele.iterdescendants("signal"))
            object_eles = list(road_ele.iterdescendants("object"))

            # signals
            apollo_signals = self._parse_signals(signal_eles=signal_eles)

            # objects
            apollo_objects = self._parse_objects(object_eles=object_eles)

            apollo_road = ApolloRoad(
                id_=self._curr_road_id,
                type_=road_type,
                junction=junction,
                lanes=apollo_lane_sections,
                signals=apollo_signals,
                objects=apollo_objects,
            )

            self.road_datum[self._curr_road_id] = apollo_road

    def parse_junctions(self, junction_eles: t.List[etree._Element]) -> None:
        for junction_ele in junction_eles:
            jun_id = str(junction_ele.attrib["id"])
            apollo_outline = self._parse_outline(
                junction_ele, outline_type=Polygon
            )

            conn_eles = junction_ele.findall("connection")
            apollo_connections = [
                ApolloJunctionConnection(
                    id_=int(conn_ele.attrib["id"]),
                    incoming_road=str(conn_ele.attrib["incomingRoad"]),
                    connecting_road=str(conn_ele.attrib["connectingRoad"]),
                    contact_point=t.cast(
                        ContactPointType, conn_ele.attrib["contactPoint"]
                    ),
                )
                for conn_ele in conn_eles
            ]

            apollo_junction = ApolloJunction(
                id_=jun_id,
                outline=apollo_outline,
                connections=apollo_connections,
            )

            self.junction_datum[jun_id] = apollo_junction

    def _parse_outline(
        self,
        outline_ele: etree._Element,
        outline_type: t.Type[t.Union[Polygon, MultiPoint]],
    ) -> t.Union[Polygon, LineString, MultiPoint]:
        points = list(outline_ele.iterdescendants("cornerGlobal"))
        if not points:
            logger.error(
                "Road %s signal/object has no cornerGlobal element",
                self._curr_road_id,
            )
            raise ValueError(
                f"Road {self._curr_road_id} "
                f"signal/object has no cornerGlobal element"
            )
        points = [
            Point(float(point.attrib["x"]), float(point.attrib["y"]))
            for point in points
        ]
        return outline_type(points)

    def _parse_geometry(self, geometry_ele: etree._Element) -> ApolloGeometry:
        s_offset = float(geometry_ele.attrib["sOffset"])
        x = float(geometry_ele.attrib["x"])
        y = float(geometry_ele.attrib["y"])
        z = float(geometry_ele.attrib["z"])
        length = float(geometry_ele.attrib["length"])

        points = list(geometry_ele.iterdescendants("point"))
        if not points:
            raise ValueError(
                f"Road {self._curr_road_id} Section"
                f" {self._curr_sec_id}: Geometry has no point element"
            )
        points = [
            Point(float(point.attrib["x"]), float(point.attrib["y"]))
            for point in points
        ]

        return ApolloGeometry(
            s_offset=s_offset,
            x=x,
            y=y,
            z=z,
            length=length,
            line=LineString(points),
        )

    def _parse_lane(self, lane_ele: etree._Element) -> t.Optional[ApolloLane]:
        lane_id = int(lane_ele.attrib["id"])
        lane_uid = str(lane_ele.attrib["uid"])
        lane_type = str(lane_ele.attrib["type"])
        lane_direction = str(lane_ele.attrib["direction"])
        turn_type = str(lane_ele.attrib["turnType"])

        # link
        link_ele = lane_ele.find("link")

        if link_ele is None:
            logger.error(
                "Road %s Lane %s has no link", self._curr_road_id, lane_uid
            )
            return None

        pre_eles = link_ele.findall("predecessor")
        apollo_pres = []
        for pre_ele in pre_eles:
            apollo_pres.append(
                ApolloLanePredecessor(str(pre_ele.attrib["id"]))
            )

        nei_eles = link_ele.findall("neighbor")
        apollo_neis = []
        for nei_ele in nei_eles:
            apollo_neis.append(
                ApolloLaneNeighbor(
                    str(nei_ele.attrib["id"]),
                    side=t.cast(
                        t.Literal["left", "right"], nei_ele.attrib["side"]
                    ),
                    direction=str(nei_ele.attrib["direction"]),
                )
            )

        suc_eles = link_ele.findall("successor")
        apollo_sucs = []
        for suc_ele in suc_eles:
            apollo_sucs.append(ApolloLaneSuccessor(str(suc_ele.attrib["id"])))

        apollo_link = ApolloLaneLink(
            predecessors=apollo_pres,
            neighbors=apollo_neis,
            successors=apollo_sucs,
        )

        # speed_limit
        speed_limit_ele = lane_ele.find("speed")
        apollo_speed_limit = None
        if speed_limit_ele is not None:
            apollo_speed_limit = ApolloLaneSpeedLimit(
                max=int(speed_limit_ele.attrib["max"]),
            )
        elif lane_id != 0:
            logger.warning(
                "Road %s Lane %s has no speed limit",
                self._curr_road_id,
                lane_uid,
            )

        # border
        border_ele = lane_ele.find("border")
        if border_ele is None:
            logger.error(
                "Road %s Lane %s has no border", self._curr_road_id, lane_uid
            )
            return None

        border_type_ele = border_ele.find("borderType")
        apollo_border_type = None
        if border_type_ele is None:
            logger.warning(
                "Road %s Lane %s has no border type",
                self._curr_road_id,
                lane_uid,
            )
        else:
            apollo_border_type = ApolloLaneBorderType(
                s_offset=float(border_type_ele.attrib["sOffset"]),
                type=str(border_type_ele.attrib["type"]),
                color=str(border_type_ele.attrib["color"]),
            )

        border_geo_ele = border_ele.find("geometry")
        if border_geo_ele is None:
            logger.error(
                "Road %s Lane %s has no border geometry",
                self._curr_road_id,
                lane_uid,
            )
            return None
        apollo_border_geo = self._parse_geometry(border_geo_ele)

        apollo_border = ApolloLaneBorder(
            border_type=apollo_border_type, geometry=apollo_border_geo
        )

        # left border
        left_border_ele = lane_ele.find("leftBorder")
        apollo_left_border = None
        if left_border_ele is not None:
            border_type_ele = left_border_ele.find("borderType")
            apollo_border_type = None
            if border_type_ele is None:
                logger.warning(
                    "Road %s Lane %s has no border type",
                    self._curr_road_id,
                    lane_uid,
                )
            else:
                apollo_border_type = ApolloLaneBorderType(
                    s_offset=float(border_type_ele.attrib["sOffset"]),
                    type=str(border_type_ele.attrib["type"]),
                    color=str(border_type_ele.attrib["color"]),
                )
            left_border_geo_ele = left_border_ele.find("geometry")
            if left_border_geo_ele is None:
                logger.warning(
                    "Road %s Lane %s has no left border geometry",
                    self._curr_road_id,
                    lane_uid,
                )
            else:
                apollo_left_border_geo = self._parse_geometry(
                    left_border_geo_ele
                )
                apollo_left_border = ApolloLaneBorder(
                    border_type=apollo_border_type,
                    geometry=apollo_left_border_geo,
                )

        # center line
        center_line_ele = lane_ele.find("centerLine")
        if center_line_ele is None:
            logger.error(
                "Road %s Lane %s has no center line",
                self._curr_road_id,
                lane_uid,
            )
            return None
        center_line_geo_ele = center_line_ele.find("geometry")
        if center_line_geo_ele is None:
            logger.error(
                "Road %s Lane %s has no center line geometry",
                self._curr_road_id,
                lane_uid,
            )
            return None
        apollo_center_line = self._parse_geometry(center_line_geo_ele)

        # sample associates
        sample_associate_eles = list(
            lane_ele.iterdescendants("sampleAssociate")
        )
        apollo_sample_associates = [
            ApolloLaneSampleAssociate(
                float(sample_associate_ele.attrib["sOffset"]),
                float(sample_associate_ele.attrib["leftWidth"]),
                float(sample_associate_ele.attrib["rightWidth"]),
            )
            for sample_associate_ele in sample_associate_eles
        ]

        # road sample associations
        road_sample_association_eles = list(
            lane_ele.iterdescendants("roadSampleAssociation")
        )
        apollo_road_sample_associations = [
            ApolloLaneRoadSampleAssociation(
                float(road_sample_association_ele.attrib["sOffset"]),
                float(road_sample_association_ele.attrib["leftWidth"]),
                float(road_sample_association_ele.attrib["rightWidth"]),
            )
            for road_sample_association_ele in road_sample_association_eles
        ]

        # signal overlap group
        signal_overlap_eles = lane_ele.iterdescendants("signalReference")
        apollo_signal_overlap_group = [
            ApolloReference(
                str(signal_overlap.attrib["id"]),
                float(signal_overlap.attrib["startOffset"]),
                float(signal_overlap.attrib["endOffset"]),
            )
            for signal_overlap in signal_overlap_eles
        ]

        # object overlap group
        object_overlap_eles = lane_ele.iterdescendants("objectReference")
        apollo_object_overlap_group = [
            ApolloReference(
                str(object_overlap.attrib["id"]),
                float(object_overlap.attrib["startOffset"]),
                float(object_overlap.attrib["endOffset"]),
            )
            for object_overlap in object_overlap_eles
        ]

        # junction overlap group
        junction_overlap_eles = lane_ele.iterdescendants("junctionReference")
        apollo_junction_overlap_group = [
            ApolloReference(
                str(junction_overlap.attrib["id"]),
                float(junction_overlap.attrib["startOffset"]),
                float(junction_overlap.attrib["endOffset"]),
            )
            for junction_overlap in junction_overlap_eles
        ]

        # lane overlap group
        lane_overlap_eles = lane_ele.iterdescendants("laneReference")
        apollo_lane_overlap_group = [
            ApolloReference(
                str(lane_overlap.attrib["id"]),
                float(lane_overlap.attrib["startOffset"]),
                float(lane_overlap.attrib["endOffset"]),
            )
            for lane_overlap in lane_overlap_eles
        ]

        apollo_lane = ApolloLane(
            id_=lane_id,
            uid=lane_uid,
            type_=lane_type,
            direction=lane_direction,
            turn_type=turn_type,
            speed_limit=apollo_speed_limit,
            link=apollo_link,
            border=apollo_border,
            left_border=apollo_left_border,
            center_line=apollo_center_line,
            sample_associates=apollo_sample_associates,
            road_sample_associations=apollo_road_sample_associations,
            signal_overlap_group=apollo_signal_overlap_group,
            object_overlap_group=apollo_object_overlap_group,
            junction_overlap_group=apollo_junction_overlap_group,
            lane_overlap_group=apollo_lane_overlap_group,
        )

        return apollo_lane

    def _parse_boundary(
        self, boudary_eles: t.Tuple[etree._Element, etree._Element]
    ) -> ApolloLaneBoundary:
        if len(boudary_eles) > 2:
            logger.error(
                f"Road ID: {self._curr_road_id} "
                f"Lane Section ID: {self._curr_sec_id} >> Error Boundary Data"
            )
            raise ValueError("cannot parse boundary")

        left_boundary = None
        right_boundary = None
        for boundary_ele in boudary_eles:
            geo_ele = boundary_ele.find("geometry")
            if geo_ele is None:
                continue
            apollo_geo = self._parse_geometry(geo_ele)
            if boundary_ele.attrib["type"].lower() == "leftboundary":
                left_boundary = apollo_geo
            else:
                right_boundary = apollo_geo

        if left_boundary is None or right_boundary is None:
            logger.error(
                f"Road ID: {self._curr_road_id} "
                f"Lane Section ID: {self._curr_sec_id} >> Error Boundary Data"
            )
            raise ValueError("cannot parse boundary")
        else:
            return ApolloLaneBoundary(left=left_boundary, right=right_boundary)

    def _parse_objects(
        self, object_eles: t.List[etree._Element]
    ) -> t.List[ApolloObject]:
        apollo_obejcts = []

        for object_ele in object_eles:
            object_id = str(object_ele.attrib["id"])
            object_type = t.cast(ObjectType, object_ele.attrib["type"])

            apollo_outline = None
            if object_type == "crosswalk":
                apollo_outline = self._parse_outline(
                    object_ele, outline_type=Polygon
                )
            elif object_type == "stopline":
                geometry_ele = object_ele.find("geometry")
                if geometry_ele is None:
                    logger.warning(
                        "Road %s Object %s has no geometry",
                        self._curr_road_id,
                        object_id,
                    )
                    continue
                apollo_outline = self._parse_geometry(geometry_ele).line
            if apollo_outline is None:
                continue

            apollo_object = ApolloObject(
                id_=object_id, type_=object_type, outline=apollo_outline
            )
            self.object_datum[object_id] = apollo_object
            apollo_obejcts.append(apollo_object)

        return apollo_obejcts

    def _parse_signals(
        self, signal_eles: t.List[etree._Element]
    ) -> t.List[ApolloSignal]:
        apollo_signals = []

        for signal_ele in signal_eles:
            signal_id = str(signal_ele.attrib["id"])
            signal_type = t.cast(SignalType, signal_ele.attrib["type"])
            layout_type = str(signal_ele.attrib["layoutType"])

            outline_ele = signal_ele.find("outline")
            if outline_ele is None:
                logger.warning(
                    "Road %s Signal %s has no outline",
                    self._curr_road_id,
                    signal_id,
                )
                continue
            apollo_outline = self._parse_outline(
                outline_ele, outline_type=MultiPoint
            )

            # stopline ref
            stopline_ele = signal_ele.find("stopLine")
            if stopline_ele is not None:
                stop_line_ref_eles = stopline_ele.findall("objectReference")
                stop_line_refs = [
                    str(stop_line_ref.attrib["id"])
                    for stop_line_ref in stop_line_ref_eles
                ]
            else:
                stop_line_refs = []

            # sub signals
            sub_signal_eles = signal_ele.findall("subSignal")
            apollo_sub_signals = []
            for sub_signal_ele in sub_signal_eles:
                sub_signal_type = t.cast(
                    SubSignalType, sub_signal_ele.attrib["type"]
                )
                sub_signal_id = str(sub_signal_ele.attrib["id"])
                center_point_ele = sub_signal_ele.find("centerPoint")
                if center_point_ele is None:
                    logger.warning(
                        "Road %s Signal %s SubSignal %s has no center point",
                        self._curr_road_id,
                        signal_id,
                        sub_signal_id,
                    )
                    continue
                center_point = Point(
                    float(center_point_ele.attrib["x"]),
                    float(center_point_ele.attrib["y"]),
                    float(center_point_ele.attrib["z"]),
                )
                apollo_sub_signals.append(
                    ApolloSubSignal(
                        id_=sub_signal_id,
                        type_=sub_signal_type,
                        center_point=center_point,
                    )
                )

            apollo_signal = ApolloSignal(
                id_=signal_id,
                type_=signal_type,
                layout_type=layout_type,
                outline=apollo_outline,
                stop_line_refs=stop_line_refs,
                sub_signals=apollo_sub_signals,
            )
            self.signal_datum[signal_id] = apollo_signal
            apollo_signals.append(apollo_signal)

        return apollo_signals

    def _parse_lane_sections(
        self, lane_section_eles: t.List[etree._Element]
    ) -> t.List[ApolloLaneSection]:
        apollo_lane_sections: t.List[ApolloLaneSection] = []

        for sec_id, lane_section_ele in enumerate(lane_section_eles):
            self._curr_sec_id = sec_id

            boudary_eles = tuple(lane_section_ele.iterdescendants("boundary"))
            apollo_boundary = self._parse_boundary(
                t.cast(t.Tuple[etree._Element, etree._Element], boudary_eles)
            )

            apollo_left_lanes: t.List[ApolloLane] = []
            apollo_right_lanes: t.List[ApolloLane] = []
            apollo_center_lane: t.Optional[ApolloLane] = None
            for side in ("center", "left", "right"):
                side_ele = lane_section_ele.find(side)
                if side_ele is None:
                    logger.info(
                        "Road %s Section %s has no %s lane",
                        self._curr_road_id,
                        self._curr_sec_id,
                        side,
                    )
                    continue

                lane_eles = side_ele.findall("lane")
                apollo_lanes: t.List[ApolloLane] = []
                for lane_ele in lane_eles:
                    apollo_lane = self._parse_lane(lane_ele)
                    if apollo_lane is None:
                        continue
                    self.lane_datum[apollo_lane.uid] = apollo_lane
                    apollo_lanes.append(apollo_lane)

                if side == "left":
                    apollo_lanes.sort()
                    apollo_left_lanes = apollo_lanes
                elif side == "right":
                    apollo_lanes.sort(reverse=True)
                    apollo_right_lanes = apollo_lanes
                else:
                    if not apollo_lanes:
                        logger.error(
                            "Road %s, Section %s has no center lane",
                            self._curr_road_id,
                            self._curr_sec_id,
                        )
                        raise ValueError(
                            f"Road {self._curr_road_id}, "
                            f"Section {self._curr_sec_id} has no center lane"
                        )
                    apollo_center_lane = apollo_lanes[0]
                    # section_id不一定是连续的，所以最终下面的逻辑不能用sec_id
                    self._curr_sec_id = apollo_center_lane.section_id
            if (
                not apollo_left_lanes
                and not apollo_right_lanes
                or apollo_center_lane is None
            ):
                # need not to raise error when there is no center lane
                # beacuse having raised error when parsing center lane
                logger.error(
                    "Road %s, Section %s has no left and right lane",
                    self._curr_road_id,
                    self._curr_sec_id,
                )
                raise ValueError(
                    f"Road {self._curr_road_id}, "
                    f"Section {self._curr_sec_id} has no left and right lane"
                )
            apollo_lane_section = ApolloLaneSection(
                id_=apollo_center_lane.section_id,
                boundary=apollo_boundary,
                left_lanes=apollo_left_lanes,
                right_lanes=apollo_right_lanes,
                ref_line=apollo_center_lane,
            )

            self.lane_section_datum[apollo_center_lane.road_section_id] = (
                apollo_lane_section
            )

            apollo_lane_sections.append(apollo_lane_section)

        return apollo_lane_sections


class MultiApolloParser:
    def __init__(self, apollo_xml: etree._Element) -> None:
        self._proc_pool = ProcessPoolExecutor(max_workers=4)

        self._futures: t.List[Future] = []

        self.tasks = self.get_tasks(apollo_xml)

    def get_tasks(self, apollo_xml: etree._Element) -> t.List[str]:
        roads = apollo_xml.findall("road")
        junctions = apollo_xml.findall("junction")

        cpu_num = os.cpu_count()
        if cpu_num is None:
            cpu_num = 1

        road_chunk_size = len(roads) // cpu_num
        junction_chunk_size = len(junctions) // cpu_num

        if road_chunk_size == 0:
            road_chunk_size = 1
        if junction_chunk_size == 0:
            junction_chunk_size = 1

        road_chunks = [
            roads[i : i + road_chunk_size]
            for i in range(0, len(roads), road_chunk_size)
        ]
        junction_chunks = [
            junctions[i : i + junction_chunk_size]
            for i in range(0, len(junctions), junction_chunk_size)
        ]

        tasks: t.List[str] = []
        road_chunk: t.Union[t.List[etree._Element], t.List]
        junction_chunk: t.Union[t.List[etree._Element], t.List]
        for road_chunk, junction_chunk in zip_longest(
            road_chunks, junction_chunks, fillvalue=[]
        ):
            r = etree.Element("apollo")
            r.extend(road_chunk)
            r.extend(junction_chunk)
            tasks.append(
                etree.tostring(r, encoding="utf-8", pretty_print=True).decode()
            )
            del r

        return tasks

    def run(self) -> ApolloParserResult:
        for task in self.tasks:
            self._futures.append(
                self._proc_pool.submit(ApolloParser.run, task)
            )
            del task

        parser_results = []
        for r in as_completed(self._futures):
            parser_results.append(r.result())

        self._proc_pool.shutdown(wait=False)

        return reduce(ApolloParserResult.__iadd__, parser_results)
