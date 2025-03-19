import json
from pathlib import Path

import pytest


from megmap_viz.megmap_dataset.megmap_memo.memo_data_parser import MemoDataDict


@pytest.fixture
def test_memo_data() -> MemoDataDict:
    test_path = str(Path(__file__).parent / "data/zjf_test.json")

    with open(test_path) as f:
        memo_data: MemoDataDict = json.load(f)

    return memo_data
