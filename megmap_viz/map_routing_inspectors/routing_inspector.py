from collections import deque
from typing import List, Dict, Set, Tuple, Union

import heapq

from .map_reader import ParserResult, RoadNode
from utils.random_color import generate_unique_color


class RoadNetwork:
    def __init__(self):
        self.nodes: Dict[str, RoadNode] = {}

    def add_road(
        self,
        road_id: str,
        length: float,
        parents: Set[str],
        children: Set[str],
    ):
        self.nodes[road_id] = RoadNode(road_id, length, parents, children)
        for parent in parents:
            if parent in self.nodes:
                self.nodes[parent].children.add(road_id)
        for child in children:
            if child in self.nodes:
                self.nodes[child].parents.add(road_id)

    def astar(self, start_id: str, end_id: str) -> Tuple[List[str], float]:
        pq = [(0.0, start_id)]
        dist = {node: float("inf") for node in self.nodes}
        prev = {node: "" for node in self.nodes}
        dist[start_id] = 0
        visited = set()

        while pq:
            curr_dist, curr_id = heapq.heappop(pq)
            if curr_dist > dist[curr_id]:
                continue
            visited.add(curr_id)
            for child in self.nodes[curr_id].children:
                new_dist = curr_dist + self.nodes[child].length
                if new_dist < dist[child]:
                    dist[child] = new_dist
                    prev[child] = curr_id
                    heapq.heappush(pq, (new_dist, child))

        if end_id not in visited:
            return list(visited), float("inf")

        path = []
        curr = end_id
        while curr != "":
            path.append(curr)
            curr = prev[curr]
        path.reverse()
        return path, dist[end_id]

    def get_all_paths(
        self, start_id: str, end_id: str
    ) -> Union[Tuple[List[str], float], List[Tuple[List[str], float]]]:
        paths = []
        visited_global = set()
        visited_local = set()

        def bfs(start_id: str, end_id: str):
            queue = deque([(start_id, [start_id], 0.0)])
            while queue:
                curr_id, path, distance = queue.popleft()
                visited_global.add(curr_id)
                if curr_id == end_id:
                    paths.append((path, distance))
                else:
                    for child in self.nodes[curr_id].children:
                        if child not in visited_local:
                            visited_local.add(child)
                            queue.append(
                                (
                                    child,
                                    path + [child],
                                    distance + self.nodes[child].length,
                                )
                            )

        bfs(start_id, end_id)

        if not paths:
            return list(visited_global), float("inf")

        return sorted(paths, key=lambda x: x[1])


class RoutingInspector:
    """
    查看输入 road id 是否有 routing
    返回所有可能路径；以及所有断点
    """

    def __init__(self, road_node_dict: ParserResult):
        self.__road_node_dict = road_node_dict
        self.__road_network = RoadNetwork()
        for road in self.__road_node_dict.values():
            self.__road_network.add_road(
                road.road_id, road.length, road.parents, road.children
            )
        self._existing_colors = []

        self.res = {}
        self.has_routing = True
        self.road_id_list = []

    def set_road_section_id_list(self, road_id_list: List[str]):
        self.road_id_list.clear()
        for road_id in road_id_list:
            self.road_id_list.append(road_id.rsplit("_", 1)[0] + "_0")

    def run(self) -> Union[Dict[str, Dict], List[str]]:
        valid, error_road_id = self.check_road_list_validity()

        if not valid:
            # print(f"Error in road ids: {error_road_id}")
            return error_road_id

        # 生成配对 road id
        road_id_pair_list = self.generate_road_id_pair()

        # 初始化 res
        self.has_routing = True
        self.res = {}
        self.first_fail_road_id_pair = None

        for idx, road_id_pair in enumerate(road_id_pair_list):
            self.path = []
            self.no_succ_lanes = []

            self.visited = set()
            path, dist = self.__road_network.astar(*road_id_pair)

            # record in res
            key_reformat = f"road_seg_{idx}"
            curr_seg_dict = {}
            curr_seg_dict["start_ref_lane_id"] = road_id_pair[0]
            curr_seg_dict["end_ref_lane_id"] = road_id_pair[1]
            if dist == float("inf"):  # no routing
                curr_seg_dict["path"] = []
                curr_seg_dict["has_routing"] = False
                curr_seg_dict["has_multi_routing"] = False
                self.has_routing = False
                self.first_fail_road_id_pair = road_id_pair
            else:  # one path
                curr_seg_dict["path"] = path
                curr_seg_dict["has_routing"] = True
                curr_seg_dict["has_multi_routing"] = False
            # else:  # multiple routing / paths
            #     curr_seg_dict["has_routing"] = True
            #     curr_seg_dict["has_multi_routing"] = False
            #     curr_seg_dict["path"] = None
            #     min_length = 0
            #     min_path_idx = 0
            #     for path_idx, path in enumerate(self.curr_path_res):
            #         length = 0
            #         for road_section_id in path:
            #             length += self.road_node_dict[road_section_id].length
            #         if length < min_length:
            #             min_length = length
            #             min_path_idx = path_idx
            #     curr_seg_dict["path"] = self.curr_path_res[min_path_idx]
            curr_seg_dict["no_succ_lanes"] = path
            curr_seg_dict["visited_lanes"] = path
            curr_seg_dict["color"] = generate_unique_color(
                self._existing_colors
            )
            self.res[key_reformat] = curr_seg_dict

            if not self.has_routing:
                break

        self.res_format()

        return self.res

    def res_format(self):
        res_summary = {}
        res_summary["has_routing"] = self.has_routing
        if not self.has_routing:
            res_summary[
                "first_failure_road_segment"
            ] = self.first_fail_road_id_pair
        # res_summary["road_ids_with_routing"] = self.succ_road_ids
        res_summary["ref_lane_ids"] = self.road_id_list

        self.res = {"summary": res_summary, "details": self.res}

    def generate_road_id_pair(self):
        """
        Generate pairs of road ids
        """
        return [
            (self.road_id_list[i], self.road_id_list[i + 1])
            for i in range(len(self.road_id_list) - 1)
        ]

    def check_road_list_validity(self) -> Tuple[bool, List[str]]:
        """
        Check if all road ids are in road node dict
        """
        valid = True
        error_road_id = []
        if len(self.road_id_list) < 2:
            valid = False
        for road in self.road_id_list:
            if road not in self.__road_node_dict:
                valid = False
                error_road_id.append(road)
        return valid, error_road_id
