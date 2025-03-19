import datetime

from megmap_viz.tasks.remove_old_maps import RemarkInfo


def test_remark_info():
    test_case = [
        RemarkInfo(is_true=False, remark="test"),
        RemarkInfo(
            is_true=True,
            name="test1",
            remark="test1_20230903_v1",
            date=datetime.date(2023, 9, 3),
            version=1,
        ),
        RemarkInfo(is_true=False, remark="test0"),
        RemarkInfo(
            is_true=True,
            name="test2",
            remark="test2_20230903_v2",
            date=datetime.date(2023, 9, 3),
            version=2,
        ),
        RemarkInfo(
            is_true=True,
            name="test2",
            remark="test2_20230903_v1",
            date=datetime.date(2023, 9, 3),
            version=1,
        ),
        RemarkInfo(is_true=False, remark="test"),
        RemarkInfo(
            is_true=True,
            name="test2",
            remark="test2_20230903_v3",
            date=datetime.date(2023, 9, 3),
            version=3,
        ),
        RemarkInfo(
            is_true=True,
            name="test2",
            remark="test2_20230902_v1",
            date=datetime.date(2023, 9, 2),
            version=1,
        ),
        RemarkInfo(
            is_true=True,
            name="test1",
            remark="test1_20230903_v4",
            date=datetime.date(2023, 9, 3),
            version=4,
        ),
        RemarkInfo(is_true=False, remark="test"),
    ]

    target = [
        RemarkInfo(is_true=False, remark="test0"),
        RemarkInfo(is_true=False, remark="test"),
        RemarkInfo(is_true=False, remark="test"),
        RemarkInfo(is_true=False, remark="test"),
        RemarkInfo(
            is_true=True,
            name="test2",
            remark="test2_20230902_v1",
            date=datetime.date(2023, 9, 2),
            version=1,
        ),
        RemarkInfo(
            is_true=True,
            name="test1",
            remark="test1_20230903_v1",
            date=datetime.date(2023, 9, 3),
            version=1,
        ),
        RemarkInfo(
            is_true=True,
            name="test2",
            remark="test2_20230903_v1",
            date=datetime.date(2023, 9, 3),
            version=1,
        ),
        RemarkInfo(
            is_true=True,
            name="test2",
            remark="test2_20230903_v2",
            date=datetime.date(2023, 9, 3),
            version=2,
        ),
        RemarkInfo(
            is_true=True,
            name="test2",
            remark="test2_20230903_v3",
            date=datetime.date(2023, 9, 3),
            version=3,
        ),
        RemarkInfo(
            is_true=True,
            name="test1",
            remark="test1_20230903_v4",
            date=datetime.date(2023, 9, 3),
            version=4,
        ),
    ]

    assert sorted(test_case) == target
    assert sorted(test_case, reverse=True) == list(reversed(target))
