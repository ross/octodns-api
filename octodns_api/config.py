#
#
#

from os import environ

from octodns.yaml import safe_load

_config_cache = {}


def get_config(config_file):
    '''
    Load and cache octoDNS configuration file

    Handles YAML loading and secret resolution (env vars)

    :param config_file: Path to octoDNS configuration file
    :type config_file: str
    :return: Parsed configuration dictionary
    '''
    if config_file not in _config_cache:
        with open(config_file) as fh:
            config = safe_load(fh, enforce_order=False)

        # Resolve environment variable secrets in API keys
        api_config = config.get('api', {})
        keys_config = api_config.get('keys', [])

        for key_config in keys_config:
            key_value = key_config.get('key')
            if key_value and isinstance(key_value, str):
                if key_value.startswith('env/'):
                    # Resolve environment variable (format: env/VAR_NAME)
                    env_var = key_value[4:]  # Remove 'env/' prefix
                    key_config['key'] = environ[env_var]

        _config_cache[config_file] = config

    return _config_cache[config_file]


def clear_config_cache():
    '''Clear the configuration cache (useful for testing)'''
    _config_cache.clear()
