import sqlite3
import pandas as pd
import os

DB_PATH = 'financial_scraper/financial_data.db'
USER_FILE = 'rsc用户/RSC用户：完整信息_认证、名片、投研行业、行为偏好、价值标签 -26.04.24全部用户.xlsx'
ORG_FILE = 'rsc用户/RSC机构库：完整信息_基础、画像、标签 2025.09.xlsx'

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS rsc_users')
    cursor.execute('DROP TABLE IF EXISTS rsc_orgs')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rsc_users (
        uid TEXT PRIMARY KEY,
        name TEXT,
        cert_type TEXT,
        org_name TEXT,
        oid TEXT,
        org_short_name TEXT,
        position TEXT,
        department TEXT,
        cert_time TEXT,
        org_full_name TEXT,
        org_type TEXT,
        stock_code TEXT,
        last_active_time TEXT,
        register_time TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rsc_orgs (
        oid TEXT PRIMARY KEY,
        full_name TEXT,
        short_name TEXT,
        en_name TEXT,
        en_short_name TEXT,
        aliases TEXT,
        logo TEXT,
        region TEXT,
        website TEXT,
        email TEXT,
        biz_reg_no TEXT,
        credit_code TEXT,
        amac_record TEXT,
        amac_url TEXT,
        org_type TEXT
    )
    ''')
    conn.commit()

def import_users(conn):
    print(f"Reading users from {USER_FILE}...")
    xls = pd.ExcelFile(USER_FILE)
    df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
    
    # Fill NaN with empty string
    df = df.fillna('')
    
    records = []
    for _, row in df.iterrows():
        uid = str(row.get('uid', '')).strip()
        if not uid:
            continue
            
        oid_val = row.get('机构OID', '')
        oid = str(int(oid_val)) if isinstance(oid_val, float) and pd.notna(oid_val) else str(oid_val).strip()
        
        records.append((
            uid,
            str(row.get('姓名', '')).strip(),
            str(row.get('认证类型', '')).strip(),
            str(row.get('机构名', '')).strip(),
            oid,
            str(row.get('机构简称', '')).strip(),
            str(row.get('职位', '')).strip(),
            str(row.get('部门', '')).strip(),
            str(row.get('认证时间', '')).strip(),
            str(row.get('机构全称(最新名称)', '')).strip(),
            str(row.get('机构类型', '')).strip(),
            str(row.get('公司股票代码', '')).strip(),
            str(row.get('最近活跃时间', '')).strip(),
            str(row.get('注册时间', '')).strip()
        ))
        
    cursor = conn.cursor()
    cursor.executemany('''
    INSERT INTO rsc_users (
        uid, name, cert_type, org_name, oid, org_short_name, position, department,
        cert_time, org_full_name, org_type, stock_code, last_active_time, register_time
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(uid) DO UPDATE SET
        name=excluded.name,
        cert_type=excluded.cert_type,
        org_name=excluded.org_name,
        oid=excluded.oid,
        org_short_name=excluded.org_short_name,
        position=excluded.position,
        department=excluded.department,
        cert_time=excluded.cert_time,
        org_full_name=excluded.org_full_name,
        org_type=excluded.org_type,
        stock_code=excluded.stock_code,
        last_active_time=excluded.last_active_time,
        register_time=excluded.register_time
    ''', records)
    conn.commit()
    print(f"Imported {len(records)} users.")

def import_orgs(conn):
    print(f"Reading orgs from {ORG_FILE}...")
    xls = pd.ExcelFile(ORG_FILE)
    df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
    df = df.fillna('')
    
    records = []
    for _, row in df.iterrows():
        oid_val = row.get('机构OID', '')
        oid = str(int(oid_val)) if isinstance(oid_val, float) and pd.notna(oid_val) else str(oid_val).strip()
        if not oid:
            continue
            
        records.append((
            oid,
            str(row.get('全称', '')).strip(),
            str(row.get('简称', '')).strip(),
            str(row.get('英文名', '')).strip(),
            str(row.get('英文简称', '')).strip(),
            str(row.get('别名/曾用名', '')).strip(),
            str(row.get('机构logo', '')).strip(),
            str(row.get('国家地区', '')).strip(),
            str(row.get('官网', '')).strip(),
            str(row.get('机构邮箱', '')).strip(),
            str(row.get('工商登记号', '')).strip(),
            str(row.get('统一信用代码', '')).strip(),
            str(row.get('中基协备案', '')).strip(),
            str(row.get('中基协备案公示网站', '')).strip(),
            str(row.get('机构类型', '')).strip()
        ))
        
    cursor = conn.cursor()
    cursor.executemany('''
    INSERT INTO rsc_orgs (
        oid, full_name, short_name, en_name, en_short_name, aliases, logo, region,
        website, email, biz_reg_no, credit_code, amac_record, amac_url, org_type
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(oid) DO UPDATE SET
        full_name=excluded.full_name,
        short_name=excluded.short_name,
        en_name=excluded.en_name,
        en_short_name=excluded.en_short_name,
        aliases=excluded.aliases,
        logo=excluded.logo,
        region=excluded.region,
        website=excluded.website,
        email=excluded.email,
        biz_reg_no=excluded.biz_reg_no,
        credit_code=excluded.credit_code,
        amac_record=excluded.amac_record,
        amac_url=excluded.amac_url,
        org_type=excluded.org_type
    ''', records)
    conn.commit()
    print(f"Imported {len(records)} orgs.")

def main():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}. Exiting.")
        return
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    import_orgs(conn)
    import_users(conn)
    conn.close()
    print("Import completed.")

if __name__ == '__main__':
    main()