#
#
#

from tempfile import NamedTemporaryFile
from unittest import TestCase
from unittest.mock import MagicMock, patch

from octodns_api.manager import ApiManager, ApiManagerException


class TestApiManager(TestCase):
    def _get_config_file(self):
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(
                '''
api:
  keys:
    - name: test
      key: test-key

providers:
  yaml:
    class: octodns.provider.yaml.YamlProvider
    directory: /tmp

zones:
  example.com.:
    sources:
      - yaml
    targets:
      - yaml
'''
            )
            return f.name

    def test_list_zones(self):
        config_file = self._get_config_file()
        manager = ApiManager(config_file)
        zones = manager.list_zones()
        self.assertIn('example.com.', zones)

    def test_get_zone_without_trailing_dot(self):
        config_file = self._get_config_file()
        manager = ApiManager(config_file)

        # Mock the provider populate
        with patch.object(
            manager.manager.providers['yaml'], 'populate'
        ) as mock_populate:
            manager.get_zone('example.com')
            # Verify it was called with trailing dot
            args = mock_populate.call_args[0]
            self.assertEqual(args[0].name, 'example.com.')

    def test_get_zone_not_configured(self):
        config_file = self._get_config_file()
        manager = ApiManager(config_file)

        with self.assertRaises(ApiManagerException) as cm:
            manager.get_zone('notfound.com.')

        self.assertIn('not configured', str(cm.exception))

    def test_get_zone_no_sources(self):
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(
                '''
providers:
  yaml:
    class: octodns.provider.yaml.YamlProvider
    directory: /tmp

zones:
  example.com.:
    targets:
      - yaml
'''
            )
            config_file = f.name

        manager = ApiManager(config_file)
        with self.assertRaises(ApiManagerException) as cm:
            manager.get_zone('example.com.')

        self.assertIn('no sources', str(cm.exception))

    def test_get_zone_source_not_found(self):
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(
                '''
providers:
  yaml:
    class: octodns.provider.yaml.YamlProvider
    directory: /tmp

zones:
  example.com.:
    sources:
      - notfound
    targets:
      - yaml
'''
            )
            config_file = f.name

        manager = ApiManager(config_file)
        with self.assertRaises(ApiManagerException) as cm:
            manager.get_zone('example.com.')

        self.assertIn('not found', str(cm.exception))

    def test_create_or_update_record_no_targets(self):
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(
                '''
providers:
  yaml:
    class: octodns.provider.yaml.YamlProvider
    directory: /tmp

zones:
  example.com.:
    sources:
      - yaml
'''
            )
            config_file = f.name

        manager = ApiManager(config_file)
        with self.assertRaises(ApiManagerException) as cm:
            manager.create_or_update_record(
                'example.com.', {'name': 'test', 'type': 'A', 'ttl': 300}
            )

        self.assertIn('no targets', str(cm.exception))

    def test_create_or_update_record_target_not_found(self):
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(
                '''
providers:
  yaml:
    class: octodns.provider.yaml.YamlProvider
    directory: /tmp

zones:
  example.com.:
    sources:
      - yaml
    targets:
      - notfound
'''
            )
            config_file = f.name

        manager = ApiManager(config_file)

        # Mock get_zone to avoid needing real zone data
        with patch.object(manager, 'get_zone') as mock_get_zone:
            mock_zone = MagicMock()
            mock_zone.name = 'example.com.'
            mock_get_zone.return_value = mock_zone

            with self.assertRaises(ApiManagerException) as cm:
                manager.create_or_update_record(
                    'example.com.',
                    {
                        'name': 'test',
                        'type': 'A',
                        'ttl': 300,
                        'values': ['1.2.3.4'],
                    },
                )

            self.assertIn('not found', str(cm.exception))

    def test_delete_record_no_targets(self):
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(
                '''
providers:
  yaml:
    class: octodns.provider.yaml.YamlProvider
    directory: /tmp

zones:
  example.com.:
    sources:
      - yaml
'''
            )
            config_file = f.name

        manager = ApiManager(config_file)
        with self.assertRaises(ApiManagerException) as cm:
            manager.delete_record('example.com.', 'test', 'A')

        self.assertIn('no targets', str(cm.exception))

    def test_delete_record_target_not_found(self):
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(
                '''
providers:
  yaml:
    class: octodns.provider.yaml.YamlProvider
    directory: /tmp

zones:
  example.com.:
    sources:
      - yaml
    targets:
      - notfound
'''
            )
            config_file = f.name

        manager = ApiManager(config_file)

        # Mock get_zone to return a zone with no matching record
        with patch.object(manager, 'get_zone') as mock_get_zone:
            mock_zone = MagicMock()
            mock_zone.name = 'example.com.'
            mock_zone.records = []
            mock_get_zone.return_value = mock_zone

            result = manager.delete_record('example.com.', 'test', 'A')
            self.assertFalse(result)

    def test_create_or_update_record_not_configured(self):
        config_file = self._get_config_file()
        manager = ApiManager(config_file)

        with self.assertRaises(ApiManagerException) as cm:
            manager.create_or_update_record(
                'notfound.com.',
                {
                    'name': 'test',
                    'type': 'A',
                    'ttl': 300,
                    'values': ['1.2.3.4'],
                },
            )

        self.assertIn('not configured', str(cm.exception))

    def test_delete_record_not_configured(self):
        config_file = self._get_config_file()
        manager = ApiManager(config_file)

        with self.assertRaises(ApiManagerException) as cm:
            manager.delete_record('notfound.com.', 'test', 'A')

        self.assertIn('not configured', str(cm.exception))

    def test_create_or_update_without_trailing_dot(self):
        config_file = self._get_config_file()
        manager = ApiManager(config_file)

        # Mock to test without trailing dot handling
        with patch.object(manager, 'get_zone') as mock_get_zone:
            mock_zone = MagicMock()
            mock_zone.name = 'example.com.'
            mock_get_zone.return_value = mock_zone

            with patch.object(
                manager.manager.providers['yaml'], 'plan'
            ) as mock_plan:
                mock_plan.return_value = None

                record, changed = manager.create_or_update_record(
                    'example.com',
                    {
                        'name': 'test',
                        'type': 'A',
                        'ttl': 300,
                        'values': ['1.2.3.4'],
                    },
                )

                self.assertFalse(changed)

    def test_delete_record_without_trailing_dot(self):
        config_file = self._get_config_file()
        manager = ApiManager(config_file)

        # Mock to test without trailing dot handling
        with patch.object(manager, 'get_zone') as mock_get_zone:
            mock_zone = MagicMock()
            mock_zone.name = 'example.com.'
            mock_zone.records = []
            mock_get_zone.return_value = mock_zone

            result = manager.delete_record('example.com', 'test', 'A')
            self.assertFalse(result)

    def test_sync_zone_without_trailing_dot(self):
        config_file = self._get_config_file()
        manager = ApiManager(config_file)

        with patch.object(manager.manager, 'sync') as mock_sync:
            mock_sync.return_value = 0

            result = manager.sync_zone('example.com', dry_run=True)

            self.assertEqual(result['zone'], 'example.com.')
            self.assertTrue(result['dry_run'])

    def test_create_or_update_record_with_plan(self):
        config_file = self._get_config_file()
        manager = ApiManager(config_file)

        # Mock to test when plan returns changes
        with patch.object(manager, 'get_zone') as mock_get_zone:
            mock_zone = MagicMock()
            mock_zone.name = 'example.com.'
            mock_get_zone.return_value = mock_zone

            with patch.object(
                manager.manager.providers['yaml'], 'plan'
            ) as mock_plan:
                with patch.object(
                    manager.manager.providers['yaml'], 'apply'
                ) as mock_apply:
                    mock_plan.return_value = MagicMock()  # Returns a plan

                    record, changed = manager.create_or_update_record(
                        'example.com.',
                        {
                            'name': 'test',
                            'type': 'A',
                            'ttl': 300,
                            'values': ['1.2.3.4'],
                        },
                    )

                    self.assertTrue(changed)
                    mock_apply.assert_called_once()

    def test_delete_record_with_plan(self):
        config_file = self._get_config_file()
        manager = ApiManager(config_file)

        # Mock to test when plan returns changes
        with patch.object(manager, 'get_zone') as mock_get_zone:
            mock_zone = MagicMock()
            mock_zone.name = 'example.com.'
            mock_record = MagicMock()
            mock_record.name = 'test'
            mock_record._type = 'A'
            mock_zone.records = [mock_record]
            mock_get_zone.return_value = mock_zone

            with patch.object(
                manager.manager.providers['yaml'], 'plan'
            ) as mock_plan:
                with patch.object(
                    manager.manager.providers['yaml'], 'apply'
                ) as mock_apply:
                    mock_plan.return_value = MagicMock()  # Returns a plan

                    result = manager.delete_record('example.com.', 'test', 'A')

                    self.assertTrue(result)
                    mock_apply.assert_called_once()

    def test_delete_record_target_really_not_found(self):
        # Test when target provider doesn't exist
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(
                '''
providers:
  yaml:
    class: octodns.provider.yaml.YamlProvider
    directory: /tmp

zones:
  example.com.:
    sources:
      - yaml
    targets:
      - notfound
'''
            )
            config_file = f.name

        manager = ApiManager(config_file)

        # Mock get_zone to return a zone with a record
        with patch.object(manager, 'get_zone') as mock_get_zone:
            mock_zone = MagicMock()
            mock_zone.name = 'example.com.'
            mock_record = MagicMock()
            mock_record.name = 'test'
            mock_record._type = 'A'
            mock_zone.records = [mock_record]
            mock_get_zone.return_value = mock_zone

            with self.assertRaises(ApiManagerException) as cm:
                manager.delete_record('example.com.', 'test', 'A')

            self.assertIn('not found', str(cm.exception))

    def test_delete_record_no_plan(self):
        config_file = self._get_config_file()
        manager = ApiManager(config_file)

        # Mock to test when plan returns None (no changes)
        with patch.object(manager, 'get_zone') as mock_get_zone:
            mock_zone = MagicMock()
            mock_zone.name = 'example.com.'
            mock_record = MagicMock()
            mock_record.name = 'test'
            mock_record._type = 'A'
            mock_zone.records = [mock_record]
            mock_get_zone.return_value = mock_zone

            with patch.object(
                manager.manager.providers['yaml'], 'plan'
            ) as mock_plan:
                mock_plan.return_value = None  # No plan (no changes)

                result = manager.delete_record('example.com.', 'test', 'A')

                self.assertFalse(result)
