import unittest


class ChatGuidanceTests(unittest.TestCase):
    def test_build_chat_guidance_returns_candidates_and_quick_replies(self):
        from backend.main import build_chat_guidance

        g = build_chat_guidance("武汉看房地产的人", {"adv_office_city": "武汉"})
        self.assertTrue(isinstance(g, dict))
        self.assertTrue("message" in g)
        self.assertTrue("candidates" in g)
        self.assertTrue("quick_replies" in g)
        self.assertTrue("模板" not in str(g.get("message")))


if __name__ == "__main__":
    unittest.main()

