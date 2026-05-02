import httpx
import json

client = httpx.Client(verify=False)
headers = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://gs.sac.net.cn",
}
# Test getPersonList
url = "https://gs.sac.net.cn/publicity/v2/getPersonList"
payload = {"aoiId": "199039", "pageNum": 1, "pageSize": 100}
res = client.post(url, data=payload, headers=headers)
print("Status:", res.status_code)
data = res.json()
print("Keys:", data.keys())
if "data" in data and "data" in data["data"]:
    print("Inner Data Type:", type(data["data"]["data"]))
    print("Inner Data Keys:", data["data"]["data"].keys())
    print("Total:", data["data"]["data"].get("total"))
    
payload2 = {"aoiId": "199039", "pageNum": 20000, "pageSize": 100}
res2 = client.post(url, data=payload2, headers=headers)
data2 = res2.json()
print("Page 20000 list:", data2["data"]["data"].get("list", "No list"))
