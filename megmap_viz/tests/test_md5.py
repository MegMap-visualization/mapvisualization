from pathlib import Path
import os


from utils.md5 import get_str_md5
from utils.file_op import smart_read


def test_md5():
    test_path = Path("data/beijing_0710.xml")
    xml_str = smart_read(test_path.absolute().as_posix())

    print(get_str_md5(xml_str))
    print(os.system(f"md5sum {test_path.absolute()}"))
