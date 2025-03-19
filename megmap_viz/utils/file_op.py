from typing import IO, Dict, Union, Optional, Tuple, Callable
import json

from lxml import etree
import refile
import megfile
from megfile import SmartPath

from .md5 import get_str_md5


SourceType = Union[str, IO]
SourcesType = Union[Dict[str, SourceType], Dict[str, str]]


def smart_read(source: SourceType) -> Union[None, str, bytes, bytearray]:
    """smartly read map file, suprort local file, s3 file, and file-like object
    Args:
        source (SourceType): map file path or file-like object

    Returns:
        Union[None, str, bytes, bytearray]: map str data
    """
    str_data = None

    if isinstance(source, str):
        file_path = SmartPath(source)
        if refile.smart_exists(file_path):
            file = refile.smart_open(SmartPath(source), mode="rb")
            str_data = file.read()
            file.close()

    elif hasattr(source, "read"):
        str_data = source.read()  # type: ignore

    return str_data


def load_xml(xml_path: str) -> Optional[Tuple[etree._Element, str]]:
    xml_str = smart_read(xml_path)

    if xml_str is None:
        return

    return etree.fromstring(xml_str), get_str_md5(xml_str)


def load_json(json_path: str) -> Optional[Tuple[Dict, str]]:
    json_str = smart_read(json_path)

    if json_str is None:
        return

    return json.loads(json_str), get_str_md5(json_str)


def get_file_size(s3_path: str) -> int:
    file_path = SmartPath(s3_path)
    return megfile.s3_stat(file_path).size


def has_file(s3_path: str) -> bool:
    file_path = SmartPath(s3_path)
    return megfile.s3_exists(file_path)


def download_from_oss(
    s3_path: str,
    file_path: str,
    callback: Optional[Callable[[int], None]] = None,
) -> None:
    megfile.s3_download(
        SmartPath(s3_path), SmartPath(file_path), callback=callback
    )


def upload_to_oss(file_path: str, s3_path: str) -> None:
    megfile.s3_upload(SmartPath(file_path), SmartPath(s3_path))
