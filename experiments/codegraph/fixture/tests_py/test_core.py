import unittest
from src_py.core import normalize_intent

class TestCore(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize_intent(' A '), 'a')
