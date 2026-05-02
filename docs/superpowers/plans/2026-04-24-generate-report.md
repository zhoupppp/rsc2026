# 综合检查报表生成 Implementation Plan (Phase 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 开发一个独立的脚本，读取 SQLite 数据库中所有已匹配的 RSC 用户信息（无论是否过期），重新解析其在 SAC/AMAC 爬虫数据中的履历，并生成一份单列展示完整履历和最新状态的综合 Excel 报表，供人工审查。

**Architecture:** 
1. `scripts/generate_matched_report.py`: 连接 `financial_scraper/financial_data.db`，读取 `rsc_user_mapping`、`rsc_users` 以及对应的 `sac_practitioners` / `amac_practitioners`。提取履历、组装 URL、格式化输出到 `matched_rsc_users_report.xlsx`。

**Tech Stack:** Python 3, Pandas, SQLite, json

---

### Task 1: 编写报表生成脚本 (Report Generation)

**Files:**
- Create: `scripts/generate_matched_report.py`

- [ ] **Step 1: 编写生成脚本**

创建 `scripts/generate_matched_report.py`：

```python
import sqlite3
import pandas as pd
import json
import os
from datetime import datetime

DB_PATH = 'financial_scraper/financial_data.db'

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

def main():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}.")
        return
        
    print("Connecting to database to generate matched report...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 联表查询所有已匹配的用户
    query = '''
    SELECT 
        m.rsc_uid, m.rsc_org, m.rsc_cert_time, m.is_outdated, m.practitioner_id, m.source_type,
        u.name, u.cert_type
    FROM rsc_user_mapping m
    LEFT JOIN rsc_users u ON m.rsc_uid = u.uid
    '''
    cursor.execute(query)
    mappings = cursor.fetchall()
    print(f"Found {len(mappings)} matched user records.")
    
    report_data = []
    
    for row in mappings:
        uid = row['rsc_uid']
        name = row['name'] or ""
        cert_type = row['cert_type'] or ""
        rsc_org = row['rsc_org'] or ""
        rsc_cert_time = row['rsc_cert_time'] or ""
        is_outdated = True if row['is_outdated'] == 1 else False
        practitioner_id = row['practitioner_id']
        source_type = row['source_type']
        
        history = []
        avatar_url = ""
        url = ""
        
        if source_type == 'SAC':
            cursor.execute("SELECT raw_data FROM sac_practitioners WHERE practitioner_id = ?", (practitioner_id,))
            sac_row = cursor.fetchone()
            if sac_row and sac_row['raw_data']:
                raw_data = json.loads(sac_row['raw_data'])
                reg_hist = raw_data.get('regHistory') or []
                for h in reg_hist:
                    history.append({
                        'org': h.get('org_name', ''),
                        'start': parse_date(h.get('get_date')),
                        'end': parse_date(h.get('leave_date'))
                    })
                
                person_id = raw_data.get('RPI_ID') or raw_data.get('pti_id') or raw_data.get('raw_list_data', {}).get('uuid') or practitioner_id
                if raw_data.get('pti_id'):
                    url = f"https://exam.sac.net.cn/pages/registration/sac-publicity/finish-publicity.html?ptiID={person_id}"
                else:
                    url = f"https://gs.sac.net.cn/pages/registration/new-sac-finish-person.html?uuid={person_id}"
                photo_path = raw_data.get("photoPath")
                if photo_path:
                    avatar_url = f"https://gs.sac.net.cn/publicity/v2/regFile/downLoadUserPhoto?photoPath={photo_path}"
                    
        elif source_type == 'AMAC':
            cursor.execute("SELECT raw_data FROM amac_practitioners WHERE practitioner_id = ?", (practitioner_id,))
            amac_row = cursor.fetchone()
            if amac_row and amac_row['raw_data']:
                raw_data = json.loads(amac_row['raw_data'])
                cert_hist = raw_data.get('personCertHistoryList') or []
                for h in cert_hist:
                    status = h.get('statusName', '')
                    leave_d = parse_date(h.get('certEndDate'))
                    leave_d_str = "" if status == '正常' or not leave_d else leave_d
                    history.append({
                        'org': h.get('orgName', ''),
                        'start': parse_date(h.get('certObtainDate')),
                        'end': leave_d_str
                    })
                    
                account_id = raw_data.get('accountId') or practitioner_id
                url = f"https://gs.amac.org.cn/amac-infodisc/res/pof/person/personDetail.html?accountId={account_id}"
                photo_b64 = raw_data.get("personPhotoBase64")
                if photo_b64:
                    avatar_url = f"data:image/jpeg;base64,{photo_b64}"
        
        # 整理履历和最新任职
        history.sort(key=lambda x: x['start'])
        latest_org = ""
        latest_start = ""
        hist_detail = ""
        
        if history:
            latest_item = history[-1]
            latest_org = latest_item['org']
            latest_start = latest_item['start']
            
            hist_strs = []
            for h in history:
                end_str = h['end'] if h['end'] else "present"
                hist_strs.append(f"{h['org']}({h['start']}~{end_str})")
            hist_detail = " -> ".join(hist_strs)
            
        report_data.append({
            'UID': uid,
            '姓名': name,
            '认证类型': cert_type,
            'RSC原机构': rsc_org,
            'RSC认证时间': rsc_cert_time,
            '是否待更新(跳槽/离职)': "是" if is_outdated else "否",
            '最新任职机构': latest_org,
            '最新任职日期': latest_start,
            '任职履历明细': hist_detail,
            '官方查验URL': url,
            '头像URL': avatar_url
        })
        
    conn.close()
    
    out_file = 'matched_rsc_users_report.xlsx'
    pd.DataFrame(report_data).to_excel(out_file, index=False)
    print(f"Done. Generated comprehensive report for {len(report_data)} matched users: {out_file}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行报表生成脚本**

Run: `python3 scripts/generate_matched_report.py`
Expected: 连接数据库读取所有已匹配用户，并在根目录生成 `matched_rsc_users_report.xlsx`。

- [ ] **Step 3: Commit (如需)**

```bash
git add scripts/generate_matched_report.py
git commit -m "feat: add comprehensive report generator for matched rsc users"
```