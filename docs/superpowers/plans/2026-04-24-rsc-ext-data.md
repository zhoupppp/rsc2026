# RSC 扩展数据导入 Implementation Plan (Phase 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将新版 RSC Excel 中除了基础信息以外的其他所有扩展 Sheet（如画像标签、管理规模、价值评分、人物简介等）导入 SQLite 数据库的主表（`rsc_users`, `rsc_orgs`）中。

**Architecture:** 
1. `scripts/import_rsc_ext_data.py`: 读取 `USER_FILE` 和 `ORG_FILE` 剩余的 Sheet，以 `uid` / `oid` 为主键，将核心扩展字段更新到表中，将零散标签等打包成 JSON 存入新增的 `ext_data` 列中。
2. 数据库迁移 (Migration)：如果原表没有扩展字段，需要先通过 `ALTER TABLE` 增加列。

**Tech Stack:** Python 3, Pandas, SQLite, json

---

### Task 1: 扩充数据库表结构

**Files:**
- Modify: `financial_scraper/financial_data.db`

- [ ] **Step 1: 编写更新数据库表结构的 Python 脚本**

创建 `scripts/migrate_rsc_tables.py`：

```python
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
```

- [ ] **Step 2: 运行迁移脚本**

Run: `python3 scripts/migrate_rsc_tables.py`
Expected: 成功添加字段，控制台输出 "Database migration completed."。

### Task 2: 编写扩展数据导入脚本 (Ext Data Ingestion)

**Files:**
- Create: `scripts/import_rsc_ext_data.py`

- [ ] **Step 1: 编写导入脚本**

创建 `scripts/import_rsc_ext_data.py`：

```python
import sqlite3
import pandas as pd
import os
import json

DB_PATH = 'financial_scraper/financial_data.db'
USER_FILE = 'rsc用户/RSC用户：完整信息_认证、名片、投研行业、行为偏好、价值标签 -26.04.24全部用户.xlsx'
ORG_FILE = 'rsc用户/RSC机构库：完整信息_基础、画像、标签 2025.09.xlsx'

def get_existing_ext_data(cursor, table, pk_col, pk_val):
    cursor.execute(f"SELECT ext_data FROM {table} WHERE {pk_col} = ?", (pk_val,))
    row = cursor.fetchone()
    if row and row[0]:
        try:
            return json.loads(row[0])
        except:
            return {}
    return {}

def update_user_ext(conn):
    print(f"Reading user extensions from {USER_FILE}...")
    xls = pd.ExcelFile(USER_FILE)
    cursor = conn.cursor()
    
    # 1. 人物简介
    if '人物简介' in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name='人物简介').fillna('')
        for _, row in df.iterrows():
            uid = str(row.get('用户UID', '')).strip()
            if not uid: continue
            
            cursor.execute('''
            UPDATE rsc_users SET
                gender = ?, intro = ?, birthday = ?, highest_edu = ?, university = ?, major = ?
            WHERE uid = ?
            ''', (
                str(row.get('性别', '')).strip(),
                str(row.get('个人介绍', '')).strip(),
                str(row.get('出生日期', '')).strip(),
                str(row.get('最高学历', '')).strip(),
                str(row.get('毕业院校', '')).strip(),
                str(row.get('所学专业', '')).strip(),
                uid
            ))
            
    # 2. 行为标签 (存入 ext_data JSON)
    if '画像标签(来自行为)' in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name='画像标签(来自行为)').fillna('')
        for _, row in df.iterrows():
            uid = str(row.get('UID', '')).strip()
            if not uid: continue
            
            ext = get_existing_ext_data(cursor, "rsc_users", "uid", uid)
            ext["behavior_tags"] = row.to_dict()
            cursor.execute("UPDATE rsc_users SET ext_data = ? WHERE uid = ?", (json.dumps(ext, ensure_ascii=False), uid))

    # 3. 价值标签
    if '价值标签' in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name='价值标签').fillna('')
        for _, row in df.iterrows():
            uid = str(row.get('uid', '')).strip()
            if not uid: continue
            
            ext = get_existing_ext_data(cursor, "rsc_users", "uid", uid)
            ext["value_tags"] = str(row.get('用户标签', '')).strip()
            cursor.execute("UPDATE rsc_users SET ext_data = ? WHERE uid = ?", (json.dumps(ext, ensure_ascii=False), uid))

    # 4. 投研行业
    if '投研行业(来自名片和获奖)' in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name='投研行业(来自名片和获奖)').fillna('')
        for _, row in df.iterrows():
            uid = str(row.get('uid', '')).strip()
            if not uid: continue
            
            ext = get_existing_ext_data(cursor, "rsc_users", "uid", uid)
            ext["research_industries"] = str(row.get('✅汇总投研行业（多选）', '')).strip()
            cursor.execute("UPDATE rsc_users SET ext_data = ? WHERE uid = ?", (json.dumps(ext, ensure_ascii=False), uid))

    conn.commit()
    print("User extensions updated.")

def update_org_ext(conn):
    print(f"Reading org extensions from {ORG_FILE}...")
    xls = pd.ExcelFile(ORG_FILE)
    cursor = conn.cursor()
    
    # 1. 管理规模
    if '管理规模' in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name='管理规模').fillna('')
        for _, row in df.iterrows():
            oid_val = row.get('机构OID', '')
            oid = str(int(oid_val)) if isinstance(oid_val, float) and pd.notna(oid_val) else str(oid_val).strip()
            if not oid: continue
            
            cursor.execute("UPDATE rsc_orgs SET aum = ? WHERE oid = ?", (str(row.get('管理规模(AUM)', '')).strip(), oid))

    # 2. 价值画像
    if '价值画像' in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name='价值画像').fillna('')
        for _, row in df.iterrows():
            oid_val = row.get('机构OID', '')
            oid = str(int(oid_val)) if isinstance(oid_val, float) and pd.notna(oid_val) else str(oid_val).strip()
            if not oid: continue
            
            cursor.execute('''
            UPDATE rsc_orgs SET
                value_score = ?, influence_score = ?, invest_position = ?, is_foreign = ?
            WHERE oid = ?
            ''', (
                str(row.get('✅ 价值评分', '')).strip(),
                str(row.get('✅影响力评分', '')).strip(),
                str(row.get('✅投资定位', '')).strip(),
                str(row.get('✅是否外资', '')).strip(),
                oid
            ))
            
    # 3. 机构标签
    if '机构标签' in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name='机构标签').fillna('')
        for _, row in df.iterrows():
            oid_val = row.get('机构OID', '')
            oid = str(int(oid_val)) if isinstance(oid_val, float) and pd.notna(oid_val) else str(oid_val).strip()
            if not oid: continue
            
            ext = get_existing_ext_data(cursor, "rsc_orgs", "oid", oid)
            ext["org_tags"] = str(row.get('机构标签', '')).strip()
            cursor.execute("UPDATE rsc_orgs SET ext_data = ? WHERE oid = ?", (json.dumps(ext, ensure_ascii=False), oid))

    conn.commit()
    print("Org extensions updated.")

def main():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}. Exiting.")
        return
    conn = sqlite3.connect(DB_PATH)
    update_user_ext(conn)
    update_org_ext(conn)
    conn.close()
    print("Extension data import completed.")

if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 运行导入脚本**

Run: `python3 scripts/import_rsc_ext_data.py`
Expected: 成功读取各个 Sheet 并更新表，控制台打印 "Extension data import completed."。