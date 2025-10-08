#
#
#

from flask import Flask
from flask_cors import CORS


def create_app(config_file):
    '''
    Flask application factory

    :param config_file: Path to octoDNS configuration file
    :type config_file: str
    :return: Flask application instance
    '''
    app = Flask(__name__)
    CORS(app)

    # Store config file path in app config
    app.config['OCTODNS_CONFIG_FILE'] = config_file

    # Register blueprints
    from .api.records import records_bp
    from .api.zones import zones_bp

    app.register_blueprint(zones_bp)
    app.register_blueprint(records_bp)

    return app
