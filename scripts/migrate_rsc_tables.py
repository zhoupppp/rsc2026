import sqlite3
import os

DB_PATH = 'financial_scraper/financial_data.db'

def alter_table(cursor, table, col, col_type="TEXT"):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        print(f"Added {col} to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            raise e

def main():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}.")
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 扩充 rsc_users
    alter_table(cursor, "rsc_users", "gender")
    alter_table(cursor, "rsc_users", "intro")
    alter_table(cursor, "rsc_users", "birthday")
    alter_table(cursor, "rsc_users", "highest_edu")
    alter_table(cursor, "rsc_users", "university")
    alter_table(cursor, "rsc_users", "major")
    alter_table(cursor, "rsc_users", "ext_data") # JSON string
    
    # 扩充 rsc_orgs
    alter_table(cursor, "rsc_orgs", "aum")
    alter_table(cursor, "rsc_orgs", "value_score")
    alter_table(cursor, "rsc_orgs", "influence_score")
    alter_table(cursor, "rsc_orgs", "invest_position")
    alter_table(cursor, "rsc_orgs", "is_foreign")
    alter_table(cursor, "rsc_orgs", "ext_data") # JSON string
    
    conn.commit()
    conn.close()
    print("Database migration completed.")

if __name__ == '__main__':
    main()
