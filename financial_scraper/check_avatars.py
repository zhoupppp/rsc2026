import sqlite3
import json

def check_avatars():
    conn = sqlite3.connect('financial_data.db')
    cursor = conn.cursor()
    
    print("--- SAC ---")
    cursor.execute("SELECT raw_data FROM sac_practitioners LIMIT 50")
    for row in cursor.fetchall():
        data = json.loads(row[0])
        # Look for image-like keys
        for k, v in data.items():
            if 'pic' in k.lower() or 'img' in k.lower() or 'photo' in k.lower() or 'avatar' in k.lower():
                print(f"Found potential image key in SAC: {k} = {v}")
                
    print("--- AMAC ---")
    cursor.execute("SELECT raw_data FROM amac_practitioners LIMIT 50")
    for row in cursor.fetchall():
        data = json.loads(row[0])
        for k, v in data.items():
            if 'pic' in k.lower() or 'img' in k.lower() or 'photo' in k.lower() or 'avatar' in k.lower():
                print(f"Found potential image key in AMAC: {k} = {v}")
                
    conn.close()

if __name__ == "__main__":
    check_avatars()
