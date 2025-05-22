import unittest
from core.environment import EnvironmentManager

class TestEnvironmentManager(unittest.TestCase):
    def test_environment_management(self):
        env_manager = EnvironmentManager()
        env_manager.add_environment('test_env', {'api_url': 'https://api.test.com'})
        self.assertIn('test_env', env_manager.environments)

    def test_apply_environment(self):
        env_manager = EnvironmentManager()
        env_manager.add_environment('test_env', {'api_url': 'https://api.test.com'})
        request_data = {'url': '{{api_url}}/endpoint'}
        updated_request = env_manager.apply_environment(request_data, 'test_env')
        self.assertEqual(updated_request['url'], 'https://api.test.com/endpoint')

if __name__ == '__main__':
    unittest.main()
