import urllib.request
import ssl
import base64

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base64_path = "L29sZHN5cy8yMDEzLTA1LTE1L3JlZ2lzdHJhdGlvblJwSW5mby8yMDEzMDUxNTA5NDUzMTAuanBn"
headers = {"User-Agent": "Mozilla/5.0"}

urls_to_try = [
    f"https://gs.sac.net.cn/publicity/v2/download/photo?photoPath={base64_path}",
    f"https://gs.sac.net.cn/publicity/v2/regFile/downLoadPhoto?photoPath={base64_path}",
    f"https://gs.sac.net.cn/publicity/v2/regFile/downloadUserPhoto?photoPath={base64_path}",
]

for u in urls_to_try:
    try:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, context=ctx) as r:
            data = r.read()
            print(u, r.status, len(data))
            if r.status == 200 and len(data) > 1000:
                print("Found it!")
    except Exception as e:
        print(u, e)
