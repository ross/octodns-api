#
#
#

from logging import getLogger

from flask import Blueprint, current_app, jsonify, request

from octodns.idna import idna_decode

from ..auth import require_api_key
from ..manager import ApiManagerException

zones_bp = Blueprint('zones', __name__, url_prefix='/zones')

log = getLogger('api.Zones')


@zones_bp.route('', methods=['GET'])
@require_api_key
def list_zones():
    '''List all configured zones'''
    try:
        zones = current_app.manager.list_zones()
        zones = sorted(idna_decode(z) for z in zones)
        log.debug('list_zones: zones=%s', zones)
        return jsonify({'zones': zones})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@zones_bp.route('/<zone_name>', methods=['GET'])
@require_api_key
def get_zone(zone_name):
    '''Get a zone with all its records'''
    try:
        zone = current_app.manager.get_zone(zone_name)
        return jsonify({'name': zone.decoded_name})
    except ApiManagerException as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@zones_bp.route('/<zone_name>/sync', methods=['POST'])
@require_api_key
def sync_zone(zone_name):
    '''Sync a zone from sources to targets'''
    try:
        data = request.get_json() or {}
        dry_run = data.get('dry_run', True)

        result = current_app.manager.sync_zone(zone_name, dry_run=dry_run)

        return jsonify(result)
    except ApiManagerException as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
