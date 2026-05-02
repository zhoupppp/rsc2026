# Fix Scraper Stuck Issue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the "stuck" state in the AMAC scraper by removing destructive progress resets, adding robust retry logic to handle rate-limits/connection drops, and fixing resource leaks (zombies/file handles) in the monitor script.

**Architecture:** We will remove the `DELETE` statement that resets progress on every restart, add a `retry` loop with exponential backoff around network requests to handle 403s/502s/timeouts gracefully, and ensure `monitor.py` properly calls `.wait()` and closes file handles when restarting child processes.

**Tech Stack:** Python, `requests` (for AMAC), `httpx` (for SAC), `subprocess` (for monitor).

---

### Task 1: Stop Destructive Progress Reset in AMAC Scraper

**Files:**
- Modify: `financial_scraper/amac_scraper.py`

- [ ] **Step 1: Remove the progress reset logic**

In `financial_scraper/amac_scraper.py` inside the `run_full_pipeline` method, remove the line that deletes `progress_tracking` records for practitioners. This is causing the scraper to start from the first institution every time `monitor.py` restarts it.

```python
    def run_full_pipeline(self):
        """Run the full scraping pipeline."""
        # 1. Scrape All Institutions (over 20,000+)
        self.scrape_institutions(filter_type="")
        
        # 2. Scrape Practitioners for each scraped institution
        query = "SELECT name FROM amac_institutions"
        cursor = self.db.fetch_all(query)
        
        # REMOVE THIS LINE: self.db.execute_query("DELETE FROM progress_tracking WHERE task_name LIKE 'practitioners_%'")
        
        for row in cursor:
            org_name = row.get("name")
```

### Task 2: Add Robust Retry Logic to AMAC Practitioner Scraper

**Files:**
- Modify: `financial_scraper/amac_scraper.py`

- [ ] **Step 1: Add a retry loop for fetching organization userId**

Wrap the `requests.post` call for getting the `userId` in `scrape_practitioners_for_org` in a retry loop.

```python
        # Get org userId
        org_req_url = f"{self.base_url}/personOrg?rand={self._get_rand()}&page=0&size=10"
        org_user_id = None
        
        for attempt in range(5):
            try:
                org_res = self.session.post(org_req_url, json={"orgType": "", "orgName": org_name, "page": 1}, verify=False, timeout=15)
                org_res.raise_for_status()
                org_data = org_res.json()
                if org_data.get("content"):
                    org_user_id = org_data["content"][0].get("userId")
                break # Success
            except Exception as e:
                logger.error(f"Failed to fetch userId for {org_name} (Attempt {attempt+1}/5): {e}")
                time.sleep(2 ** attempt)
                
        if not org_user_id:
            logger.error(f"Could not find userId for {org_name} after retries. Skipping.")
            return
```

- [ ] **Step 2: Add a retry loop for fetching practitioner pages**

Wrap the pagination `requests.post` call inside the `while True` loop with a retry block.

```python
        while True:
            logger.info(f"Fetching practitioners for {org_name} (userId: {org_user_id}), page {page}...")
            response = None
            for attempt in range(5):
                try:
                    response = self.session.post(req_url, json={"userId": org_user_id, "page": page+1}, verify=False, timeout=15)
                    response.raise_for_status()
                    break # Success
                except Exception as e:
                    logger.error(f"Failed to fetch practitioner page {page} for {org_name} (Attempt {attempt+1}/5): {e}")
                    time.sleep(2 ** attempt)
            
            if not response:
                logger.error(f"Failed to fetch practitioner page {page} for {org_name} after 5 retries. Aborting this org.")
                break # Break to avoid infinite loop on persistent errors
                
            try:
                data = response.json()
```

### Task 3: Fix Resource Leaks in Monitor Daemon

**Files:**
- Modify: `financial_scraper/monitor.py`

- [ ] **Step 1: Properly clean up zombie processes and file handles**

In `financial_scraper/monitor.py`, modify the restart logic inside the `while True` loop to call `.wait()` on the killed processes and close the old log file handles before reopening them.

```python
            # Check AMAC progress
            if curr_amac_count > last_amac_count:
                last_amac_count = curr_amac_count
                logging.info(f"AMAC scraper is active. Count increased to {curr_amac_count}")
            elif curr_amac_count == last_amac_count and curr_amac_count != -1:
                logging.warning("AMAC scraper seems stuck (no new data in 20 mins). Terminating and restarting...")
                amac_process.terminate()
                time.sleep(2)
                amac_process.kill()
                amac_process.wait() # Reap zombie process
                
                if not amac_log.closed:
                    amac_log.close() # Prevent file handle leak
                amac_log = open("amac_scraper.log", "a")
                
                amac_process = subprocess.Popen(
                    amac_cmd, stdout=amac_log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, close_fds=True
                )
```

Apply the exact same `.wait()` and `.close()` logic to the SAC scraper restart block:

```python
            # Check SAC progress
            if curr_sac_count > last_sac_count:
                last_sac_count = curr_sac_count
                logging.info(f"SAC scraper is active. Count increased to {curr_sac_count}")
            elif curr_sac_count == last_sac_count and curr_sac_count != -1:
                logging.warning("SAC scraper seems stuck (no new data in 20 mins). Terminating and restarting...")
                sac_process.terminate()
                time.sleep(2)
                sac_process.kill()
                sac_process.wait() # Reap zombie process
                
                if not sac_log.closed:
                    sac_log.close() # Prevent file handle leak
                sac_log = open("sac_scraper.log", "a")
                
                sac_process = subprocess.Popen(
                    sac_cmd, stdout=sac_log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, close_fds=True
                )
```
