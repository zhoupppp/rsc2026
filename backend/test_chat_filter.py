import os
import unittest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class ChatFilterTests(unittest.TestCase):
    def test_chat_filter_requires_api_key(self):
        old = os.environ.pop("DEEPSEEK_API_KEY", None)
        try:
            response = client.post(
                "/api/chat/filter",
                json={"messages": [{"role": "user", "content": "test"}]},
            )
            self.assertEqual(response.status_code, 500)
        finally:
            if old is not None:
                os.environ["DEEPSEEK_API_KEY"] = old

if __name__ == "__main__":
    unittest.main()
