import unittest
from core.executor import Executor

class TestExecutor(unittest.TestCase):
    def test_execute_request(self):
        executor = Executor()
        request_data = {
            'method': 'GET',
            'url': 'https://api.github.com',
        }
        response = executor.execute_request(request_data)
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
