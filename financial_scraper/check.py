import sqlite3

def check():
    conn = sqlite3.connect('/Users/zhoupeng/Documents/rsc2026/financial_scraper/financial_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM sac_practitioners")
    print(f"SAC: {cursor.fetchone()[0]}")
    cursor.execute("SELECT count(*) FROM amac_practitioners")
    print(f"AMAC: {cursor.fetchone()[0]}")
    conn.close()

if __name__ == "__main__":
    check()