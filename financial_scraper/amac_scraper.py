import requests
import time
import random
import logging
import json
from typing import List, Dict, Any, Optional
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

from database import Database

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("amac_scraper")

class AmacScraper:
    def __init__(self):
        self.db = Database()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Origin": "https://gs.amac.org.cn",
            "Referer": "https://gs.amac.org.cn/amac-infodisc/res/pof/person/personOrgList.html",
        })
        self.session.trust_env = False
        self.session.proxies = {"http": None, "https": None}
        self.base_url = "https://gs.amac.org.cn/amac-infodisc/api/pof"

    def _get_rand(self) -> str:
        """Generate a random number for API parameters."""
        return str(random.random())

    def _sleep(self):
        """Random delay to avoid anti-scraping."""
        time.sleep(random.uniform(0.1, 0.5))

    def get_progress(self, task_name: str) -> dict:
        """Get the progress of a specific task."""
        row = self.db.fetch_one(
            "SELECT raw_data FROM progress_tracking WHERE task_name = ?",
            (task_name,)
        )
        if row and row.get('raw_data'):
            try:
                return json.loads(row['raw_data'])
            except json.JSONDecodeError:
                pass
        return {"task": task_name, "page": 0, "completed": False}

    def save_progress(self, task_name: str, page: int, completed: bool = False, extra: dict = None):
        """Save the progress of a specific task."""
        update_doc = {"task": task_name, "page": page, "completed": completed}
        if extra:
            update_doc.update(extra)
            
        status = "completed" if completed else "pending"
        raw_data = json.dumps(update_doc, ensure_ascii=False)
        
        query = """
            INSERT INTO progress_tracking (task_name, status, raw_data, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(task_name) DO UPDATE SET
                status = excluded.status,
                raw_data = excluded.raw_data,
                updated_at = CURRENT_TIMESTAMP
        """
        self.db.execute_query(query, (task_name, status, raw_data))

    def scrape_institutions(self, filter_type: str = ""):
        """
        Scrape institution list and filter by specific type.
        If filter_type is empty, it scrapes all institutions (over 20,000+).
        """
        logger.info(f"Starting to scrape institutions with filter: {filter_type}")
        task_name = f"institutions_{filter_type}" if filter_type else "institutions_all"
        progress = self.get_progress(task_name)
        
        if progress.get("completed"):
            logger.info("Institution scraping already completed.")
            return

        page = progress.get("page", 0)
        size = 20
        
        url = f"{self.base_url}/personOrg?rand={self._get_rand()}&page={{}}&size={size}"

        while True:
            logger.info(f"Fetching institution list page {page}...")
            
            for attempt in range(5):
                try:
                    payload = {"orgType": filter_type, "orgName": "", "page": 0}
                    
                    response = self.session.post(url.format(page), json=payload, verify=False, timeout=15)
                    response.raise_for_status()
                    data = response.json()
                    break
                except Exception as e:
                    logger.error(f"Failed to fetch institution page {page} (Attempt {attempt+1}/5): {e}")
                    time.sleep(2 ** attempt)
            else:
                logger.error(f"Failed to fetch institution page {page} after 5 retries. Aborting.")
                break

            content = data.get("content", [])
            if not content:
                logger.info("No more institutions found. Scraping completed.")
                self.save_progress(task_name, page, completed=True)
                break

            for inst in content:
                manager_name = inst.get("orgName")
                if not manager_name:
                    continue
                
                inst_id = str(inst.get("id") or inst.get("userId") or manager_name)
                raw_data = json.dumps(inst, ensure_ascii=False)
                
                query = """
                    INSERT OR REPLACE INTO amac_institutions 
                    (institution_id, name, raw_data, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """
                try:
                    self.db.execute_query(query, (inst_id, manager_name, raw_data))
                except Exception as e:
                    logger.error(f"Failed to insert institution {manager_name}: {e}")
                
            logger.info(f"Saved {len(content)} institutions from page {page}.")
            self.save_progress(task_name, page)
            
            page += 1
            self._sleep()
            
            # Stop if we reached the last page
            if page >= data.get("totalPages", 0):
                self.save_progress(task_name, page, completed=True)
                break

    def scrape_practitioners_for_org(self, org_name: str, org_user_id: str = None, target_roles: List[str] = None):
        """
        Scrape internal members for a specific institution. 
        Previously filtered by roles, now fetches ALL practitioners to ensure completeness.
        """
        logger.info(f"Scraping practitioners for org: {org_name}")
        task_name = f"practitioners_{org_name}"
        progress = self.get_progress(task_name)
        
        if progress.get("completed"):
            logger.info(f"Practitioner scraping already completed for {org_name}.")
            return

        # 1. First get the org's userId in the personnel system if not provided
        if not org_user_id:
            org_req_url = f"{self.base_url}/personOrg?rand={self._get_rand()}&page=0&size=20"
            
            for attempt in range(5):
                try:
                    org_res = self.session.post(org_req_url, json={"orgType": "", "orgName": org_name, "page": 0}, verify=False, timeout=15)
                    org_res.raise_for_status()
                    org_data = org_res.json()
                    if not org_data.get("content"):
                        logger.info(f"No personnel org found for {org_name}.")
                        self.save_progress(task_name, 0, completed=True)
                        return
                        
                    org_user_id = org_data["content"][0].get("userId")
                    if not org_user_id:
                        logger.info(f"No userId found for {org_name}.")
                        self.save_progress(task_name, 0, completed=True)
                        return
                    break # Success
                except Exception as e:
                    logger.error(f"Failed to fetch org userId for {org_name} (Attempt {attempt+1}/5): {e}")
                    time.sleep(2 ** attempt)
                    
            if not org_user_id:
                logger.error(f"Could not find userId for {org_name} after retries. Skipping.")
                return

        # 2. Iterate through person pages using the org's userId
        page = progress.get("page", 0)
        size = 20
        url = f"{self.base_url}/person"
        
        while True:
            logger.info(f"Fetching practitioners for {org_name} (userId: {org_user_id}), page {page}...")
            req_url = f"{url}?rand={self._get_rand()}&page={page}&size={size}"
            
            for attempt in range(5):
                try:
                    response = self.session.post(req_url, json={"userId": org_user_id, "page": page+1}, verify=False, timeout=15)
                    response.raise_for_status()
                    data = response.json()
                    break # Success
                except Exception as e:
                    logger.error(f"Failed to fetch practitioners for {org_name}, page {page} (Attempt {attempt+1}/5): {e}")
                    time.sleep(2 ** attempt)
            else:
                logger.error(f"Failed to fetch practitioner page {page} for {org_name} after 5 retries. Aborting this org.")
                break # Break to avoid infinite loop on persistent errors

            content = data.get("content", [])
            if not content:
                self.save_progress(task_name, page, completed=True)
                break

            for person in content:
                # personCertHistoryList is already included!
                person_id = person.get("accountId") or person.get("id") or person.get("userId")
                if not person_id:
                    continue
                
                person_name = person.get("userName") or person.get("workerName", "")
                
                # Save all practitioners unconditionally to ensure completeness
                try:
                    self.db.execute_query(
                        """
                        INSERT INTO amac_practitioners (practitioner_id, name, institution_id, raw_data)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(practitioner_id) DO UPDATE SET
                            name=excluded.name,
                            institution_id=excluded.institution_id,
                            raw_data=excluded.raw_data,
                            updated_at=CURRENT_TIMESTAMP
                        """,
                        (str(person_id), person_name, org_name, json.dumps(person, ensure_ascii=False))
                    )
                except Exception as e:
                    logger.error(f"DB Insert error: {e}")
                
            self.save_progress(task_name, page)
            page += 1
            self._sleep()
            
            if page >= data.get("totalPages", 0):
                self.save_progress(task_name, page, completed=True)
                break

    def scrape_person_details(self, person_id: str) -> Dict[str, Any]:
        """
        Scrape detailed info and certificate change records for a person.
        """
        detail_url = f"{self.base_url}/person/{person_id}"
        try:
            time.sleep(0.5)
            response = self.session.get(detail_url, verify=False, timeout=10)
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    return {"detail_fetched": True, "raw_text": response.text[:200]}
        except Exception as e:
            logger.error(f"Failed to fetch details for person {person_id}: {e}")
            
        return {}

    def run_full_pipeline(self):
        """Run the full scraping pipeline."""
        # 1. Scrape All Institutions (over 20,000+)
        self.scrape_institutions(filter_type="")
        
        # 2. Scrape Practitioners for each scraped institution
        query = "SELECT name, raw_data FROM amac_institutions"
        cursor = self.db.fetch_all(query)
        
        # 准备任务参数
        tasks = []
        for row in cursor:
            org_name = row.get("name")
            if not org_name:
                continue
                
            try:
                raw_data = json.loads(row.get("raw_data", "{}"))
                # Try to extract userId directly from institution data to save an API call
                org_user_id = raw_data.get("userId") or raw_data.get("id")
            except:
                org_user_id = None
                
            tasks.append((org_name, org_user_id))
            
        # 并发执行
        max_workers = 10  # 提速：10个并发线程
        logger.info(f"Starting practitioner scraping with {max_workers} threads for {len(tasks)} institutions...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_org = {
                executor.submit(self.scrape_practitioners_for_org, org_name, org_user_id): org_name 
                for org_name, org_user_id in tasks
            }
            
            for future in as_completed(future_to_org):
                org_name = future_to_org[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Critical error in thread scraping {org_name}: {e}")

        self.save_progress("amac_pipeline", 0, completed=True)
                
if __name__ == "__main__":
    scraper = AmacScraper()
    scraper.run_full_pipeline()
