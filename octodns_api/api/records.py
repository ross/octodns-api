#
#
#

from collections import defaultdict
from logging import getLogger

from flask import Blueprint, current_app, jsonify, request

from octodns.idna import idna_decode

from ..auth import require_api_key
from ..manager import ApiManagerException

records_bp = Blueprint('records', __name__, url_prefix='/zones')

log = getLogger('api.Records')


@records_bp.route('/<zone_name>/records', methods=['GET'])
@require_api_key
def list_records(zone_name):
    '''List all records in a zone'''
    try:
        log.debug('list_records: zone_name=%s', zone_name)
        zone_name = idna_decode(zone_name)
        zone = current_app.manager.get_zone(zone_name)
        log.debug('list_records:   zone_name=%s, zone=%s', zone_name, zone)

        records = defaultdict(dict)
        for record in zone.records:
            records[record.decoded_name][record._type] = record.data

        return jsonify({'zone': zone.decoded_name, 'records': records})
    except ApiManagerException as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@records_bp.route(
    '/<zone_name>/records/<record_name>/<record_type>', methods=['GET']
)
@records_bp.route('/<zone_name>/records//<record_type>', methods=['GET'])
@require_api_key
def get_record(zone_name, record_type, record_name=''):
    '''Get a specific record'''
    try:
        log.debug(
            'get_record: zone_name=%s, record_name=%s, record_type=%s',
            zone_name,
            record_name,
            record_type,
        )
        zone_name = idna_decode(zone_name)
        record_name = idna_decode(record_name)
        record = current_app.manager.get_record(
            zone_name, record_name, record_type
        )
        log.debug(
            'get_record:   zone_name=%s, record_name=%s, record=%s',
            zone_name,
            record_name,
            record,
        )

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
        data['name'] = record.decoded_name
        data['type'] = record._type

        return jsonify(data)
    except ApiManagerException as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@records_bp.route(
    '/<zone_name>/records/<record_name>/<record_type>', methods=['POST']
)
@records_bp.route('/<zone_name>/records//<record_type>', methods=['POST'])
@require_api_key
def create_or_update_record(zone_name, record_type, record_name=''):
    '''Create or update a record'''
    try:
        log.debug(
            'create_or_update_record: zone_name=%s, record_name=%s, record_type=%s',
            zone_name,
            record_name,
            record_type,
        )
        zone_name = idna_decode(zone_name)
        record_name = idna_decode(record_name)
        record_data = request.get_json()

        if not record_data:
            return jsonify({'error': 'No record data provided'}), 400

        record, changed = current_app.manager.create_or_update_record(
            zone_name, record_name, record_type, record_data
        )
        log.debug(
            'create_or_update_record:   zone_name=%s, record_name=%s, record=%s, changed=%s',
            zone_name,
            record_name,
            record,
            changed,
        )

        # Get full record data including name and type
        data = record.data
        data['name'] = record_name
        data['type'] = record_type

        return (jsonify(data), 201 if changed else 200)
    except ApiManagerException as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@records_bp.route(
    '/<zone_name>/records/<record_name>/<record_type>', methods=['DELETE']
)
@records_bp.route('/<zone_name>/records//<record_type>', methods=['DELETE'])
@require_api_key
def delete_record(zone_name, record_type, record_name=''):
    '''Delete a record'''
    try:
        log.debug(
            'delete_record: zone_name=%s, record_name=%s, record_type=%s',
            zone_name,
            record_name,
            record_type,
        )
        zone_name = idna_decode(zone_name)
        record_name = idna_decode(record_name)

        deleted = current_app.manager.delete_record(
            zone_name, record_name, record_type
        )
        log.debug(
            'delete_record:   zone_name=%s, record_name=%s, deleted=%s',
            zone_name,
            record_name,
            deleted,
        )

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
