# RSC 数据交叉比对重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 RSC 平台最新导出的多 Sheet 完整用户和机构 Excel 数据导入 SQLite 数据库，并基于 OID 关联和机构别名机制重构与 SAC/AMAC 数据的比对引擎，提升数据匹配精度与持久化管理能力。

**Architecture:** 
1. `scripts/import_rsc_data.py`: 使用 `pandas` 读取两个新的 Excel 文件，将核心列提取并落库到 `financial_scraper/financial_data.db` 的 `rsc_users` 和 `rsc_orgs` 表中。
2. `scripts/rsc_cross_check.py`: 修改比对逻辑。在判断一个用户时，优先通过其 `oid` 在 `rsc_orgs` 库中拿到全面的“别名/曾用名”列表进行精确+模糊匹配；如果没有 OID，则回退使用原有的 `org_name` 进行匹配。最终依然将结果 UPSERT 到 `rsc_user_mapping` 表并输出报告。

**Tech Stack:** Python 3, Pandas, SQLite, zhconv

---

### Task 1: 编写数据导入脚本 (Data Ingestion)

**Files:**
- Create: `scripts/import_rsc_data.py`

- [ ] **Step 1: 编写导入脚本**

创建 `scripts/import_rsc_data.py`：

```python
import sqlite3
import pandas as pd
import os

DB_PATH = 'financial_scraper/financial_data.db'
USER_FILE = 'rsc用户/RSC用户：完整信息_认证、名片、投研行业、行为偏好、价值标签 -26.04.24全部用户.xlsx'
ORG_FILE = 'rsc用户/RSC机构库：完整信息_基础、画像、标签 2025.09.xlsx'

def init_db(conn):
    cursor = conn.cursor()
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
```

- [ ] **Step 2: 运行导入脚本以验证并生成数据**

Run: `python3 scripts/import_rsc_data.py`
Expected: 成功读取 Excel 并插入数据，控制台打印 "Import completed."。

### Task 2: 重构交叉比对引擎

**Files:**
- Modify: `scripts/rsc_cross_check.py`

- [ ] **Step 1: 重写 `rsc_cross_check.py` 脚本内容**

用以下内容完全替换 `scripts/rsc_cross_check.py`：

```python
import sqlite3
import json
import re
import zhconv
import pandas as pd
from datetime import datetime

SUFFIX_WORDS = [
    '股份有限公司', '有限责任公司', '有限公司', '股份公司',
    '研究所', '营业部', '分公司', '资产管理总部', '资产管理部', '资产管理',
    '研发中心', '研究中心', '投资银行部', '投行部', '财富管理部'
]

def clean_name(name):
    if not isinstance(name, str) or not name:
        return ""
    name = zhconv.convert(name, 'zh-cn')
    name = name.lower()
    name = re.sub(r'[\W_]+', '', name)
    return name

def strip_company_tail(name):
    if not name:
        return ""
    sorted_suffixes = sorted(SUFFIX_WORDS, key=len, reverse=True)
    for suffix in sorted_suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
        name = name.replace(suffix, '')
    return name

def is_fuzzy_match(name1, name2):
    c1 = clean_name(name1)
    c2 = clean_name(name2)
    if not c1 or not c2:
        return False
    if c1 == c2:
        return True
        
    s1 = strip_company_tail(c1)
    s2 = strip_company_tail(c2)
    
    if s1 == s2 and s1:
        return True
    
    if (s1 in s2 or s2 in s1) and min(len(s1), len(s2)) >= 2:
        return True
    return False

def any_fuzzy_match(db_org, rsc_orgs):
    for rsc_org in rsc_orgs:
        if is_fuzzy_match(db_org, rsc_org):
            return True
    return False

def parse_date(date_val):
    if pd.isna(date_val) or not date_val:
        return ""
    if isinstance(date_val, (int, float)):
        try:
            return datetime.fromtimestamp(date_val / 1000.0).strftime('%Y-%m-%d')
        except:
            return ""
    if isinstance(date_val, str):
        try:
            if len(date_val) == 4 and date_val.isdigit():
                return f"{date_val}-01-01"
            dt = pd.to_datetime(date_val)
            return dt.strftime('%Y-%m-%d')
        except:
            return ""
    if isinstance(date_val, datetime):
        return date_val.strftime('%Y-%m-%d')
    return ""

def get_org_names_by_oid(cursor, oid):
    names = []
    if not oid:
        return names
    cursor.execute("SELECT full_name, short_name, en_name, en_short_name, aliases FROM rsc_orgs WHERE oid = ?", (oid,))
    row = cursor.fetchone()
    if row:
        for val in row:
            if val:
                parts = str(val).replace('，', ',').split(',')
                names.extend([p.strip() for p in parts if p.strip()])
    return list(set(names))

def main():
    db_path = 'financial_scraper/financial_data.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("Fetching users from database...")
    # 仅查询分析师或机构投资者
    cursor.execute("SELECT * FROM rsc_users WHERE cert_type LIKE '%卖方分析师%' OR cert_type LIKE '%机构投资者%'")
    users = cursor.fetchall()
    print(f"Found {len(users)} target users.")
    
    outdated_users = []
    unmatched_users = []
    matched_rsc_users_for_db = []
    
    for user in users:
        uid = user['uid']
        name = user['name']
        if not name:
            continue
            
        cert_type = user['cert_type']
        oid = user['oid']
        rsc_org_main = user['org_name'] or ""
        rsc_org_full = user['org_full_name'] or ""
        rsc_cert_time = parse_date(user['cert_time'])
        
        # 组装待比对的机构名称集合
        rsc_orgs = get_org_names_by_oid(cursor, oid)
        if rsc_org_main and rsc_org_main not in rsc_orgs:
            rsc_orgs.append(rsc_org_main)
        if rsc_org_full and rsc_org_full not in rsc_orgs:
            rsc_orgs.append(rsc_org_full)
            
        cursor.execute("SELECT * FROM sac_practitioners WHERE name = ?", (name,))
        sac_rows = cursor.fetchall()
        
        cursor.execute("SELECT * FROM amac_practitioners WHERE name = ?", (name,))
        amac_rows = cursor.fetchall()
        
        if not sac_rows and not amac_rows:
            unmatched_users.append({
                'UID': uid,
                '姓名': name,
                '认证类型': cert_type,
                'RSC原机构': rsc_org_main,
                '机构OID': oid,
                '认证时间': rsc_cert_time,
                '未匹配原因': '数据库中查无此人'
            })
            continue
            
        matched_db_record = None
        source_type = None
        history = []
        
        for s_row in sac_rows:
            raw_data = json.loads(s_row['raw_data'])
            reg_hist = raw_data.get('regHistory') or []
            belongs = False
            parsed_hist = []
            for h in reg_hist:
                org = h.get('org_name', '')
                get_d = parse_date(h.get('get_date'))
                leave_d = parse_date(h.get('leave_date'))
                status = h.get('status', '')
                parsed_hist.append({
                    'org': org,
                    'start': get_d,
                    'end': leave_d,
                    'status': status
                })
                if any_fuzzy_match(org, rsc_orgs):
                    belongs = True
            
            if belongs:
                matched_db_record = s_row
                source_type = 'SAC'
                history = parsed_hist
                break
                
        if not matched_db_record:
            for a_row in amac_rows:
                raw_data = json.loads(a_row['raw_data'])
                cert_hist = raw_data.get('personCertHistoryList') or []
                belongs = False
                parsed_hist = []
                for h in cert_hist:
                    org = h.get('orgName', '')
                    get_d = parse_date(h.get('certObtainDate'))
                    leave_d = parse_date(h.get('certEndDate'))
                    status = h.get('statusName', '')
                    leave_d_str = "" if status == '正常' or not leave_d else leave_d
                    parsed_hist.append({
                        'org': org,
                        'start': get_d,
                        'end': leave_d_str,
                        'status': status
                    })
                    if any_fuzzy_match(org, rsc_orgs):
                        belongs = True
                        
                if belongs:
                    matched_db_record = a_row
                    source_type = 'AMAC'
                    history = parsed_hist
                    break
                    
        if not matched_db_record:
            unmatched_users.append({
                'UID': uid,
                '姓名': name,
                '认证类型': cert_type,
                'RSC原机构': rsc_org_main,
                '机构OID': oid,
                '认证时间': rsc_cert_time,
                '未匹配原因': '查到同名人员，但历史履历中均无此机构'
            })
            continue

        # 判断过期逻辑
        history.sort(key=lambda x: x['start'])
        latest_item = history[-1] if history else None
        if not latest_item:
            continue
            
        latest_org = latest_item['org']
        latest_start = latest_item['start']
        
        hist_strs = []
        for h in history:
            end_str = h['end'] if h['end'] else "present"
            hist_strs.append(f"{h['org']}({h['start']}~{end_str})")
        hist_detail = " -> ".join(hist_strs)
        
        is_outdated = False
        if not any_fuzzy_match(latest_org, rsc_orgs):
            if not rsc_cert_time or latest_start > rsc_cert_time:
                is_outdated = True
        else:
            if latest_item['end'] and latest_item['end'] != "present":
                if not rsc_cert_time or latest_item['end'] > rsc_cert_time:
                    is_outdated = True
        
        if is_outdated:
            practitioner_id = matched_db_record['practitioner_id']
            avatar_url = ""
            if source_type == 'SAC':
                raw_data = json.loads(matched_db_record['raw_data'])
                person_id = raw_data.get('RPI_ID') or raw_data.get('pti_id') or raw_data.get('raw_list_data', {}).get('uuid') or practitioner_id
                if raw_data.get('pti_id'):
                    url = f"https://exam.sac.net.cn/pages/registration/sac-publicity/finish-publicity.html?ptiID={person_id}"
                else:
                    url = f"https://gs.sac.net.cn/pages/registration/new-sac-finish-person.html?uuid={person_id}"
                photo_path = raw_data.get("photoPath")
                if photo_path:
                    avatar_url = f"https://gs.sac.net.cn/publicity/v2/regFile/downLoadUserPhoto?photoPath={photo_path}"
            else:
                raw_data = json.loads(matched_db_record['raw_data'])
                account_id = raw_data.get('accountId') or practitioner_id
                url = f"https://gs.amac.org.cn/amac-infodisc/res/pof/person/personDetail.html?accountId={account_id}"
                photo_b64 = raw_data.get("personPhotoBase64")
                if photo_b64:
                    avatar_url = f"data:image/jpeg;base64,{photo_b64}"
                    
            outdated_users.append({
                'UID': uid,
                '姓名': name,
                'RSC原机构': rsc_org_main,
                'RSC认证时间': rsc_cert_time,
                '人才库最新机构': latest_org,
                '人才库登记日期': latest_start,
                '官方查验URL': url,
                '头像URL': avatar_url,
                '任职记录历史明细': hist_detail
            })
            
        matched_rsc_users_for_db.append({
            'practitioner_id': matched_db_record['practitioner_id'],
            'rsc_uid': uid,
            'rsc_org': rsc_org_main,
            'rsc_cert_time': rsc_cert_time,
            'is_outdated': 1 if is_outdated else 0,
            'source_type': source_type
        })
        
    print(f"Found {len(matched_rsc_users_for_db)} matched users.")
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rsc_user_mapping (
        practitioner_id TEXT,
        source_type TEXT,
        rsc_uid TEXT,
        rsc_org TEXT,
        rsc_cert_time TEXT,
        is_outdated INTEGER,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (practitioner_id, source_type)
    )
    ''')
    
    for item in matched_rsc_users_for_db:
        cursor.execute('''
        INSERT INTO rsc_user_mapping (practitioner_id, source_type, rsc_uid, rsc_org, rsc_cert_time, is_outdated, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(practitioner_id, source_type) DO UPDATE SET
            rsc_uid=excluded.rsc_uid,
            rsc_org=excluded.rsc_org,
            rsc_cert_time=excluded.rsc_cert_time,
            is_outdated=excluded.is_outdated,
            updated_at=CURRENT_TIMESTAMP
        ''', (item['practitioner_id'], item['source_type'], item['rsc_uid'], item['rsc_org'], item['rsc_cert_time'], item['is_outdated']))
        
    conn.commit()
    conn.close()
    
    pd.DataFrame(outdated_users).to_excel('outdated_rsc_users.xlsx', index=False)
    pd.DataFrame(unmatched_users).to_excel('unmatched_rsc_users.xlsx', index=False)
    print("Done. Saved output files.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行比对脚本以验证**

Run: `python3 scripts/rsc_cross_check.py`
Expected: 成功连接数据库，拉取 `rsc_users` 数据，并使用新逻辑完成比对。控制台输出 "Done. Saved output files."

- [ ] **Step 3: Commit**

```bash
git add scripts/import_rsc_data.py scripts/rsc_cross_check.py
git commit -m "feat: refactor rsc matching engine using database and OID aliasing"
```