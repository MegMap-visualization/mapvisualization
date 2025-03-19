from megmap_viz.megmap_dataset.megmap_memo.memo_data_parser import (
    MemoParser,
    MemoDataDict,
)


def test_memo_parser(test_memo_data: MemoDataDict) -> None:
    memo_parser = MemoParser(test_memo_data)
    rv = memo_parser.run()
