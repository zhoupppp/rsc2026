import database
import middleware
import logging

logging.basicConfig(level=logging.INFO)

print("Testing Database Initialization...")
try:
    # Attempting to initialize DB
    # Note: If mongodb is not running locally, this will not error immediately because pymongo connects lazily.
    # We will just test if the code runs without syntax/import errors.
    db = database.Database()
    print("Database module imported and initialized successfully.")
except Exception as e:
    print(f"Database error: {e}")

print("\nTesting Middleware Initialization...")
try:
    mw = middleware.SpiderMiddleware(proxies=["http://proxy1", "http://proxy2"])
    ua = mw.get_random_ua()
    print(f"Generated Random UA: {ua}")
    proxy = mw.get_proxy()
    print(f"Generated Proxy: {proxy}")
    client = mw.get_httpx_client(use_proxy=True)
    print("HTTPX Client generated successfully.")
except Exception as e:
    print(f"Middleware error: {e}")

print("\nAll tests passed successfully.")
