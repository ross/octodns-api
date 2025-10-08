#
#
#

from functools import wraps

from flask import current_app, jsonify, request


class AuthenticationError(Exception):
    pass


def _get_api_keys():
    '''Get the configured API keys from the octoDNS config'''
    from .config import get_config

    config = get_config(current_app.config['OCTODNS_CONFIG_FILE'])
    api_config = config.get('api', {})
    keys_config = api_config.get('keys', [])

    # Extract the actual key values, resolving env vars if needed
    keys = []
    for key_config in keys_config:
        key_value = key_config.get('key')
        if key_value:
            keys.append(key_value)

    return keys


def require_api_key(f):
    '''
    Decorator to require valid API key authentication

    Expects Authorization header with format: Bearer <api-key>
    '''

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return (jsonify({'error': 'Missing Authorization header'}), 401)

        # Parse Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return (
                jsonify(
                    {
                        'error': 'Invalid Authorization header format. Expected: Bearer <api-key>'
                    }
                ),
                401,
            )

        provided_key = parts[1]

        # Validate against configured keys
        valid_keys = _get_api_keys()
        if provided_key not in valid_keys:
            return jsonify({'error': 'Invalid API key'}), 401

        return f(*args, **kwargs)

    return decorated_function
