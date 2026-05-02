import httpx
import logging
import time
import json
import concurrent.futures
from typing import List, Dict, Any
from database import db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class SACScraper:
    def __init__(self):
        self.base_url = "https://gs.sac.net.cn"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://gs.sac.net.cn",
        }
        self.client = httpx.Client(verify=False, timeout=15.0)

    def fetch_org_list(self) -> List[Dict[str, Any]]:
        """Fetch the list of SAC institutions."""
        url = f"{self.base_url}/publicity/v2/getOrgList"
        logger.info(f"Fetching org list from {url}")
        try:
            # Depending on the API, it could be GET or POST. 
            # If it requires POST with empty payload:
            response = self.client.post(url, headers=self.headers, json={"pageNum": 1, "pageSize": 5000})
            response.raise_for_status()
            data = response.json()
            if data.get("success") and "data" in data and "data" in data["data"]:
                orgs = data["data"]["data"]
                logger.info(f"Successfully fetched {len(orgs)} institutions.")
                return orgs
            else:
                logger.error(f"Failed to parse org list: {data}")
        except Exception as e:
            logger.error(f"Error fetching org list: {e}")
        return []

    def fetch_person_list(self, org_id: str, page_num: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """Fetch the practitioner list for a specific institution."""
        url = f"{self.base_url}/publicity/v2/getPersonList"
        payload = {
            "aoiId": org_id,
            "pageNum": page_num,
            "pageSize": page_size
        }
        headers = self.headers.copy()
        
        try:
            response = self.client.post(url, data=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching person list for org {org_id} page {page_num}: {e}")
            return {}

    def fetch_person_detail(self, uuid: str) -> Dict[str, Any]:
        """Fetch the detailed information and practice change records for a practitioner."""
        url = f"{self.base_url}/publicity/v2/getPersonDetail"
        payload = {"uuid": uuid}
        headers = self.headers.copy()
        
        try:
            response = self.client.post(url, data=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            detail = data.get("data", {}).get("data", {}) if "data" in data else data
            return detail
        except Exception as e:
            logger.error(f"Error fetching person detail for {uuid}: {e}")
            return {}

    def sync_institutions(self):
        """Fetch and store all institutions to SQLite."""
        orgs = self.fetch_org_list()
        for org in orgs:
            org_id = org.get("orgId")
            org_name = org.get("orgName")
            
            if not org_id:
                continue
                
            status = "pending"
            try:
                existing_org = db.fetch_one("SELECT raw_data FROM sac_institutions WHERE institution_id = ?", (org_id,))
                if existing_org and existing_org.get("raw_data"):
                    existing_data = json.loads(existing_org["raw_data"])
                    status = existing_data.get("status", "pending")
            except Exception:
                pass
                
            org_data = {
                "institution_id": org_id,
                "name": org_name,
                "orgTypeCode": org.get("orgTypeCode"),
                "pracPersonCnt": org.get("pracPersonCnt"),
                "status": status
            }
            try:
                query = """
                    INSERT INTO sac_institutions (institution_id, name, raw_data, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(institution_id) DO UPDATE SET
                        name=excluded.name,
                        raw_data=excluded.raw_data,
                        updated_at=CURRENT_TIMESTAMP
                """
                db.execute_query(query, (org_id, org_name, json.dumps(org_data, ensure_ascii=False)))
            except Exception as e:
                logger.error(f"Failed to insert org {org_name}: {e}")

    def scrape_practitioners_for_org(self, org_id: str):
        """Scrape all practitioners for a given institution with breakpoint resume."""
        # Get progress
        task_name = f"sac_org_{org_id}"
        progress_row = db.fetch_one("SELECT raw_data FROM progress_tracking WHERE task_name = ?", (task_name,))
        
        start_page = 1
        if progress_row and progress_row.get("raw_data"):
            try:
                progress_data = json.loads(progress_row["raw_data"])
                start_page = progress_data.get("page_num", 1)
            except json.JSONDecodeError:
                pass
                
        page_num = start_page
        page_size = 100
        total_pages = 1
        success = True
        
        while True:
            if page_num > total_pages:
                break
                
            logger.info(f"Fetching persons for org {org_id}, page {page_num}/{total_pages}")
            data = self.fetch_person_list(org_id, page_num, page_size)
            
            if not data or "data" not in data or "data" not in data["data"]:
                logger.warning(f"No person data found for org {org_id} on page {page_num}")
                success = False
                break
                
            page_data = data["data"]["data"]
            
            # If page_data is None, it means no records
            if not page_data:
                break
                
            total_records = int(page_data.get("total", 0))
            total_pages = (total_records + page_size - 1) // page_size
            
            # Update total pages if needed
            if total_pages == 0:
                total_pages = 1
                
            person_list = page_data.get("list", [])
            if not person_list:
                break
                
            for person in person_list:
                uuid = person.get("uuid")
                if not uuid:
                    continue
                    
                # Check if practitioner already exists
                if db.fetch_one("SELECT id FROM sac_practitioners WHERE practitioner_id = ?", (uuid,)):
                    continue
                
                # Fetch details
                detail = self.fetch_person_detail(uuid)
                
                reg_history = detail.get("regHistory", [])
                if isinstance(reg_history, str):
                    try:
                        reg_history = json.loads(reg_history)
                    except:
                        pass
                
                practitioner_data = {
                    "practitioner_id": uuid,
                    "institution_id": org_id,
                    "name": detail.get("name", person.get("name")),
                    "gender": detail.get("gender", person.get("gender")),
                    "certifNo": detail.get("certifNo"),
                    "pracCtegName": detail.get("pracCtegName"),
                    "edu": detail.get("edu"),
                    "regDate": detail.get("regDate"),
                    "photoPath": detail.get("photoPath"),
                    "regHistory": reg_history,
                    "raw_list_data": person
                }
                
                try:
                    query = """
                        INSERT INTO sac_practitioners (practitioner_id, name, institution_id, raw_data, updated_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(practitioner_id) DO UPDATE SET
                            name=excluded.name,
                            institution_id=excluded.institution_id,
                            raw_data=excluded.raw_data,
                            updated_at=CURRENT_TIMESTAMP
                    """
                    db.execute_query(query, (
                        uuid,
                        practitioner_data["name"],
                        org_id,
                        json.dumps(practitioner_data, ensure_ascii=False)
                    ))
                except Exception as e:
                    logger.error(f"Failed to insert practitioner {uuid}: {e}")
                    
            # Save progress after completing a page
            progress_data = {"page_num": page_num + 1, "total_pages": total_pages}
            try:
                query = """
                    INSERT INTO progress_tracking (task_name, status, raw_data, updated_at)
                    VALUES (?, 'in_progress', ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(task_name) DO UPDATE SET
                        status=excluded.status,
                        raw_data=excluded.raw_data,
                        updated_at=CURRENT_TIMESTAMP
                """
                db.execute_query(query, (task_name, json.dumps(progress_data, ensure_ascii=False)))
            except Exception as e:
                logger.error(f"Failed to update progress for org {org_id}: {e}")
            
            page_num += 1

        return success

    def run(self):
        """Main execution flow with breakpoint resume."""
        logger.info("Starting SAC scraping...")
        
        # 1. Sync institutions
        self.sync_institutions()
        
        # 2. Iterate through pending institutions
        all_orgs = db.fetch_all("SELECT * FROM sac_institutions")
        pending_orgs = []
        for org in all_orgs:
            try:
                raw_data = json.loads(org["raw_data"])
                if raw_data.get("status") != "completed":
                    pending_orgs.append(org)
            except Exception:
                pass
                
        logger.info(f"Found {len(pending_orgs)} pending institutions to scrape.")
        
        def process_org(org):
            org_id = org.get("institution_id")
            org_name = org.get("name")
            logger.info(f"Scraping practitioners for {org_name} ({org_id})")
            
            try:
                success = self.scrape_practitioners_for_org(org_id)
                
                if success:
                    # Mark as completed
                    org_raw_data = json.loads(org["raw_data"])
                    org_raw_data["status"] = "completed"
                    query = """
                        UPDATE sac_institutions 
                        SET raw_data = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE institution_id = ?
                    """
                    db.execute_query(query, (json.dumps(org_raw_data, ensure_ascii=False), org_id))
                    logger.info(f"Completed scraping for {org_name}")
            except Exception as e:
                logger.error(f"Error scraping {org_name}: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(process_org, pending_orgs)

        try:
            remaining = 0
            all_orgs = db.fetch_all("SELECT raw_data FROM sac_institutions")
            for org in all_orgs:
                try:
                    raw_data = json.loads(org["raw_data"])
                    if raw_data.get("status") != "completed":
                        remaining += 1
                except Exception:
                    remaining += 1
            if remaining == 0:
                query = """
                    INSERT INTO progress_tracking (task_name, status, raw_data, updated_at)
                    VALUES ('sac_pipeline', 'completed', ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(task_name) DO UPDATE SET
                        status=excluded.status,
                        raw_data=excluded.raw_data,
                        updated_at=CURRENT_TIMESTAMP
                """
                db.execute_query(query, (json.dumps({"task": "sac_pipeline", "completed": True}, ensure_ascii=False),))
        except Exception as e:
            logger.error(f"Failed to update sac_pipeline status: {e}")

if __name__ == "__main__":
    scraper = SACScraper()
    scraper.run()
