#
#
#

from logging import getLogger

from flask import Flask
from flask_cors import CORS

from .api.records import records_bp
from .api.zones import zones_bp
from .manager import ApiManager


def create_app(config_file):
    '''
    Flask application factory

    :param config_file: Path to octoDNS configuration file
    :type config_file: str
    :return: Flask application instance
    '''
    app = Flask(__name__)
    # Don't merge consecutive slashes - needed for apex records with empty names
    app.url_map.merge_slashes = False
    CORS(app)

    # Configure Flask to use named logger so errors are logged
    app.logger = getLogger('App')

    # Create and store ApiManager instance for reuse across requests
    app.manager = ApiManager(config_file)

    # Register blueprints
    app.register_blueprint(zones_bp)
    app.register_blueprint(records_bp)

    return app
