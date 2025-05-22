import unittest
from core.importer import Importer

class TestImporter(unittest.TestCase):
    def test_import_collection(self):
        importer = Importer()
        # Crie um arquivo JSON de teste ou use um mock
        test_file = 'tests/test_collection.json'
        data = importer.import_collection(test_file)
        self.assertIsNotNone(data)
        # Adicione mais assertivas conforme necessário

if __name__ == '__main__':
    unittest.main()
