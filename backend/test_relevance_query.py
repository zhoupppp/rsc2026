import unittest


class RelevanceQuerySplitTests(unittest.TestCase):
    def test_split_hard_soft_from_and_query(self):
        from backend.main import split_query_hard_soft

        q = {
            "op": "and",
            "children": [
                {"field": "adv_office_city", "op": "eq", "value": "深圳"},
                {"field": "tags", "op": "in", "values": ["云计算", "人工智能"]},
            ],
        }

        hard, soft = split_query_hard_soft(q)
        self.assertEqual(soft, ["云计算", "人工智能"])
        self.assertEqual(
            hard,
            {"field": "adv_office_city", "op": "eq", "value": "深圳"},
        )


if __name__ == "__main__":
    unittest.main()
