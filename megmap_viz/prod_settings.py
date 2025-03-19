
# celery config
CELERY = {
    "broker_url": "redis://localhost:6379/0",
    "result_backend": "redis://localhost:6379/1",
    "beat_schedule": {
        "remove-old-map-data": {
            "task": "megmap_viz.tasks.remove_old_maps.remove_old_map_data",
            "schedule": 60,
            "args": (),
        },
    },
}


# cache config
cache_dir = "/data/megmap_viz_cache"
CACHE = {
    "cache_dir": cache_dir,
    "map_file_cache_dir": f"{cache_dir}/megmap_files",
    "map_layer_cache_dir": f"{cache_dir}/map_layer_datum",
    "upload_file_cache_dir": f"{cache_dir}/upload_files",
    "mem_buffer_size": 10,
    "wanlixing_vis_data_cache_dir": f"{cache_dir}/wanlixing_vis_data",
    "wanlixing_s3_path": "s3://broadside-map/wanlixing/last_result/",
}

LOCAL_MAP_NAME = "localmap4e1a43c90ee15a7aec66454e96b9e899_20240101_v99"

# logging config
LOGGING = {
    "level": "DEBUG",
}