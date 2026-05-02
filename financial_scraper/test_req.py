import requests
import random

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://gs.amac.org.cn/amac-infodisc/res/pof/person/personOrgList.html",
})

url = f"https://gs.amac.org.cn/amac-infodisc/api/pof/person?rand={random.random()}&page=0&size=20"
payload = {"userId": 2309140927320704, "page": 1}
res = session.post(url, json=payload, verify=False, proxies={"http": None, "https": None})
print("Status:", res.status_code)
if res.status_code == 200:
    print("Content:", res.json())
else:
    print("Response text:", res.text)
