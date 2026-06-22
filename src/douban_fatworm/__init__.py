from __future__ import annotations

from flask import Flask

from .config import Config
from .database import init_db
from .routes import bp


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    config_object.ensure_directories()
    init_db(app.config["DATABASE"])
    app.register_blueprint(bp)

    @app.after_request
    def set_utf8_headers(response):
        if response.mimetype.startswith("text/"):
            response.headers["Content-Type"] = f"{response.mimetype}; charset=utf-8"
        return response

    return app
