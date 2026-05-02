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