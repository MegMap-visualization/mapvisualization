from typing import Set

from utils.random_color import generate_unique_color
from .map_reader import ParserResult


class AllRoutingInspector:
    def __init__(self, road_node_dict: ParserResult):
        self.road_node_dict = road_node_dict
        self.res = {}
        self.single_road_res = set()

        self._existing_colors = []

    def run(self):
        # 初始化s
        self.res = {}
        self.single_road_res = set()

        # 找 sub trees
        self.find_subtress()

        return {
            "submaps": self.res,
            "isolated_roads": {
                "color": generate_unique_color(self._existing_colors),
                "roads": list(self.single_road_res),
            },
        }

    def find_subtress(self):
        roads_list = set(self.road_node_dict.keys())  # 所有 roads id，不变
        remain_roads_list = set(self.road_node_dict.keys())  # 所有未经过的 roads id
        visited_road = set()  # 所有经过的 roads id
        count = 0
        while len(remain_roads_list) > 0:
            curr_road = remain_roads_list.pop()

            if curr_road in visited_road:
                continue

            if (
                len(self.road_node_dict[curr_road].children) == 0
                or len(self.road_node_dict[curr_road].parents) == 0
            ):
                visited_road.add(curr_road)
                remain_roads_list = roads_list - visited_road  # 减掉当前 road id
                self.single_road_res.add(curr_road)
                continue

            count += 1
            curr_in = set()
            curr_out = set()

            self.find_leaves(curr_road, visited_road, curr_in, curr_out)
            self.res[f"submap_{count}"] = {
                "roads": list(curr_in.union(curr_out)),
                "color": generate_unique_color(self._existing_colors),
            }
            remain_roads_list = roads_list - visited_road

        self.subtree_count = count

    def find_leaves(
        self, road, visited_road, curr_in: Set[str], curr_out: Set[str]
    ):
        if road in visited_road:
            return

        curr_road = self.road_node_dict[road]

        visited_road.add(road)

        if len(curr_road.parents) != 0:
            curr_in.update(curr_road.parents)
            for father in curr_road.parents:
                self.find_leaves(father, visited_road, curr_in, curr_out)

        if len(curr_road.children) != 0:
            curr_out.update(curr_road.children)
            for son in curr_road.children:
                self.find_leaves(son, visited_road, curr_in, curr_out)
