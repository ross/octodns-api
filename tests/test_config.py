#
#
#

from tempfile import NamedTemporaryFile
from unittest import TestCase
from unittest.mock import patch

from octodns_api.config import clear_config_cache, get_config


class TestConfig(TestCase):
    def tearDown(self):
        clear_config_cache()

    def test_get_config_basic(self):
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(
                '''
api:
  keys:
    - name: test
      key: plaintext-key

providers:
  config:
    class: octodns.provider.yaml.YamlProvider
    directory: /tmp
'''
            )
            config_file = f.name

        config = get_config(config_file)
        self.assertIn('api', config)
        self.assertEqual(config['api']['keys'][0]['key'], 'plaintext-key')

        # Second call should hit cache
        config2 = get_config(config_file)
        self.assertEqual(config, config2)

    def test_get_config_with_env_vars(self):
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(
                '''
api:
  keys:
    - name: test
      key: env/TEST_API_KEY

providers:
  config:
    class: octodns.provider.yaml.YamlProvider
    directory: /tmp
'''
            )
            config_file = f.name

        with patch.dict('os.environ', {'TEST_API_KEY': 'secret-from-env'}):
            config = get_config(config_file)
            self.assertEqual(config['api']['keys'][0]['key'], 'secret-from-env')

    def test_clear_config_cache(self):
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(
                '''
api:
  keys:
    - name: test
      key: test-key
'''
            )
            config_file = f.name

        # Load config
        config1 = get_config(config_file)
        self.assertEqual(config1['api']['keys'][0]['key'], 'test-key')

        # Clear cache
        clear_config_cache()

        # Load again (should re-read file)
        config2 = get_config(config_file)
        self.assertEqual(config2['api']['keys'][0]['key'], 'test-key')

    def test_get_config_with_non_string_key(self):
        # Test coverage for when key value is not a string
        with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(
                '''
api:
  keys:
    - name: test
      key: 12345

providers:
  config:
    class: octodns.provider.yaml.YamlProvider
    directory: /tmp
'''
            )
            config_file = f.name

        config = get_config(config_file)
        # Should not try to resolve non-string as env var
        self.assertEqual(config['api']['keys'][0]['key'], 12345)
