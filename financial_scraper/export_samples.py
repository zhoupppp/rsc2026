import sqlite3
import json

def export_samples():
    conn = sqlite3.connect('/Users/zhoupeng/Documents/rsc2026/financial_scraper/financial_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("========== 中证协 (SAC) 机构数据样本 ==========")
    cursor.execute("SELECT * FROM sac_institutions LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(f"机构ID: {row['institution_id']}, 名称: {row['name']}")
        print(f"原始数据: {json.loads(row['raw_data'])}")
    print("\n")
    
    print("========== 中证协 (SAC) 人员数据样本 ==========")
    cursor.execute("SELECT * FROM sac_practitioners LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(f"人员ID: {row['practitioner_id']}, 姓名: {row['name']}, 机构ID: {row['institution_id']}")
        data = json.loads(row['raw_data'])
        print(f"原始数据中的执业变更记录条数: {len(data.get('regHistory', []))}")
        print(f"原始数据: {data}")
    print("\n")
    
    print("========== 中基协 (AMAC) 机构数据样本 ==========")
    cursor.execute("SELECT * FROM amac_institutions LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(f"机构ID: {row['institution_id']}, 名称: {row['name']}")
        print(f"原始数据: {json.loads(row['raw_data'])}")
    print("\n")
    
    conn.close()

if __name__ == "__main__":
    export_samples()