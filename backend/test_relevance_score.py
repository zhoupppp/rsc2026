import unittest


class RelevanceScoreTests(unittest.TestCase):
    def test_overlap_counts(self):
        from backend.main import compute_relevance_score

        desired = ["云计算", "人工智能", "AIGC"]
        candidate = ["人工智能", "新能源", "云计算"]
        self.assertEqual(compute_relevance_score(desired, candidate), 2)


if __name__ == "__main__":
    unittest.main()

