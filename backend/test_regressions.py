import json
import urllib.parse
import urllib.request


def get_json(url: str):
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    stats = get_json("http://127.0.0.1:8000/api/filters/stats?top_n=50")
    org_opts = [o["value"] for o in stats["fields"]["adv_org_type"]["options"]]
    assert "公募基金" in org_opts, "adv_org_type stats should include 公募基金"

    total_pub = get_json("http://127.0.0.1:8000/api/talents/search?adv_org_type=%E5%85%AC%E5%8B%9F%E5%9F%BA%E9%87%91")["total"]
    assert total_pub > 0, "adv_org_type=公募基金 should have results"

    q = {
        "op": "and",
        "children": [
            {"field": "adv_office_city", "op": "eq", "value": "深圳"},
            {"field": "tags", "op": "in", "values": ["云计算", "人工智能", "计算机", "通信"]},
        ],
    }
    url = "http://127.0.0.1:8000/api/talents/search?" + urllib.parse.urlencode(
        {"adv_query": json.dumps(q, ensure_ascii=False)}
    )
    total_adv = get_json(url)["total"]
    assert total_adv > 0, "深圳 + 科技相关 tags 的 adv_query 应有结果"

    url2 = "http://127.0.0.1:8000/api/talents/search?" + urllib.parse.urlencode(
        {"adv_office_city": "深圳", "tags": "MSCI中国,云计算,人工智能", "size": 50}
    )
    items = get_json(url2)["items"]
    for it in items:
        for t in it.get("top_tags") or []:
            assert "," not in t, f"top_tags should be split, got: {t}"

    print("OK")


if __name__ == "__main__":
    main()

