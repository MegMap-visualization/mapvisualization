from flask import Blueprint, request

from megmap_viz.utils.transfer_util import Transfer

bp = Blueprint("ct_old", __name__, url_prefix="/coordinate-transformation")

transfer = Transfer()


@bp.route("/wgs2utm")
def wgs2utm():
    lon = request.args.get("lon")
    lat = request.args.get("lat")
    utm_x, utm_y, utm_id = transfer.wgs84_to_utm(float(lon), float(lat))
    return str(utm_x) + "," + str(utm_y) + "," + str(utm_id)


@bp.route("/utm2wgs")
def utm2wgs():
    x = request.args.get("x")
    y = request.args.get("y")
    utm_id = request.args.get("utm_id")
    wgs84_lon, wgs84_lat = transfer.utm_to_wgs84(x, y, utm_id)
    return str(wgs84_lon) + "," + str(wgs84_lat)
