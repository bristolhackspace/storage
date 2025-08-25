import logging
import os
import sys
import tomllib

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SITE_NAME="Example Site",
        SECRET_KEY="dev",
        SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://postgres:postgres@localhost:5432/hackspace_storage",
        LOGIN_START_SECRET="dev",
        PORTAL_URL="https://example.com"
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_file("config.toml", load=tomllib.load, text=False, silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    register_extensions(app)
    register_blueprints(app)
    configure_logger(app)

    return app


def register_extensions(app: Flask):
    from .extensions import db, migrate
    from . import login
    db.init_app(app)
    migrate.init_app(app)
    login.init_app(app)


def register_blueprints(app: Flask):
    from hackspace_storage import main
    app.register_blueprint(main.views.bp)

    # This provides no pages, but some CLI commands
    from hackspace_storage import demo_data
    app.register_blueprint(demo_data.bp)

def configure_logger(app):
    """Configure loggers."""
    handler = logging.StreamHandler(sys.stdout)
    if not app.logger.handlers:
        app.logger.addHandler(handler)