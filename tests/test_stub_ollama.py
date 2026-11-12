import unittest

import requests

from tests.stub_ollama import start_stub


class StubTests(unittest.TestCase):
    def test_stub_basics(self):
        srv, url = start_stub()
        try:
            self.assertEqual(requests.get(f"{url}/api/version", timeout=3).json()["version"], "9.9.9")
            self.assertEqual(requests.get(f"{url}/api/unknown", timeout=3).status_code, 404)
            self.assertEqual(requests.post(f"{url}/api/chat", json={"model": "x"}, timeout=3).status_code, 404)
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
