import numpy as np

from megmap_viz.utils.coord_converter import GCJ02


def test_gcj02():
    test_gcj02 = [
        [116.31791864066153, 39.990131832635086],
        [116.31707278719804, 39.988448523740914],
        [116.31663497624304, 39.98694542408507],
        [116.31862570202405, 39.984746699703045],
        [116.32310030875952, 39.985552061710685],
        [116.32387042095648, 39.986446543568306],
        [116.32455568510046, 39.98768617491347],
        [116.32168694842585, 39.99042057850435],
        [116.31958872638083, 39.99080259803358],
        [116.31819689758048, 39.99097026377063],
    ]

    test_gcj02_array = np.array(test_gcj02)
    test_wgs84_lon_array, test_wgs84_lat_array = GCJ02.to_wgs84(
        test_gcj02_array[:, 0], test_gcj02_array[:, 1]
    )
    test_wgs84 = np.stack([test_wgs84_lon_array, test_wgs84_lat_array], axis=1)

    for lon, lat in test_gcj02:
        a = GCJ02.to_wgs84(lon, lat)
        print(a)
