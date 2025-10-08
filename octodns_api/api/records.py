#
#
#

from flask import Blueprint, current_app, jsonify, request

from ..auth import require_api_key
from ..manager import ApiManager, ApiManagerException

records_bp = Blueprint('records', __name__, url_prefix='/zones')


@records_bp.route('/<zone_name>/records', methods=['GET'])
@require_api_key
def list_records(zone_name):
    '''List all records in a zone'''
    try:
        manager = ApiManager(current_app.config['OCTODNS_CONFIG_FILE'])
        zone = manager.get_zone(zone_name)

        records = [record.data for record in zone.records]

        return jsonify({'zone': zone.name, 'records': records})
    except ApiManagerException as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@records_bp.route(
    '/<zone_name>/records/<record_name>/<record_type>', methods=['GET']
)
@require_api_key
def get_record(zone_name, record_name, record_type):
    '''Get a specific record'''
    try:
        manager = ApiManager(current_app.config['OCTODNS_CONFIG_FILE'])
        record = manager.get_record(zone_name, record_name, record_type)

        if not record:
            return (
                jsonify(
                    {
                        'error': f'Record {record_name} ({record_type}) not found in zone {zone_name}'
                    }
                ),
                404,
            )

        # Get full record data including name and type
        data = record.data
        data['name'] = record.name
        data['type'] = record._type

        return jsonify(data)
    except ApiManagerException as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@records_bp.route('/<zone_name>/records', methods=['POST'])
@require_api_key
def create_or_update_record(zone_name):
    '''Create or update a record'''
    try:
        record_data = request.get_json()

        if not record_data:
            return jsonify({'error': 'No record data provided'}), 400

        manager = ApiManager(current_app.config['OCTODNS_CONFIG_FILE'])
        record, changed = manager.create_or_update_record(
            zone_name, record_data
        )

        # Get full record data including name and type
        data = record.data
        data['name'] = record.name
        data['type'] = record._type

        return (
            jsonify({'record': data, 'changed': changed}),
            201 if changed else 200,
        )
    except ApiManagerException as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@records_bp.route(
    '/<zone_name>/records/<record_name>/<record_type>', methods=['DELETE']
)
@require_api_key
def delete_record(zone_name, record_name, record_type):
    '''Delete a record'''
    try:
        manager = ApiManager(current_app.config['OCTODNS_CONFIG_FILE'])
        deleted = manager.delete_record(zone_name, record_name, record_type)

        if not deleted:
            return (
                jsonify(
                    {
                        'error': f'Record {record_name} ({record_type}) not found in zone {zone_name}'
                    }
                ),
                404,
            )

        return jsonify({'deleted': True}), 200
    except ApiManagerException as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
