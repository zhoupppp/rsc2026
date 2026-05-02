from amac_scraper import AmacScraper

scraper = AmacScraper()
org_req_url = f"{scraper.base_url}/personOrg?rand=0.1&page=0&size=20"
org_res = scraper.session.post(org_req_url, json={"orgType": "", "orgName": "上海重阳投资管理股份有限公司", "page": 1}, verify=False)
org_user_id = org_res.json()["content"][0]["userId"]

req_url = f"{scraper.base_url}/person?rand=0.2&page=0&size=20"
res = scraper.session.post(req_url, json={"userId": org_user_id, "page": 1}, verify=False)
data = res.json()
print("First person:", data["content"][0])
