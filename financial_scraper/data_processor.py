import logging
import hashlib
import json
from typing import Dict, Any, List
from database import db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class DataProcessor:
    def __init__(self):
        self.db = db

    def _generate_person_id(self, name: str, cert_no: str) -> str:
        """Generate a unique ID based on name and certificate number."""
        unique_string = f"{name or ''}_{cert_no or ''}".encode('utf-8')
        return hashlib.md5(unique_string).hexdigest()

    def parse_amac_records(self, amac_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Task 4.1: Parse AMAC certificate status change records, extract employment records.
        """
        employment_records = []
        
        # In AMAC data, history might be stored in certList, changeList, or similar fields
        history_keys = ['certList', 'certHistory', 'changeHistory', 'personHistory']
        
        for key in history_keys:
            if key in amac_data and isinstance(amac_data[key], list):
                for record in amac_data[key]:
                    # Map the record to a standard format
                    start_date = record.get('obtainDate') or record.get('startDate') or record.get('regDate')
                    end_date = record.get('cancelDate') or record.get('endDate') or record.get('leaveDate')
                    org_name = record.get('orgName') or record.get('institutionName')
                    role = record.get('certType') or record.get('pracCtegName') or record.get('role')
                    
                    if org_name:
                        employment_records.append({
                            "institution": org_name,
                            "role": role,
                            "start_date": start_date,
                            "end_date": end_date,
                            "source": "AMAC"
                        })
                break # Only process one history key if found
                
        # If no explicit history is found, we can at least use the current institution info
        if not employment_records:
            org_name = amac_data.get('orgName')
            if org_name:
                employment_records.append({
                    "institution": org_name,
                    "role": amac_data.get('certType') or amac_data.get('role'),
                    "start_date": amac_data.get('obtainDate') or amac_data.get('regDate'),
                    "end_date": None,
                    "source": "AMAC"
                })
                
        return employment_records

    def parse_sac_records(self, sac_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Task 4.2: Parse SAC practice change records, extract employment records.
        """
        employment_records = []
        
        # SAC data explicitly defines regHistory
        reg_history = sac_data.get('regHistory', [])
        
        if isinstance(reg_history, list):
            for record in reg_history:
                # Structure: {"orgName": "...", "pracCtegName": "...", "startDate": "...", "endDate": "..."}
                org_name = record.get('orgName') or record.get('ptiName') # sometimes ptiName is used
                if org_name:
                    employment_records.append({
                        "institution": org_name,
                        "role": record.get('pracCtegName') or record.get('jobName'),
                        "start_date": record.get('startDate') or record.get('regDate'),
                        "end_date": record.get('endDate') or record.get('cancelDate'),
                        "source": "SAC"
                    })
                    
        # If no history, use current info
        if not employment_records:
            org_name = sac_data.get('orgName') or sac_data.get('institution_id') # We might need to look up inst name
            if org_name:
                employment_records.append({
                    "institution": org_name,
                    "role": sac_data.get('pracCtegName'),
                    "start_date": sac_data.get('regDate'),
                    "end_date": None,
                    "source": "SAC"
                })

        return employment_records

    def process_and_merge(self):
        """
        Task 4.3: Merge data into standard personnel view and save to unified_personnel.
        """
        logger.info("Starting data processing and merging...")
        
        unified_data = {}
        
        # 1. Process SAC data
        sac_records = self.db.fetch_all("SELECT raw_data FROM sac_practitioners")
        sac_count = 0
        for row in sac_records:
            try:
                doc = json.loads(row['raw_data'])
            except Exception as e:
                logger.error(f"Failed to parse SAC JSON: {e}")
                continue
                
            name = doc.get('name')
            cert_no = doc.get('certifNo')
            
            if not name:
                continue
                
            person_id = self._generate_person_id(name, cert_no)
            
            records = self.parse_sac_records(doc)
            
            if person_id in unified_data:
                existing = unified_data[person_id]
                existing_hashes = {f"{r['institution']}_{r['role']}_{r['start_date']}" for r in existing["employment_records"]}
                for r in records:
                    r_hash = f"{r['institution']}_{r['role']}_{r['start_date']}"
                    if r_hash not in existing_hashes:
                        existing["employment_records"].append(r)
                        existing_hashes.add(r_hash)
            else:
                unified_data[person_id] = {
                    "person_id": person_id,
                    "name": name,
                    "gender": doc.get('gender'),
                    "education": doc.get('edu'),
                    "certificate_number": cert_no,
                    "source": ["SAC"],
                    "employment_records": records,
                    "original_sac_id": doc.get('practitioner_id')
                }
            sac_count += 1
            
        logger.info(f"Processed {sac_count} SAC records.")
        
        # 2. Process AMAC data
        amac_records = self.db.fetch_all("SELECT raw_data FROM amac_practitioners")
        amac_count = 0
        for row in amac_records:
            try:
                doc = json.loads(row['raw_data'])
            except Exception as e:
                logger.error(f"Failed to parse AMAC JSON: {e}")
                continue
                
            name = doc.get('name') or doc.get('userName') or doc.get('workerName')
            cert_no = doc.get('certNo') or doc.get('certifNo') or doc.get('certNum')
            
            if not name:
                continue
                
            person_id = self._generate_person_id(name, cert_no)
            records = self.parse_amac_records(doc)
            
            if person_id in unified_data:
                # Merge
                existing = unified_data[person_id]
                if "AMAC" not in existing["source"]:
                    existing["source"].append("AMAC")
                
                # Combine records, avoiding duplicates based on orgName and role
                existing_hashes = {f"{r['institution']}_{r['role']}_{r['start_date']}" for r in existing["employment_records"]}
                for r in records:
                    r_hash = f"{r['institution']}_{r['role']}_{r['start_date']}"
                    if r_hash not in existing_hashes:
                        existing["employment_records"].append(r)
                        existing_hashes.add(r_hash)
                        
                existing["original_amac_id"] = doc.get('workerId') or doc.get('id')
                
                # Update missing basic info
                if not existing.get("gender") and doc.get("gender"):
                    existing["gender"] = doc.get("gender")
                if not existing.get("education") and (doc.get("eduName") or doc.get("education")):
                    existing["education"] = doc.get("eduName") or doc.get("education")
                if not existing.get("certificate_number") and cert_no:
                    existing["certificate_number"] = cert_no
            else:
                # Create new
                unified_data[person_id] = {
                    "person_id": person_id,
                    "name": name,
                    "gender": doc.get('gender'),
                    "education": doc.get('eduName') or doc.get('education'),
                    "certificate_number": cert_no,
                    "source": ["AMAC"],
                    "employment_records": records,
                    "original_amac_id": doc.get('workerId') or doc.get('id')
                }
            amac_count += 1
            
        logger.info(f"Processed {amac_count} AMAC records.")
        
        # 3. Save to SQLite
        logger.info(f"Saving {len(unified_data)} unified records to database...")
        inserted = 0
        updated = 0
        
        for person_id, data in unified_data.items():
            try:
                # Check if exists to count correctly (optional, but good for logging)
                existing = self.db.fetch_one("SELECT id FROM unified_personnel WHERE person_id = ?", (person_id,))
                
                query = """
                    INSERT INTO unified_personnel (person_id, name, certificate_number, source, raw_data, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(person_id) DO UPDATE SET
                        name=excluded.name,
                        certificate_number=excluded.certificate_number,
                        source=excluded.source,
                        raw_data=excluded.raw_data,
                        updated_at=CURRENT_TIMESTAMP
                """
                self.db.execute_query(query, (
                    person_id,
                    data.get("name"),
                    data.get("certificate_number"),
                    json.dumps(data.get("source", []), ensure_ascii=False),
                    json.dumps(data, ensure_ascii=False)
                ))
                
                if existing:
                    updated += 1
                else:
                    inserted += 1
            except Exception as e:
                logger.error(f"Failed to save unified record for {person_id}: {e}")
                
        logger.info(f"Data processing complete. Inserted: {inserted}, Updated: {updated}.")

if __name__ == "__main__":
    processor = DataProcessor()
    processor.process_and_merge()
