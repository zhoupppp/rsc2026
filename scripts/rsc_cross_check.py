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
    
    with open('cross_check.log', 'a') as logf:
        logf.write("Fetching users from database...\n")
        logf.flush()
    print("Fetching users from database...", flush=True)
    # 仅查询分析师或机构投资者
    cursor.execute("SELECT * FROM rsc_users WHERE cert_type LIKE '%卖方分析师%' OR cert_type LIKE '%机构投资者%'")
    users = cursor.fetchall()
    
    with open('cross_check.log', 'a') as logf:
        logf.write(f"Found {len(users)} target users.\n")
        logf.flush()
    print(f"Found {len(users)} target users.", flush=True)
    
    outdated_users = []
    unmatched_users = []
    matched_rsc_users_for_db = []
    
    for i, user in enumerate(users):
        if i % 1000 == 0:
            with open('cross_check.log', 'a') as logf:
                logf.write(f"Processed {i} users...\n")
                logf.flush()
            print(f"Processed {i} users...", flush=True)
            
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
    with open('cross_check.log', 'a') as logf:
        logf.write("Done. Saved output files.\n")
        logf.flush()
    print("Done. Saved output files.")

if __name__ == "__main__":
    main()