#
#
#

from os import makedirs
from os.path import join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from octodns_api.app import create_app


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
        self.assertIn('records', data)
        self.assertEqual(len(data['records']), 2)

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

    def test_create_record(self):
        record_data = {
            'name': 'test',
            'ttl': 600,
            'type': 'A',
            'values': ['9.9.9.9'],
        }
        response = self.client.post(
            '/zones/example.com./records',
            json=record_data,
            headers=self.headers,
        )
        self.assertIn(response.status_code, [200, 201])
        data = response.get_json()
        self.assertIn('record', data)
        self.assertEqual(data['record']['name'], 'test')

    def test_create_record_no_data(self):
        # Test with empty/null JSON to ensure get_json() returns None
        response = self.client.post(
            '/zones/example.com./records',
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
        from unittest.mock import patch

        from octodns_api.manager import ApiManagerException

        with patch('octodns_api.api.records.ApiManager') as mock_manager:
            mock_manager.return_value.create_or_update_record.side_effect = (
                ApiManagerException('Target not found')
            )
            response = self.client.post(
                '/zones/example.com./records',
                json={'name': 'test', 'ttl': 300, 'type': 'A'},
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 404)

    def test_create_record_unexpected_error(self):
        # Test generic exception
        from unittest.mock import patch

        with patch('octodns_api.api.records.ApiManager') as mock_manager:
            mock_manager.return_value.create_or_update_record.side_effect = (
                Exception('Unexpected error')
            )
            response = self.client.post(
                '/zones/example.com./records',
                json={'name': 'test', 'ttl': 300, 'type': 'A'},
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 400)

    def test_get_record_api_manager_error(self):
        from unittest.mock import patch

        from octodns_api.manager import ApiManagerException

        with patch('octodns_api.api.records.ApiManager') as mock_manager:
            mock_manager.return_value.get_record.side_effect = (
                ApiManagerException('Zone not configured')
            )
            response = self.client.get(
                '/zones/example.com./records/www/A', headers=self.headers
            )
            self.assertEqual(response.status_code, 404)

    def test_get_record_unexpected_error(self):
        from unittest.mock import patch

        with patch('octodns_api.api.records.ApiManager') as mock_manager:
            mock_manager.return_value.get_record.side_effect = Exception(
                'Unexpected'
            )
            response = self.client.get(
                '/zones/example.com./records/www/A', headers=self.headers
            )
            self.assertEqual(response.status_code, 500)

    def test_delete_record_api_manager_error(self):
        from unittest.mock import patch

        from octodns_api.manager import ApiManagerException

        with patch('octodns_api.api.records.ApiManager') as mock_manager:
            mock_manager.return_value.delete_record.side_effect = (
                ApiManagerException('Zone not configured')
            )
            response = self.client.delete(
                '/zones/example.com./records/www/A', headers=self.headers
            )
            self.assertEqual(response.status_code, 404)

    def test_delete_record_unexpected_error(self):
        from unittest.mock import patch

        with patch('octodns_api.api.records.ApiManager') as mock_manager:
            mock_manager.return_value.delete_record.side_effect = Exception(
                'Unexpected'
            )
            response = self.client.delete(
                '/zones/example.com./records/www/A', headers=self.headers
            )
            self.assertEqual(response.status_code, 500)

    def test_list_zones_error(self):
        from unittest.mock import patch

        with patch('octodns_api.api.zones.ApiManager') as mock_manager:
            mock_manager.return_value.list_zones.side_effect = Exception(
                'Unexpected'
            )
            response = self.client.get('/zones', headers=self.headers)
            self.assertEqual(response.status_code, 500)

    def test_get_zone_api_manager_error(self):
        from unittest.mock import patch

        from octodns_api.manager import ApiManagerException

        with patch('octodns_api.api.zones.ApiManager') as mock_manager:
            mock_manager.return_value.get_zone.side_effect = (
                ApiManagerException('Zone not configured')
            )
            response = self.client.get(
                '/zones/example.com.', headers=self.headers
            )
            self.assertEqual(response.status_code, 404)

    def test_get_zone_unexpected_error(self):
        from unittest.mock import patch

        with patch('octodns_api.api.zones.ApiManager') as mock_manager:
            mock_manager.return_value.get_zone.side_effect = Exception(
                'Unexpected'
            )
            response = self.client.get(
                '/zones/example.com.', headers=self.headers
            )
            self.assertEqual(response.status_code, 500)

    def test_sync_zone_api_manager_error(self):
        from unittest.mock import patch

        from octodns_api.manager import ApiManagerException

        with patch('octodns_api.api.zones.ApiManager') as mock_manager:
            mock_manager.return_value.sync_zone.side_effect = (
                ApiManagerException('Zone not configured')
            )
            response = self.client.post(
                '/zones/example.com./sync',
                json={'dry_run': True},
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 404)

    def test_sync_zone_unexpected_error(self):
        from unittest.mock import patch

        with patch('octodns_api.api.zones.ApiManager') as mock_manager:
            mock_manager.return_value.sync_zone.side_effect = Exception(
                'Unexpected'
            )
            response = self.client.post(
                '/zones/example.com./sync',
                json={'dry_run': True},
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 500)

    def test_list_records_api_manager_error(self):
        from unittest.mock import patch

        from octodns_api.manager import ApiManagerException

        with patch('octodns_api.api.records.ApiManager') as mock_manager:
            mock_manager.return_value.get_zone.side_effect = (
                ApiManagerException('Zone not configured')
            )
            response = self.client.get(
                '/zones/example.com./records', headers=self.headers
            )
            self.assertEqual(response.status_code, 404)

    def test_list_records_unexpected_error(self):
        from unittest.mock import patch

        with patch('octodns_api.api.records.ApiManager') as mock_manager:
            mock_manager.return_value.get_zone.side_effect = Exception(
                'Unexpected'
            )
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
