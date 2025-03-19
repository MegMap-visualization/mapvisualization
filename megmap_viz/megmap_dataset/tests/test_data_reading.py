from lxml import etree
import time

from megmap_viz.megmap_dataset.megmap_apollo.apollo_parser import (
    MultiApolloParser,
)
from megmap_viz.utils.file_op import load_xml


def test_local_apollo_parser(test_apollo_xml_local_path: str):
    start = time.time()
    apollo_xml = etree.parse(test_apollo_xml_local_path).getroot()
    apollo_parser = MultiApolloParser(apollo_xml)
    rv = apollo_parser.run()
    assert rv is not None
    end = time.time()
    assert end - start < 60 * 3


def test_s3_apollo_parser(test_apollo_xml_s3_path: str):
    start = time.time()
    apollo_xml_dat = load_xml(test_apollo_xml_s3_path)
    assert apollo_xml_dat is not None
    apollo_xml, _ = apollo_xml_dat
    apollo_parser = MultiApolloParser(apollo_xml)
    rv = apollo_parser.run()
    assert rv is not None
    end = time.time()
    assert end - start < 60 * 3
