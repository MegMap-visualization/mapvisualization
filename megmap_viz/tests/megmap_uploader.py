import typing as t

import click
import requests


MEGMAP_TYPE = t.Literal["apollo", "memo"]

MEGMAP_BUILDER_API = "http://megmap-v2.chenjunjie.megvii-transformer.svc:5000"


def upload_megmap(
    megmap_s3_path: str, map_type: MEGMAP_TYPE, remark: t.Optional[str] = None
) -> t.Optional[str]:
    req_json = {
        "map_path": megmap_s3_path,
        "map_type": map_type,
    }

    if remark is not None:
        req_json["remark"] = remark

    rv = requests.put(
        f"{MEGMAP_BUILDER_API}/megmap-layer-builder/builder-task",
        json=req_json,
    )

    if rv.status_code != 200:
        return None

    data = rv.json()
    if data["status"] != "success":
        return None

    return data["data"]["task_id"]


def delete_megmap(remark: str, md5: str) -> bool:
    rv = requests.delete(
        f"{MEGMAP_BUILDER_API}/megmap-dataset/{remark}/{md5}",
    )

    if rv.status_code != 200:
        return False

    data = rv.json()
    if data["status"] != "success":
        return False

    return True


@click.group()
def cli() -> None:
    pass


@cli.command("delete")
@click.option("--remark", required=True, type=str)
@click.option("--md5", required=True, type=str)
def delete(remark: str, md5: str) -> None:
    if delete_megmap(remark, md5):
        print("delete success")
    else:
        print("delete failed")


@cli.command("upload")
@click.option("--map-path", required=True, type=str)
@click.option(
    "--map-type", required=True, type=click.Choice(["apollo", "memo"])
)
@click.option("--remark", required=False, type=str)
def upload(
    map_path: str, map_type: MEGMAP_TYPE, remark: t.Optional[str] = None
) -> None:
    task_id = upload_megmap(map_path, map_type, remark)
    if task_id is None:
        print("upload failed")
        return

    print(f"upload success, task_id: {task_id}")


if __name__ == "__main__":
    cli()
