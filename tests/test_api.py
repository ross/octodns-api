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
        data = response.get_json()
        self.assertEqual(
            {'name': 'test', 'ttl': 600, 'type': 'A', 'value': '9.9.9.9'}, data
        )
        self.assertEqual(response.status_code, 201)

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
        data = response.get_json()
        self.assertEqual(
            {'name': '', 'ttl': 600, 'type': 'A', 'value': '8.8.8.8'}, data
        )
        self.assertEqual(response.status_code, 201)

        # create or update with no changes is a 200
        response = self.client.post(
            '/zones/example.com./records//A',
            json=record_data,
            headers=self.headers,
        )
        data = response.get_json()
        self.assertEqual(
            {'name': '', 'ttl': 600, 'type': 'A', 'value': '8.8.8.8'}, data
        )
        self.assertEqual(response.status_code, 200)

        # and with a change it'll go back to 201
        record_data['values'] = ['1.2.3.4', '2.3.4.5']
        response = self.client.post(
            '/zones/example.com./records//A',
            json=record_data,
            headers=self.headers,
        )
        data = response.get_json()
        self.assertEqual(
            {
                'name': '',
                'ttl': 600,
                'type': 'A',
                'values': ['1.2.3.4', '2.3.4.5'],
            },
            data,
        )
        self.assertEqual(response.status_code, 201)

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


class TestApiIdna(TestCase):
    '''Tests for IDNA/UTF-8 zone and record names

    octoDNS and octodns-api treat IDNA and UTF-8 names interchangeably.
    For example, café.com and xn--caf-dma.com are considered the same zone.
    '''

    def setUp(self):
        self.tmpdir = mkdtemp()
        self.config_dir = join(self.tmpdir, 'config')
        makedirs(self.config_dir)

        # Create test zone file using UTF-8 zone name: café.com
        # (equivalent to xn--caf-dma.com in IDNA)
        utf8_zone_file = join(self.config_dir, 'café.com.yaml')
        with open(utf8_zone_file, 'w') as f:
            # Mix UTF-8 and IDNA record names
            # señor (UTF-8) vs xn--e1aybc (IDNA for тест)
            f.write(
                '''
---
'':
  ttl: 300
  type: A
  values:
    - 1.2.3.4
señor:
  ttl: 300
  type: A
  values:
    - 10.0.0.1
test:
  ttl: 300
  type: A
  values:
    - 5.6.7.8
xn--e1aybc:
  ttl: 300
  type: A
  values:
    - 10.0.0.2
'''
            )

        # Create zone file using IDNA zone name: xn--wgv71a.example.com
        # (equivalent to 日本.example.com in UTF-8)
        idna_zone_file = join(self.config_dir, 'xn--wgv71a.example.com.yaml')
        with open(idna_zone_file, 'w') as f:
            # Mix IDNA and UTF-8 record names
            f.write(
                '''
---
'':
  ttl: 300
  type: A
  values:
    - 2.3.4.5
müller:
  ttl: 300
  type: A
  values:
    - 4.5.6.7
xn--zckzah:
  ttl: 300
  type: A
  values:
    - 3.4.5.6
'''
            )

        # Create config file mixing UTF-8 and IDNA zone names
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
  café.com.:
    sources:
      - config
    targets:
      - config
  xn--wgv71a.example.com.:
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

    def test_list_zones_mixed_encoding(self):
        '''Test listing zones with mixed UTF-8 and IDNA names'''
        response = self.client.get('/zones', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('zones', data)
        self.assertEqual(['café.com.', '日本.example.com.'], data['zones'])

    def test_get_utf8_zone_by_utf8_name(self):
        '''Test getting UTF-8 configured zone using UTF-8 name (café.com)'''
        response = self.client.get('/zones/café.com.', headers=self.headers)
        data = response.get_json()
        self.assertEqual({'name': 'café.com.'}, data)
        self.assertEqual(response.status_code, 200)

    def test_get_utf8_zone_by_idna_name(self):
        '''Test getting UTF-8 configured zone using IDNA name (xn--caf-dma.com)'''
        response = self.client.get(
            '/zones/xn--caf-dma.com.', headers=self.headers
        )
        data = response.get_json()
        self.assertEqual({'name': 'café.com.'}, data)
        self.assertEqual(response.status_code, 200)

    def test_get_idna_zone_by_idna_name(self):
        '''Test getting IDNA configured zone using IDNA name (xn--wgv71a.example.com)'''
        response = self.client.get(
            '/zones/xn--wgv71a.example.com.', headers=self.headers
        )
        data = response.get_json()
        self.assertEqual({'name': '日本.example.com.'}, data)
        self.assertEqual(response.status_code, 200)

    def test_get_idna_zone_by_utf8_name(self):
        '''Test getting IDNA configured zone using UTF-8 name (日本.example.com)'''
        response = self.client.get(
            '/zones/日本.example.com.', headers=self.headers
        )
        data = response.get_json()
        self.assertEqual({'name': '日本.example.com.'}, data)
        self.assertEqual(response.status_code, 200)

    def test_list_records_mixed_encoding(self):
        '''Test listing records with mixed UTF-8 and IDNA names'''
        response = self.client.get(
            '/zones/café.com./records', headers=self.headers
        )
        data = response.get_json()
        # Should have 4 records: apex, test, señor, xn--e1aybc (тест)
        self.assertEqual(
            {
                'records': {
                    '': {'A': {'ttl': 300, 'value': '1.2.3.4'}},
                    'señor': {'A': {'ttl': 300, 'value': '10.0.0.1'}},
                    'test': {'A': {'ttl': 300, 'value': '5.6.7.8'}},
                    'тест': {'A': {'ttl': 300, 'value': '10.0.0.2'}},
                },
                'zone': 'café.com.',
            },
            data,
        )
        self.assertEqual(response.status_code, 200)

    def test_get_utf8_record_by_utf8_name(self):
        '''Test getting UTF-8 configured record using UTF-8 name (señor)'''
        response = self.client.get(
            '/zones/café.com./records/señor/A', headers=self.headers
        )
        data = response.get_json()
        self.assertEqual(
            {'name': 'señor', 'ttl': 300, 'type': 'A', 'value': '10.0.0.1'},
            data,
        )
        self.assertEqual(response.status_code, 200)

    def test_get_utf8_record_by_idna_name(self):
        '''Test getting UTF-8 configured record using IDNA name (xn--seor-hqa for señor)'''
        response = self.client.get(
            '/zones/café.com./records/xn--seor-hqa/A', headers=self.headers
        )
        data = response.get_json()
        self.assertEqual(
            {'name': 'señor', 'ttl': 300, 'type': 'A', 'value': '10.0.0.1'},
            data,
        )
        self.assertEqual(response.status_code, 200)

    def test_get_idna_record_by_idna_name(self):
        '''Test getting IDNA configured record using IDNA name (xn--e1aybc for тест)'''
        response = self.client.get(
            '/zones/café.com./records/xn--e1aybc/A', headers=self.headers
        )
        data = response.get_json()
        self.assertEqual(
            {'name': 'тест', 'ttl': 300, 'type': 'A', 'value': '10.0.0.2'}, data
        )
        self.assertEqual(response.status_code, 200)

    def test_get_idna_record_by_utf8_name(self):
        '''Test getting IDNA configured record using UTF-8 name (тест)'''
        response = self.client.get(
            '/zones/café.com./records/тест/A', headers=self.headers
        )
        data = response.get_json()
        self.assertEqual(
            {'name': 'тест', 'ttl': 300, 'type': 'A', 'value': '10.0.0.2'}, data
        )
        self.assertEqual(response.status_code, 200)

    def test_get_idna_zone_utf8_record_by_idna(self):
        '''Test getting UTF-8 configured record from IDNA zone using IDNA name'''
        response = self.client.get(
            '/zones/xn--wgv71a.example.com./records/xn--mller-kva/A',
            headers=self.headers,
        )
        data = response.get_json()
        self.assertEqual(
            {'name': 'müller', 'ttl': 300, 'type': 'A', 'value': '4.5.6.7'},
            data,
        )
        self.assertEqual(response.status_code, 200)

    def test_get_idna_zone_utf8_record_by_utf8(self):
        '''Test getting UTF-8 configured record from IDNA zone using UTF-8 name'''
        response = self.client.get(
            '/zones/xn--wgv71a.example.com./records/müller/A',
            headers=self.headers,
        )
        data = response.get_json()
        self.assertEqual(
            {'name': 'müller', 'ttl': 300, 'type': 'A', 'value': '4.5.6.7'},
            data,
        )
        self.assertEqual(response.status_code, 200)

    def test_get_idna_zone_idna_record_by_idna(self):
        '''Test getting IDNA configured record from IDNA zone using IDNA name'''
        response = self.client.get(
            '/zones/xn--wgv71a.example.com./records/xn--zckzah/A',
            headers=self.headers,
        )
        data = response.get_json()
        self.assertEqual(
            {'name': 'テスト', 'ttl': 300, 'type': 'A', 'value': '3.4.5.6'},
            data,
        )
        self.assertEqual(response.status_code, 200)

    def test_get_idna_zone_idna_record_by_utf8(self):
        '''Test getting IDNA configured record from IDNA zone using UTF-8 name (テスト)'''
        response = self.client.get(
            '/zones/日本.example.com./records/テスト/A', headers=self.headers
        )
        data = response.get_json()
        self.assertEqual(
            {'name': 'テスト', 'ttl': 300, 'type': 'A', 'value': '3.4.5.6'},
            data,
        )
        self.assertEqual(response.status_code, 200)

    def test_create_record_with_utf8_name_in_utf8_zone(self):
        '''Test creating a record with UTF-8 name in UTF-8 zone'''
        record_data = {'ttl': 600, 'values': ['9.9.9.9']}
        response = self.client.post(
            '/zones/café.com./records/über/A',
            json=record_data,
            headers=self.headers,
        )
        data = response.get_json()
        self.assertEqual(
            {'name': 'über', 'ttl': 600, 'type': 'A', 'value': '9.9.9.9'}, data
        )
        self.assertEqual(response.status_code, 201)

        # exact same data again, returns 200, no change
        response = self.client.post(
            '/zones/café.com./records/über/A',
            json=record_data,
            headers=self.headers,
        )
        data = response.get_json()
        self.assertEqual(
            {'name': 'über', 'ttl': 600, 'type': 'A', 'value': '9.9.9.9'}, data
        )
        self.assertEqual(response.status_code, 200)

    def test_create_record_with_idna_name_in_idna_zone(self):
        '''Test creating a record with IDNA name in IDNA zone'''
        record_data = {'ttl': 600, 'values': ['8.8.8.8']}
        # xn--wda for ü
        response = self.client.post(
            '/zones/xn--wgv71a.example.com./records/xn--ber-goa/A',
            json=record_data,
            headers=self.headers,
        )
        data = response.get_json()
        self.assertEqual(
            {'name': 'über', 'ttl': 600, 'type': 'A', 'value': '8.8.8.8'}, data
        )
        self.assertEqual(response.status_code, 201)

    def test_delete_utf8_record_from_utf8_zone(self):
        '''Test deleting UTF-8 record from UTF-8 zone using UTF-8 name'''
        response = self.client.delete(
            '/zones/café.com./records/señor/A', headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['deleted'])

    def test_delete_idna_record_from_utf8_zone(self):
        '''Test deleting IDNA record from UTF-8 zone using IDNA name'''
        response = self.client.delete(
            '/zones/café.com./records/xn--e1aybc/A', headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['deleted'])

    def test_delete_utf8_record_from_idna_zone(self):
        '''Test deleting UTF-8 record from IDNA zone using UTF-8 name'''
        response = self.client.delete(
            '/zones/日本.example.com./records/müller/A', headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['deleted'])

    def test_mixed_access_same_record(self):
        '''Test that UTF-8 and IDNA access to same record returns same data'''
        # Access with UTF-8
        response1 = self.client.get(
            '/zones/café.com./records/señor/A', headers=self.headers
        )
        self.assertEqual(response1.status_code, 200)

        # Access with IDNA
        response2 = self.client.get(
            '/zones/xn--caf-dma.com./records/xn--seor-hqa/A',
            headers=self.headers,
        )
        self.assertEqual(response2.status_code, 200)

        # Both should return the same values
        data1 = response1.get_json()
        data2 = response2.get_json()
        self.assertEqual(data1, data2)
