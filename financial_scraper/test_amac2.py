import logging
logging.basicConfig(level=logging.DEBUG)
from database import db
from amac_scraper import AmacScraper

print("Deleting progress...")
db.execute_query("DELETE FROM progress_tracking WHERE task_name = 'practitioners_上海重阳投资管理股份有限公司'")
print("Init scraper...")
scraper = AmacScraper()
print("Starting scrape...")
scraper.scrape_practitioners_for_org("上海重阳投资管理股份有限公司")
print("Done.")
