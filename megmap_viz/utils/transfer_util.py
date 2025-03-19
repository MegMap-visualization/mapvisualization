# 将WGS84坐标系转换为GCJ02火星坐标系
import math
from decimal import Decimal

import numpy as np
import utm
from pyproj import CRS, Transformer, Proj

pi = math.pi
a = 6378245.0
ee = 0.00669342162296594323


def format_coordinate(coordinate):
    return f"{float(coordinate):.17e}"


def format_float(x):
    return f"{x:.6f}"


class Transfer:
    def __init__(self):
        self.a = 6378245.0
        self.ee = Decimal(0.00669342162296594323)

    def transformLng(self, x, y):
        ret = Decimal()
        ret = (
            300.0
            + x
            + 2.0 * y
            + 0.1 * x * x
            + 0.1 * x * y
            + 0.1 * math.sqrt(math.fabs(x))
        )
        ret += (
            (
                20.0 * math.sin(6.0 * x * math.pi)
                + 20.0 * math.sin(2.0 * x * math.pi)
            )
            * 2.0
            / 3.0
        )
        ret += (
            (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi))
            * 2.0
            / 3.0
        )
        ret += (
            (
                150.0 * math.sin(x / 12.0 * math.pi)
                + 300.0 * math.sin(x / 30.0 * math.pi)
            )
            * 2.0
            / 3.0
        )
        return ret

    def transformLat(self, x, y):
        ret = Decimal()
        ret = (
            -100.0
            + 2.0 * x
            + 3.0 * y
            + 0.2 * y * y
            + 0.1 * x * y
            + 0.2 * math.sqrt(math.fabs(x))
        )
        ret += (
            (
                20.0 * math.sin(6.0 * x * math.pi)
                + 20.0 * math.sin(2.0 * x * math.pi)
            )
            * 2.0
            / 3.0
        )
        ret += (
            (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi))
            * 2.0
            / 3.0
        )
        ret += (
            (
                160.0 * math.sin(y / 12.0 * math.pi)
                + 320 * math.sin(y * math.pi / 30.0)
            )
            * 2.0
            / 3.0
        )
        return ret

    def wgs84_to_gcj02(self, wgs84_lon, wgs84_lat):
        dLat = self.transformLat(wgs84_lon - 105.0, wgs84_lat - 35.0)
        dLng = self.transformLng(wgs84_lon - 105.0, wgs84_lat - 35.0)
        radLat = wgs84_lat / 180.0 * math.pi
        magic = math.sin(radLat)
        magic = 1 - self.ee * Decimal(magic) * Decimal(magic)
        sqrtMagic = math.sqrt(magic)
        dLat = Decimal((dLat * 180.0)) / (
            (Decimal(self.a) * (1 - self.ee))
            / (Decimal(magic) * Decimal(sqrtMagic))
            * Decimal(math.pi)
        )
        dLng = (dLng * 180.0) / (
            self.a / sqrtMagic * math.cos(radLat) * math.pi
        )
        gcj02Lat = wgs84_lat + float(dLat)
        gcj02Lng = wgs84_lon + dLng
        return gcj02Lng, gcj02Lat

    def gcj02_to_wgs84(self, lng, lat):
        """
        GCJ02(火星坐标系)转GPS84
        :param lng:火星坐标系的经度
        :param lat:火星坐标系纬度
        :return: lng, lat
        """
        if self.out_of_china(lng, lat):
            return [lng, lat]
        dlat = self.transformLat(lng - 105.0, lat - 35.0)
        dlng = self.transformLng(lng - 105.0, lat - 35.0)
        radlat = lat / 180.0 * pi
        magic: float = math.sin(radlat)
        magic = 1 - ee * magic * magic
        sqrtmagic = math.sqrt(magic)
        dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
        dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * pi)
        mglat = lat + dlat
        mglng = lng + dlng
        return [lng * 2 - mglng, lat * 2 - mglat]

    def out_of_china(self, lng, lat):
        """
        判断是否在国内，不在国内不做偏移
        :param lng:
        :param lat:
        :return:
        """
        return not (
            lng > 73.66 and lng < 135.05 and lat > 3.86 and lat < 53.55
        )

    def utm_to_wgs84(self, utm_x, utm_y, utm_id=51):
        p = Proj(
            proj="utm",
            zone=utm_id,
            ellps="WGS84",
            south=False,
            north=True,
            errcheck=True,
        )
        wgs84_lon, wgs84_lat = p(utm_x, utm_y, inverse=True)
        return wgs84_lon, wgs84_lat

    def wgs84_to_utm(self, lon, lat):
        utm_x, utm_y, zone_number, zone_letter = utm.from_latlon(lat, lon)
        return utm_x, utm_y, zone_number

    def cgcs2000_to_wgs84(self, CGCS2000_x, CGCS2000_y):
        crs_CGCS2000 = CRS.from_epsg(4490)
        crs_WGS84 = CRS.from_epsg(4326)

        transformer = Transformer.from_crs(crs_CGCS2000, crs_WGS84)
        wgs84_x, wgs84_y = transformer.transform(CGCS2000_x, CGCS2000_y)
        return wgs84_x, wgs84_y

    def wgs84_to_cgcs2000(self, lon, lat):
        # 未测试
        convert_matrix = np.array(
            [
                [0.999997079, 3.47778126e-7, -2.6082455e-7],
                [3.21041821e-8, 1, 2.14655547e-8],
                [2.13904843e-7, -3.436997e-8, 1],
            ]
        )

        wgs84 = np.array([lon, lat, 0.0])
        return (convert_matrix * wgs84).tolist()


coordinate_transfer = Transfer()
