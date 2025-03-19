import typing as t

import utm

import numpy as np
from numpy import typing as npt

try:
    import numpy as mathlib
except ImportError:
    import math as mathlib


class GCJ02:
    a = 6378245.0
    ee = 0.00669342162296594323

    @t.overload
    def __transform_lat(self, x: float, y: float) -> float:
        ...

    @t.overload
    def __transform_lat(
        self, x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
    ) -> npt.NDArray[np.float64]:
        ...

    def __transform_lat(self, x, y):
        ret = (
            -100.0
            + 2.0 * x
            + 3.0 * y
            + 0.2 * y * y
            + 0.1 * x * y
            + 0.2 * mathlib.sqrt(mathlib.abs(x))
        )
        ret += (
            (
                20.0 * mathlib.sin(6.0 * x * mathlib.pi)
                + 20.0 * mathlib.sin(2.0 * x * mathlib.pi)
            )
            * 2.0
            / 3.0
        )
        ret += (
            (
                20.0 * mathlib.sin(y * mathlib.pi)
                + 40.0 * mathlib.sin(y / 3.0 * mathlib.pi)
            )
            * 2.0
            / 3.0
        )
        ret += (
            (
                160.0 * mathlib.sin(y / 12.0 * mathlib.pi)
                + 320 * mathlib.sin(y * mathlib.pi / 30.0)
            )
            * 2.0
            / 3.0
        )
        return ret

    @t.overload
    def __transform_lon(self, x: float, y: float) -> float:
        ...

    @t.overload
    def __transform_lon(
        self, x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
    ) -> npt.NDArray[np.float64]:
        ...

    def __transform_lon(self, x, y):
        ret = (
            300.0
            + x
            + 2.0 * y
            + 0.1 * x * x
            + 0.1 * x * y
            + 0.1 * mathlib.sqrt(mathlib.abs(x))
        )
        ret += (
            (
                20.0 * mathlib.sin(6.0 * x * mathlib.pi)
                + 20.0 * mathlib.sin(2.0 * x * mathlib.pi)
            )
            * 2.0
            / 3.0
        )
        ret += (
            (
                20.0 * mathlib.sin(x * mathlib.pi)
                + 40.0 * mathlib.sin(x / 3.0 * mathlib.pi)
            )
            * 2.0
            / 3.0
        )
        ret += (
            (
                150.0 * mathlib.sin(x / 12.0 * mathlib.pi)
                + 300.0 * mathlib.sin(x / 30.0 * mathlib.pi)
            )
            * 2.0
            / 3.0
        )
        return ret

    @t.overload
    def __calc_offset(self, lon: float, lat: float) -> t.Tuple[float, float]:
        ...

    @t.overload
    def __calc_offset(
        self, lon: npt.NDArray[np.float64], lat: npt.NDArray[np.float64]
    ) -> t.Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        ...

    def __calc_offset(self, lon, lat):
        dlat = self.__transform_lat(lon - 105.0, lat - 35.0)
        dlon = self.__transform_lon(lon - 105.0, lat - 35.0)
        radlat = lat / 180.0 * mathlib.pi
        magic = mathlib.sin(radlat)
        magic = 1 - self.ee * magic * magic
        sqrtmagic = mathlib.sqrt(magic)
        dlat = (dlat * 180.0) / (
            (self.a * (1 - self.ee)) / (magic * sqrtmagic) * mathlib.pi
        )
        dlon = (dlon * 180.0) / (
            self.a / sqrtmagic * mathlib.cos(radlat) * mathlib.pi
        )
        return dlon, dlat

    @t.overload
    def _to_wgs84(
        self, gcj_lon: float, gcj_lat: float
    ) -> t.Tuple[float, float]:
        ...

    @t.overload
    def _to_wgs84(
        self,
        gcj_lon: npt.NDArray[np.float64],
        gcj_lat: npt.NDArray[np.float64],
    ) -> t.Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        ...

    def _to_wgs84(self, gcj_lon, gcj_lat):
        dlon, dlat = self.__calc_offset(gcj_lon, gcj_lat)
        wgs_lat = gcj_lat - dlat
        wgs_lon = gcj_lon - dlon
        return wgs_lon, wgs_lat

    @t.overload
    def _from_wgs84(
        self, wgs_lon: float, wgs_lat: float
    ) -> t.Tuple[float, float]:
        ...

    @t.overload
    def _from_wgs84(
        self,
        wgs_lon: npt.NDArray[np.float64],
        wgs_lat: npt.NDArray[np.float64],
    ) -> t.Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        ...

    def _from_wgs84(self, wgs_lon, wgs_lat):
        dlon, dlat = self.__calc_offset(wgs_lon, wgs_lat)
        gcj_lat = wgs_lat + dlat
        gcj_lon = wgs_lon + dlon
        return gcj_lon, gcj_lat

    @t.overload
    @classmethod
    def to_wgs84(cls, gcj_lon: float, gcj_lat: float) -> t.Tuple[float, float]:
        ...

    @t.overload
    @classmethod
    def to_wgs84(
        cls, gcj_lon: npt.NDArray[np.float64], gcj_lat: npt.NDArray[np.float64]
    ) -> t.Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        ...

    @classmethod
    def to_wgs84(cls, gcj_lon, gcj_lat):
        return cls()._to_wgs84(gcj_lon, gcj_lat)

    @t.overload
    @classmethod
    def from_wgs84(
        cls, wgs_lon: float, wgs_lat: float
    ) -> t.Tuple[float, float]:
        ...

    @t.overload
    @classmethod
    def from_wgs84(
        cls, wgs_lon: npt.NDArray[np.float64], wgs_lat: npt.NDArray[np.float64]
    ) -> t.Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        ...

    @classmethod
    def from_wgs84(cls, wgs_lon, wgs_lat):
        return cls()._from_wgs84(wgs_lon, wgs_lat)


class WGS84:
    @t.overload
    @staticmethod
    def to_utm(lon: float, lat: float) -> t.Tuple[float, float, int, str]:
        ...

    @t.overload
    @staticmethod
    def to_utm(
        lon: npt.NDArray[np.float64], lat: npt.NDArray[np.float64]
    ) -> t.Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], int, str]:
        ...

    @staticmethod
    def to_utm(lon, lat):
        return utm.from_latlon(lat, lon)

    @t.overload
    @staticmethod
    def from_utm(
        easting: float, northing: float, zone_number: int, zone_letter: str
    ) -> t.Tuple[float, float]:
        ...

    @t.overload
    @staticmethod
    def from_utm(
        easting: float, northing: float, zone_number: int, *, northern: bool
    ) -> t.Tuple[float, float]:
        ...

    @t.overload
    @staticmethod
    def from_utm(
        easting: npt.NDArray[np.float64],
        northing: npt.NDArray[np.float64],
        zone_number: int,
        *,
        northern: bool
    ) -> t.Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        ...

    @t.overload
    @staticmethod
    def from_utm(
        easting: npt.NDArray[np.float64],
        northing: npt.NDArray[np.float64],
        zone_number: int,
        zone_letter: str,
    ) -> t.Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        ...

    @staticmethod
    def from_utm(
        easting, northing, zone_number, zone_letter=None, *, northern=None
    ):
        return utm.to_latlon(
            easting, northing, zone_number, zone_letter, northern
        )[::-1]


def wgs84_to_gcj02(
    wgs84_points: t.List[t.Tuple[float, float]]
) -> t.List[t.Tuple[float, float]]:
    points_array = np.array(wgs84_points)
    gcj02_lon, gcj02_lat = GCJ02.from_wgs84(
        wgs_lon=points_array[:, 0], wgs_lat=points_array[:, 1]
    )
    return list(zip(gcj02_lon.tolist(), gcj02_lat.tolist()))
