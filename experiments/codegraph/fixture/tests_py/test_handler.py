import unittest
from src_py.handler import handle_idea

class TestHandler(unittest.TestCase):
    def test_flow(self):
        self.assertEqual(handle_idea(' A ')['intent'], 'a')
