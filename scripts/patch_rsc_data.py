import sqlite3
import json
import pandas as pd
import math

def safe_val(val):
    if pd.isna(val):
        return ""
    if isinstance(val, float) and math.isnan(val):
        return ""
    return str(val)

def safe_list(val):
    if pd.isna(val):
        return []
    if isinstance(val, float) and math.isnan(val):
        return []
    if isinstance(val, list):
        out = []
        for x in val:
            out.extend(safe_list(x))
        return out
    s = str(val).strip()
    if not s:
        return []
    for sep in [",", "，", "、", ";", "；", "|", "\n", "\t"]:
        s = s.replace(sep, ",")
    parts = [p.strip() for p in s.split(",")]
    return [p for p in parts if p]

def patch_data():
    db_path = '/Users/zhoupeng/Documents/rsc2026/financial_scraper/financial_data_v1.db'
    user_file = '/Users/zhoupeng/Documents/rsc2026/rsc用户/RSC用户：完整信息_认证、名片、投研行业、行为偏好、价值标签 -26.04.24全部用户.xlsx'
    org_file = '/Users/zhoupeng/Documents/rsc2026/rsc用户/RSC机构库：完整信息_基础、画像、标签 2025.09.xlsx'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Loading Excel files...")
    df_user_main = pd.read_excel(user_file, sheet_name='RSC全部用户')
    df_user_main['uid'] = df_user_main['uid'].astype(str)
    df_user_main = df_user_main.set_index('uid')
    
    df_user_behavior = pd.read_excel(user_file, sheet_name='画像标签(来自行为)')
    df_user_behavior['UID'] = df_user_behavior['UID'].astype(str)
    df_user_behavior = df_user_behavior.set_index('UID')
    
    df_user_industry = pd.read_excel(user_file, sheet_name='投研行业(来自名片和获奖)')
    df_user_industry['uid'] = df_user_industry['uid'].astype(str)
    df_user_industry = df_user_industry.set_index('uid')
    
    df_user_tags = pd.read_excel(user_file, sheet_name='价值标签')
    df_user_tags['uid'] = df_user_tags['uid'].astype(str)
    
    df_user_address = pd.read_excel(user_file, sheet_name='办公地址(来自名片)')
    df_user_address['uid'] = df_user_address['uid'].astype(str)
    df_user_address = df_user_address.set_index('uid')
    
    df_user_intro = pd.read_excel(user_file, sheet_name='人物简介')
    df_user_intro['用户UID'] = df_user_intro['用户UID'].astype(str)
    df_user_intro = df_user_intro.set_index('用户UID')
    
    df_org_main = pd.read_excel(org_file, sheet_name='基本信息')
    df_org_main['机构OID'] = df_org_main['机构OID'].astype(str)
    df_org_main = df_org_main.set_index('机构OID')
    
    df_org_scale = pd.read_excel(org_file, sheet_name='管理规模')
    df_org_scale['机构OID'] = df_org_scale['机构OID'].astype(str)
    df_org_scale = df_org_scale.set_index('机构OID')
    
    df_org_value = pd.read_excel(org_file, sheet_name='价值画像')
    df_org_value['机构OID'] = df_org_value['机构OID'].astype(str)
    df_org_value = df_org_value.set_index('机构OID')
    
    df_org_aux = pd.read_excel(org_file, sheet_name='辅助信息')
    df_org_aux['机构OID'] = df_org_aux['机构OID'].astype(str)
    df_org_aux = df_org_aux.set_index('机构OID')
    
    df_org_tags = pd.read_excel(org_file, sheet_name='机构标签')
    df_org_tags['机构OID'] = df_org_tags['机构OID'].astype(str)
    
    # Process Users
    print("Patching rsc_users...")
    cursor.execute("SELECT uid, ext_data FROM rsc_users")
    users = cursor.fetchall()
    
    user_tags_dict = df_user_tags.groupby('uid')['用户标签'].apply(list).to_dict()
    
    updated_users = 0
    for uid_tuple in users:
        uid = uid_tuple[0]
        ext_data_str = uid_tuple[1]
        ext_data = json.loads(ext_data_str) if ext_data_str else {}
        
        # Merge Main
        if uid in df_user_main.index:
            row = df_user_main.loc[uid]
            # Handle duplicate indices if any
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            ext_data['register_time'] = safe_val(row.get('注册时间'))
            ext_data['last_active_time'] = safe_val(row.get('最近活跃时间'))
            ext_data['org_type'] = safe_val(row.get('机构类型'))
            ext_data['cert_type'] = safe_val(row.get('认证类型'))
            ext_data['mobile_city'] = safe_val(row.get('手机城市'))
            ext_data['avatar_url'] = safe_val(row.get('头像URL'))
            ext_data['recent_follow_companies'] = safe_list(row.get('近期关注公司'))
            
        # Merge Behavior
        if uid in df_user_behavior.index:
            row = df_user_behavior.loc[uid]
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            ext_data['shenwan_1'] = safe_val(row.get('偏好行业(申万一级) 第1'))
            ext_data['shenwan_1_score'] = safe_val(row.get('偏好行业(申万一级) 第1_分值'))
            ext_data['shenwan_2'] = safe_val(row.get('偏好行业(申万一级) 第2'))
            ext_data['shenwan_2_score'] = safe_val(row.get('偏好行业(申万一级) 第2_分值'))
            ext_data['shenwan_3'] = safe_val(row.get('偏好行业(申万一级) 第3'))
            ext_data['shenwan_3_score'] = safe_val(row.get('偏好行业(申万一级) 第3_分值'))
            ext_data['pref_theme'] = safe_val(row.get('偏好主题'))
            ext_data['pref_track'] = safe_val(row.get('偏好赛道'))
            
        # Merge Industry
        if uid in df_user_industry.index:
            row = df_user_industry.loc[uid]
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            ext_data['agg_research_industry'] = safe_val(row.get('✅汇总投研行业（多选）'))
            
        # Merge Tags
        if uid in user_tags_dict:
            ext_data['value_tags'] = user_tags_dict[uid]
            
        # Merge Address
        if uid in df_user_address.index:
            row = df_user_address.loc[uid]
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            ext_data['office_address'] = safe_val(row.get('办公地址'))
            ext_data['office_country'] = safe_val(row.get('办公-国家地区'))
            ext_data['office_province'] = safe_val(row.get('办公-省份'))
            ext_data['office_city'] = safe_val(row.get('办公-城市'))
            ext_data['mobile_country'] = safe_val(row.get('手机-国家地区'))
            ext_data['mobile_province'] = safe_val(row.get('手机-省份'))
            
        # Merge Intro
        if uid in df_user_intro.index:
            row = df_user_intro.loc[uid]
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            ext_data['personal_intro'] = safe_val(row.get('个人介绍'))
            
        cursor.execute("UPDATE rsc_users SET ext_data = ? WHERE uid = ?", (json.dumps(ext_data, ensure_ascii=False), uid))
        updated_users += 1
        
    print(f"Patched {updated_users} users.")

    # Process Orgs
    print("Patching rsc_orgs...")
    cursor.execute("SELECT oid, ext_data FROM rsc_orgs")
    orgs = cursor.fetchall()
    
    org_tags_dict = df_org_tags.groupby('机构OID')['机构标签'].apply(list).to_dict()
    
    updated_orgs = 0
    for oid_tuple in orgs:
        oid = oid_tuple[0]
        ext_data_str = oid_tuple[1]
        ext_data = json.loads(ext_data_str) if ext_data_str else {}
        
        # Merge Main
        if oid in df_org_main.index:
            row = df_org_main.loc[oid]
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            ext_data['region'] = safe_val(row.get('国家地区'))
            ext_data['logo'] = safe_val(row.get('机构logo'))
            ext_data['amac_website'] = safe_val(row.get('中基协备案公示网站'))
            ext_data['website'] = safe_val(row.get('官网'))
            ext_data['email'] = safe_val(row.get('机构邮箱'))
            
        # Merge Scale
        if oid in df_org_scale.index:
            row = df_org_scale.loc[oid]
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            ext_data['org_group'] = safe_val(row.get('机构分组'))
            ext_data['org_subtype'] = safe_val(row.get('机构子类型'))
            ext_data['aum'] = safe_val(row.get('管理规模(AUM)'))
            ext_data['office_location'] = safe_val(row.get('办公地点'))
            
        # Merge Value
        if oid in df_org_value.index:
            row = df_org_value.loc[oid]
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            ext_data['one_sentence_pos'] = safe_val(row.get('一句话定位✨'))
            ext_data['core_figures'] = safe_val(row.get('核心人物✨'))
            ext_data['value_score_desc'] = safe_val(row.get('✅价值评分描述'))
            ext_data['influence_score_desc'] = safe_val(row.get('✅影响力评分描述') or row.get('✅影响力评分理由') or row.get('影响力评分理由'))
            ext_data['invest_pos'] = safe_val(row.get('✅投资定位'))
            ext_data['invest_style'] = safe_val(row.get('✅投资风格'))
            ext_data['is_foreign'] = safe_val(row.get('✅是否外资'))
            
        # Merge Aux
        if oid in df_org_aux.index:
            row = df_org_aux.loc[oid]
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            ext_data['org_intro'] = safe_val(row.get('机构简介'))
            ext_data['rsc_profile_url'] = safe_val(row.get('🔚 || 机构档案RSC'))
            
        # Merge Tags
        if oid in org_tags_dict:
            ext_data['org_tags'] = org_tags_dict[oid]
            
        cursor.execute("UPDATE rsc_orgs SET ext_data = ? WHERE oid = ?", (json.dumps(ext_data, ensure_ascii=False), oid))
        updated_orgs += 1
        
    conn.commit()
    conn.close()
    print(f"Patched {updated_orgs} orgs.")
    print("Patch complete.")

if __name__ == "__main__":
    patch_data()
