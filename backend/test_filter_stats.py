import json
import urllib.request


def main():
    with urllib.request.urlopen("http://127.0.0.1:8000/api/filters/stats?top_n=200", timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    tags = data.get("fields", {}).get("tags", {}).get("options", [])
    tag_values = {t.get("value") for t in tags if isinstance(t, dict)}
    if "科技" in tag_values:
        raise SystemExit("unexpected tag: 科技")

    if any(isinstance(v, str) and "," in v for v in tag_values):
        raise SystemExit("unexpected unsplit tag containing ','")


if __name__ == "__main__":
    main()

