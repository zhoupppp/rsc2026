import sqlite3

def test_sqlite():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
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
    query = """
        INSERT INTO sac_institutions (institution_id, name, raw_data, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(institution_id) DO UPDATE SET
            name=excluded.name,
            raw_data=excluded.raw_data,
            updated_at=CURRENT_TIMESTAMP
    """
    cursor.execute(query, ("1", "test1", "{}"))
    cursor.execute(query, ("1", "test2", "{\"status\": \"pending\"}"))
    
    cursor.execute("SELECT * FROM sac_institutions")
    print(cursor.fetchall())

if __name__ == "__main__":
    test_sqlite()
