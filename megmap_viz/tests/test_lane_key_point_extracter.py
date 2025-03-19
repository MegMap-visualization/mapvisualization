import time

from utils.file_op import smart_read
from lxml import etree
from lane_key_point_extracter.lane_key_point_extracter import (
    LaneKeyPointExtracter,
)

# TEST_MAP_PATH = "s3://zjf-map/apollo_files/merge/beijing_0710.xml"
TEST_MAP_PATH = "data/beijing_0710.xml"


def test_lane_key_point_extracter():
    xml_str = smart_read(TEST_MAP_PATH)
    if xml_str is not None:
        start = time.time()
        apollo_xml = etree.fromstring(xml_str)
        lane_key_point_extracter = LaneKeyPointExtracter()
        lane_key_point_extracter.extract(apollo_xml)
        data = lane_key_point_extracter.get_lane_key_points(
            "13252313Ad99d4_0_-1", 3
        )
        print(data)
        end = time.time()
        data = lane_key_point_extracter.get_lane_key_points(
            "13252313Ad99d4_0_-1", 3
        )
        endend = time.time()
        print("Cost: ", end - start, endend - end)
