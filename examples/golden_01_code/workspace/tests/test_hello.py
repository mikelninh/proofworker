import unittest
from hello import greet

class TestHello(unittest.TestCase):
    def test_greet(self):
        self.assertEqual(greet("Ada"), "Hello, Ada!")

if __name__ == "__main__":
    unittest.main()
