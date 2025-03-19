import os
from pathlib import Path
import sys
import pkgutil
from importlib import import_module
from typing import Dict, Optional
import logging
from logging.config import dictConfig

from flask import Flask, jsonify, request
from flask_cors import CORS
from celery import Celery, Task


# mapvisualization/megmap_viz/__init__.py
BASE_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(BASE_DIR))

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "# Process ID: %(process)d [%(asctime)s] %(levelname)s in %(module)s:%(lineno)d - %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
                "level": "DEBUG",  # 设置为DEBUG级别
            },
            # 删除 file handler
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["wsgi"]  # 只保留 wsgi handler
        },
        "loggers": {
            "megmap_viz": {
                "level": "DEBUG",
                "handlers": ["wsgi"],  # 只保留 wsgi handler
                "propagate": False
            }
        }
    }
)


def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app


def megmap_dataset_init(app: Flask) -> None:
    from megmap_viz.megmap_dataset.megmap_gpkg.gpkg_db import GPKGDB
    from megmap_viz.megmap_dataset.megmap_manager import MegMapManager

    gpkg_db = GPKGDB(app.config["CACHE"]["map_layer_cache_dir"])
    megmap_manager = MegMapManager(gpkg_db)
    app.extensions["megmap_manager"] = megmap_manager
    app.extensions["gpkg_db"] = gpkg_db
    app.config["UPLOAD_FOLDER"] = app.config["CACHE"]["upload_file_cache_dir"]


def register_blueprints(app):
    package_name = "megmap_viz.views"
    package = import_module(package_name)

    with app.app_context():
        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            full_module_name = f"{package_name}.{module_name}"
            module = import_module(full_module_name)
            if hasattr(module, "bp"):
                app.register_blueprint(module.bp)


def create_app(test_config: Optional[Dict] = None) -> Flask:
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # 在应用启动时记录日志
    app.logger.info("Starting application...")

    # load the default configuration
    if app.config["DEBUG"]:
        app.config.from_pyfile("dev_settings.py")
    else:
        app.config.from_pyfile("prod_settings.py")

    logging.basicConfig(level=app.config["LOGGING"]["level"])

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_envvar("MEGMAP_VIZ_CONFIG", silent=True)
        app.config.from_prefixed_env()
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    app.logger.info(f"app config: {app.config}")

    # ensure the cache folder exists
    cache_config = app.config["CACHE"]
    for k, v in cache_config.items():
        if k.endswith("_dir"):
            os.makedirs(v, exist_ok=True)

    app.logger.info("init celery")
    celery_init_app(app)

    app.logger.info("init megmap dataset")
    megmap_dataset_init(app)

    register_blueprints(app)

    CORS(app, supports_credentials=True)

    # 健康检查端点移到根路径
    @app.route('/', methods=['GET'])
    def health_check():
        return jsonify({"message": "This is Megmap!!!"}), 200

    # 添加错误处理
    @app.errorhandler(500)
    def handle_500(error):
        app.logger.error('Server Error: %s', error)
        return jsonify({
            'error': 'Internal Server Error',
            'message': str(error)
        }), 500

    # 添加详细的请求日志
    @app.before_request
    def log_request_info():
        app.logger.info('Request: %s %s', request.method, request.path)
        app.logger.info('Headers: %s', request.headers)
        app.logger.info('Args: %s', request.args)

    @app.after_request
    def log_response_info(response):
        app.logger.info('Response Status: %s', response.status)
        if response.status_code >= 400:
            app.logger.error('Response Data: %s', response.get_data())
        return response


    return app
