import logging
from amac_scraper import AmacScraper

logging.basicConfig(level=logging.DEBUG)
scraper = AmacScraper()
scraper.scrape_institutions()
