import unittest
from src_py.unrelated import greeting

class TestUnrelated(unittest.TestCase):
    def test_it(self):
        self.assertEqual(greeting(), 'hello')
