from . import create_app
from megmap_viz.tasks.remove_old_maps import remove_old_map_data


flask_app = create_app()
celery_app = flask_app.extensions["celery"]
