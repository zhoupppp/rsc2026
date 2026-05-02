import requests
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Content-Type": "application/json"
}
url = "https://gs.amac.org.cn/amac-infodisc/api/pof/personOrg?rand=0.1&page=200&size=20"
res = requests.post(url, json={"orgType": "", "orgName": "", "page": 0}, headers=headers, verify=False)
data = res.json()
items = data.get("content", [])
print(f"Items length: {len(items)}")
if items: print(f"First item: {items[0].get('orgName')}")
