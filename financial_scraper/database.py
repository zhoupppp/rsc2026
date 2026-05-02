import sqlite3
import json
import logging
from datetime import datetime
import os
import threading

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "financial_data_v2.db"):
        """Initialize SQLite connection and set up tables with indexes."""
        self.db_path = db_path
        self.conn = None
        self.lock = threading.Lock()
        self._connect()
        self._init_tables()
        logger.info(f"Connected to SQLite database: {db_path}")

    def _connect(self):
        """Establish connection to the SQLite database."""
        try:
            # Connect to database (creates it if it doesn't exist)
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            # Enable row factory to access columns by name
            self.conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def _init_tables(self):
        """Create tables and indexes if they do not exist."""
        try:
            cursor = self.conn.cursor()

            # 1. amac_institutions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS amac_institutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    institution_id TEXT UNIQUE,
                    name TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_amac_inst_name ON amac_institutions(name)")

            # 2. amac_practitioners
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS amac_practitioners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    practitioner_id TEXT UNIQUE,
                    name TEXT,
                    institution_id TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_amac_prac_name ON amac_practitioners(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_amac_prac_inst ON amac_practitioners(institution_id)")

            # 3. sac_institutions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sac_institutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    institution_id TEXT UNIQUE,
                    name TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sac_inst_name ON sac_institutions(name)")

            # 4. sac_practitioners
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sac_practitioners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    practitioner_id TEXT UNIQUE,
                    name TEXT,
                    institution_id TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sac_prac_name ON sac_practitioners(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sac_prac_inst ON sac_practitioners(institution_id)")

            # 5. progress_tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS progress_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT UNIQUE,
                    last_processed_id TEXT,
                    status TEXT,
                    raw_data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 6. unified_personnel
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS unified_personnel (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id TEXT UNIQUE,
                    name TEXT,
                    certificate_number TEXT,
                    source TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_unified_name ON unified_personnel(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_unified_cert ON unified_personnel(certificate_number)")

            self.conn.commit()
            logger.info("Successfully initialized database tables and indexes.")
            
        except sqlite3.Error as e:
            logger.error(f"Error initializing tables: {e}")
            self.conn.rollback()
            raise

    def execute_query(self, query: str, parameters: tuple = ()):
        """Execute a query that doesn't return data (INSERT, UPDATE, DELETE)."""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute(query, parameters)
                self.conn.commit()
                return cursor.lastrowid
            except sqlite3.Error as e:
                logger.error(f"Error executing query: {e}")
                self.conn.rollback()
                raise

    def fetch_all(self, query: str, parameters: tuple = ()):
        """Execute a query and return all results."""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute(query, parameters)
                return [dict(row) for row in cursor.fetchall()]
            except sqlite3.Error as e:
                logger.error(f"Error fetching data: {e}")
                raise

    def fetch_one(self, query: str, parameters: tuple = ()):
        """Execute a query and return a single result."""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute(query, parameters)
                row = cursor.fetchone()
                return dict(row) if row else None
            except sqlite3.Error as e:
                logger.error(f"Error fetching data: {e}")
                raise

    def close(self):
        """Close the database connection."""
        with self.lock:
            if self.conn:
                self.conn.close()
                logger.info("Database connection closed.")

try:
    # Singleton instance
    db = Database()
except Exception as e:
    logger.warning(f"Failed to initialize database connection on startup: {e}")
    db = None
