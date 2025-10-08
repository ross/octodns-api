#
#
#

from tempfile import NamedTemporaryFile
from unittest import TestCase
from unittest.mock import patch

from flask import Flask

from octodns_api.auth import _get_api_keys, require_api_key


class TestAuth(TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['OCTODNS_CONFIG_FILE'] = '/tmp/test-config.yaml'

        @self.app.route('/test')
        @require_api_key
        def test_endpoint():
            return {'success': True}

        self.client = self.app.test_client()

    @patch('octodns_api.auth._get_api_keys')
    def test_missing_authorization_header(self, mock_get_keys):
        mock_get_keys.return_value = ['test-key-123']

        response = self.client.get('/test')
        self.assertEqual(response.status_code, 401)
        self.assertIn(
            'Missing Authorization header', response.get_json()['error']
        )

    @patch('octodns_api.auth._get_api_keys')
    def test_invalid_authorization_format(self, mock_get_keys):
        mock_get_keys.return_value = ['test-key-123']

        response = self.client.get(
            '/test', headers={'Authorization': 'InvalidFormat'}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn(
            'Invalid Authorization header format', response.get_json()['error']
        )

    @patch('octodns_api.auth._get_api_keys')
    def test_invalid_api_key(self, mock_get_keys):
        mock_get_keys.return_value = ['valid-key-123']

        response = self.client.get(
            '/test', headers={'Authorization': 'Bearer invalid-key'}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn('Invalid API key', response.get_json()['error'])

    @patch('octodns_api.auth._get_api_keys')
    def test_valid_api_key(self, mock_get_keys):
        mock_get_keys.return_value = ['valid-key-123']

        response = self.client.get(
            '/test', headers={'Authorization': 'Bearer valid-key-123'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'success': True})

    def test_get_api_keys_with_missing_key_value(self):
        # Test coverage for when a key config has no 'key' field
        from octodns_api.app import create_app

        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(
                '''
api:
  keys:
    - name: test1
      key: valid-key
    - name: test2
      # No 'key' field here

providers:
  config:
    class: octodns.provider.yaml.YamlProvider
    directory: /tmp

zones:
  example.com.:
    sources:
      - config
'''
            )
            config_file = f.name

        test_app = create_app(config_file)
        with test_app.app_context():
            keys = _get_api_keys()
            # Should only include the valid key, skip the one without 'key' field
            self.assertEqual(keys, ['valid-key'])
