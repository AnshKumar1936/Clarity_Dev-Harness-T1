import os
import json
import unittest
from unittest.mock import MagicMock, patch
from src.memory_store import MemoryStore

def mock_openai_response():
    class MockResponse:
        def __init__(self):
            self.choices = [MagicMock()]
            self.choices[0].message = MagicMock()
            self.choices[0].message.content = json.dumps({
                'user_profile': 'test user',
                'preferences': ['test preference'],
                'work_in_progress': ['test work'],
                'open_loops': [],
                'last_updated': '2023-01-01T00:00:00.000000'
            })
    return MockResponse()

class TestMemoryStore(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_memory"
        os.makedirs(self.test_dir, exist_ok=True)
        self.memory_file = os.path.join(self.test_dir, "long_term.json")
        
        # Patch the OpenAI client
        self.patcher = patch('src.memory_store.OpenAI')
        self.mock_openai = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_openai.return_value = self.mock_client
        self.mock_client.chat.completions.create.return_value = mock_openai_response()
        
        self.store = MemoryStore(memory_dir=self.test_dir)

    def tearDown(self):
        # Cleanup
        if os.path.exists(self.memory_file):
            os.remove(self.memory_file)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)
        self.patcher.stop()

    def test_invalid_json_handling(self):
        # Test 1: Invalid JSON
        with open(self.memory_file, 'w') as f:
            f.write("This is not valid JSON")
        
        memory = self.store.load_long_term_memory()
        self.assertIsNone(memory, "Should return None for invalid JSON")

    def test_empty_file(self):
        # Test 2: Empty file
        open(self.memory_file, 'w').close()
        memory = self.store.load_long_term_memory()
        self.assertIsNone(memory, "Should return None for empty file")

    def test_missing_required_fields(self):
        # Test 3: Missing required fields
        with open(self.memory_file, 'w') as f:
            json.dump({"test": "invalid"}, f)
        memory = self.store.load_long_term_memory()
        self.assertIsNone(memory, "Should return None for missing required fields")

    def test_valid_memory_save_and_load(self):
        # Test 4: Valid memory save and load
        test_memory = {
            'user_profile': 'test user',
            'preferences': ['test preference'],
            'work_in_progress': ['test work'],
            'open_loops': [],
            'last_updated': '2023-01-01T00:00:00.000000'
        }
        
        # Test save
        result = self.store.save_long_term_memory(test_memory)
        self.assertTrue(result, "Save should succeed with valid memory")
        
        # Test load
        loaded = self.store.load_long_term_memory()
        self.assertEqual(loaded, test_memory, "Loaded memory should match saved memory")

if __name__ == "__main__":
    unittest.main()
