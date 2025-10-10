#
#
#

from os import makedirs
from os.path import join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase
from unittest.mock import MagicMock, patch

from octodns_api.app import create_app
from octodns_api.manager import ApiManagerException


class TestApi(TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()
        self.config_dir = join(self.tmpdir, 'config')
        makedirs(self.config_dir)

        # Create a test zone file
        zone_file = join(self.config_dir, 'example.com.yaml')
        with open(zone_file, 'w') as f:
            f.write(
                '''
---
'':
  ttl: 300
  type: A
  values:
    - 1.2.3.4
www:
  ttl: 300
  type: A
  values:
    - 5.6.7.8
'''
            )

        # Create test config file
        self.config_file = join(self.tmpdir, 'config.yaml')
        with open(self.config_file, 'w') as f:
            f.write(
                f'''
api:
  keys:
    - name: test
      key: test-key-123

providers:
  config:
    class: octodns.provider.yaml.YamlProvider
    directory: {self.config_dir}

zones:
  example.com.:
    sources:
      - config
    targets:
      - config
'''
            )

        self.app = create_app(self.config_file)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        self.headers = {'Authorization': 'Bearer test-key-123'}

    def tearDown(self):
        rmtree(self.tmpdir)

    def test_list_zones(self):
        response = self.client.get('/zones', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('zones', data)
        self.assertIn('example.com.', data['zones'])

    def test_get_zone(self):
        response = self.client.get('/zones/example.com.', headers=self.headers)
        if response.status_code != 200:
            print(f"Error: {response.get_json()}")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], 'example.com.')

    def test_get_zone_not_found(self):
        response = self.client.get('/zones/notfound.com.', headers=self.headers)
        self.assertEqual(response.status_code, 404)

    def test_list_records(self):
        response = self.client.get(
            '/zones/example.com./records', headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['zone'], 'example.com.')
        self.assertEqual(len(data['records']), 2)

    def test_get_record(self):
        response = self.client.get(
            '/zones/example.com./records/www/A', headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        # Print to debug
        if 'type' not in data:
            print(f"Response data: {data}")
        self.assertEqual(data['type'], 'A')
        self.assertEqual(data['name'], 'www')

    def test_get_record_not_found(self):
        response = self.client.get(
            '/zones/example.com./records/notfound/A', headers=self.headers
        )
        self.assertEqual(response.status_code, 404)

    def test_get_apex_record(self):
        # Test getting apex record (empty string name) using double slash
        response = self.client.get(
            '/zones/example.com./records//A', headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['type'], 'A')
        self.assertEqual(data['name'], '')

    def test_create_record(self):
        record_data = {'ttl': 600, 'values': ['9.9.9.9']}
        response = self.client.post(
            '/zones/example.com./records/test/A',
            json=record_data,
            headers=self.headers,
        )
        self.assertIn(response.status_code, [200, 201])
        data = response.get_json()
        self.assertIn('record', data)
        self.assertEqual(data['record']['name'], 'test')
        self.assertEqual(data['record']['type'], 'A')

    def test_create_record_no_data(self):
        # Test with empty/null JSON to ensure get_json() returns None
        response = self.client.post(
            '/zones/example.com./records/test/A',
            headers=self.headers,
            data='null',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('No record data provided', data['error'])

    def test_delete_record(self):
        response = self.client.delete(
            '/zones/example.com./records/www/A', headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['deleted'])

    def test_delete_record_not_found(self):
        response = self.client.delete(
            '/zones/example.com./records/notfound/A', headers=self.headers
        )
        self.assertEqual(response.status_code, 404)

    def test_create_apex_record(self):
        # Test creating apex record (empty string name) using double slash
        record_data = {'ttl': 600, 'values': ['8.8.8.8']}
        response = self.client.post(
            '/zones/example.com./records//A',
            json=record_data,
            headers=self.headers,
        )
        self.assertIn(response.status_code, [200, 201])
        data = response.get_json()
        self.assertIn('record', data)
        self.assertEqual(data['record']['name'], '')
        self.assertEqual(data['record']['type'], 'A')

    def test_delete_apex_record(self):
        # Test deleting apex record (empty string name) using double slash
        response = self.client.delete(
            '/zones/example.com./records//A', headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['deleted'])

    def test_sync_zone(self):
        response = self.client.post(
            '/zones/example.com./sync',
            json={'dry_run': True},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['zone'], 'example.com.')
        self.assertTrue(data['dry_run'])

    def test_sync_zone_not_found(self):
        response = self.client.post(
            '/zones/notfound.com./sync',
            json={'dry_run': True},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 404)

    def test_create_record_error(self):
        # Test API manager exception
        mock_manager = MagicMock()
        mock_manager.manager.config = {
            'api': {'keys': [{'key': 'test-key-123'}]}
        }
        mock_manager.create_or_update_record.side_effect = ApiManagerException(
            'Target not found'
        )
        with patch.object(self.app, 'manager', mock_manager):
            response = self.client.post(
                '/zones/example.com./records/test/A',
                json={'ttl': 300},
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 404)

    def test_create_record_unexpected_error(self):
        # Test generic exception
        mock_manager = MagicMock()
        mock_manager.manager.config = {
            'api': {'keys': [{'key': 'test-key-123'}]}
        }
        mock_manager.create_or_update_record.side_effect = Exception(
            'Unexpected error'
        )
        with patch.object(self.app, 'manager', mock_manager):
            response = self.client.post(
                '/zones/example.com./records/test/A',
                json={'ttl': 300},
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 400)

    def test_get_record_api_manager_error(self):
        mock_manager = MagicMock()
        mock_manager.manager.config = {
            'api': {'keys': [{'key': 'test-key-123'}]}
        }
        mock_manager.get_record.side_effect = ApiManagerException(
            'Zone not configured'
        )
        with patch.object(self.app, 'manager', mock_manager):
            response = self.client.get(
                '/zones/example.com./records/www/A', headers=self.headers
            )
            self.assertEqual(response.status_code, 404)

    def test_get_record_unexpected_error(self):
        mock_manager = MagicMock()
        mock_manager.manager.config = {
            'api': {'keys': [{'key': 'test-key-123'}]}
        }
        mock_manager.get_record.side_effect = Exception('Unexpected')
        with patch.object(self.app, 'manager', mock_manager):
            response = self.client.get(
                '/zones/example.com./records/www/A', headers=self.headers
            )
            self.assertEqual(response.status_code, 500)

    def test_delete_record_api_manager_error(self):
        mock_manager = MagicMock()
        mock_manager.manager.config = {
            'api': {'keys': [{'key': 'test-key-123'}]}
        }
        mock_manager.delete_record.side_effect = ApiManagerException(
            'Zone not configured'
        )
        with patch.object(self.app, 'manager', mock_manager):
            response = self.client.delete(
                '/zones/example.com./records/www/A', headers=self.headers
            )
            self.assertEqual(response.status_code, 404)

    def test_delete_record_unexpected_error(self):
        mock_manager = MagicMock()
        mock_manager.manager.config = {
            'api': {'keys': [{'key': 'test-key-123'}]}
        }
        mock_manager.delete_record.side_effect = Exception('Unexpected')
        with patch.object(self.app, 'manager', mock_manager):
            response = self.client.delete(
                '/zones/example.com./records/www/A', headers=self.headers
            )
            self.assertEqual(response.status_code, 500)

    def test_list_zones_error(self):
        mock_manager = MagicMock()
        mock_manager.manager.config = {
            'api': {'keys': [{'key': 'test-key-123'}]}
        }
        mock_manager.list_zones.side_effect = Exception('Unexpected')
        with patch.object(self.app, 'manager', mock_manager):
            response = self.client.get('/zones', headers=self.headers)
            self.assertEqual(response.status_code, 500)

    def test_get_zone_api_manager_error(self):
        mock_manager = MagicMock()
        mock_manager.manager.config = {
            'api': {'keys': [{'key': 'test-key-123'}]}
        }
        mock_manager.get_zone.side_effect = ApiManagerException(
            'Zone not configured'
        )
        with patch.object(self.app, 'manager', mock_manager):
            response = self.client.get(
                '/zones/example.com.', headers=self.headers
            )
            self.assertEqual(response.status_code, 404)

    def test_get_zone_unexpected_error(self):
        mock_manager = MagicMock()
        mock_manager.manager.config = {
            'api': {'keys': [{'key': 'test-key-123'}]}
        }
        mock_manager.get_zone.side_effect = Exception('Unexpected')
        with patch.object(self.app, 'manager', mock_manager):
            response = self.client.get(
                '/zones/example.com.', headers=self.headers
            )
            self.assertEqual(response.status_code, 500)

    def test_sync_zone_api_manager_error(self):
        mock_manager = MagicMock()
        mock_manager.manager.config = {
            'api': {'keys': [{'key': 'test-key-123'}]}
        }
        mock_manager.sync_zone.side_effect = ApiManagerException(
            'Zone not configured'
        )
        with patch.object(self.app, 'manager', mock_manager):
            response = self.client.post(
                '/zones/example.com./sync',
                json={'dry_run': True},
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 404)

    def test_sync_zone_unexpected_error(self):
        mock_manager = MagicMock()
        mock_manager.manager.config = {
            'api': {'keys': [{'key': 'test-key-123'}]}
        }
        mock_manager.sync_zone.side_effect = Exception('Unexpected')
        with patch.object(self.app, 'manager', mock_manager):
            response = self.client.post(
                '/zones/example.com./sync',
                json={'dry_run': True},
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 500)

    def test_list_records_api_manager_error(self):
        mock_manager = MagicMock()
        mock_manager.manager.config = {
            'api': {'keys': [{'key': 'test-key-123'}]}
        }
        mock_manager.get_zone.side_effect = ApiManagerException(
            'Zone not configured'
        )
        with patch.object(self.app, 'manager', mock_manager):
            response = self.client.get(
                '/zones/example.com./records', headers=self.headers
            )
            self.assertEqual(response.status_code, 404)

    def test_list_records_unexpected_error(self):
        mock_manager = MagicMock()
        mock_manager.manager.config = {
            'api': {'keys': [{'key': 'test-key-123'}]}
        }
        mock_manager.get_zone.side_effect = Exception('Unexpected')
        with patch.object(self.app, 'manager', mock_manager):
            response = self.client.get(
                '/zones/example.com./records', headers=self.headers
            )
            self.assertEqual(response.status_code, 500)

    def test_unauthorized_access(self):
        response = self.client.get('/zones')
        self.assertEqual(response.status_code, 401)

        response = self.client.get(
            '/zones', headers={'Authorization': 'Bearer wrong-key'}
        )
        self.assertEqual(response.status_code, 401)
