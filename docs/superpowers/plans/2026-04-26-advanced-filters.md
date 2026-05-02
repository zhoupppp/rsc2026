# Advanced Filters & Full Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Patch the SQLite database with 20+ missing advanced data fields from Excel, update the backend APIs to serve and filter these fields, and implement a collapsible advanced filter UI + expanded detail view on the frontend.

**Architecture:** 
1. `scripts/patch_rsc_data.py`: A one-off Python script using `pandas` to read `.xlsx` files, extract new columns, and merge them into the existing `ext_data` JSON column in SQLite.
2. `backend/main.py`: Expand the `search_rsc_experts` and `get_talent_detail` endpoints to extract the new JSON fields and build dynamic `WHERE json_extract(...)` clauses.
3. `frontend/src/app/page.tsx`: Add a Shadcn UI Collapsible panel for advanced filtering and expand the detail page's right column to display the new sections.

**Tech Stack:** Python, Pandas, SQLite, FastAPI, Next.js, React, Tailwind CSS

---

### Task 1: Patch SQLite Database with Missing Excel Fields

**Files:**
- Create: `scripts/patch_rsc_data.py`

- [ ] **Step 1: Write the patching script**

```python
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

def patch_data():
    db_path = '/Users/zhoupeng/Documents/rsc2026/financial_scraper/financial_data_v1.db'
    user_file = '/Users/zhoupeng/Documents/rsc2026/rsc用户/RSC用户：完整信息_认证、名片、投研行业、行为偏好、价值标签 -26.04.24全部用户.xlsx'
    org_file = '/Users/zhoupeng/Documents/rsc2026/rsc用户/RSC机构库：完整信息_基础、画像、标签 2025.09.xlsx'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Loading Excel files...")
    df_user_main = pd.read_excel(user_file, sheet_name='RSC全部用户20260424')
    df_user_behavior = pd.read_excel(user_file, sheet_name='画像标签(来自行为)')
    df_user_industry = pd.read_excel(user_file, sheet_name='投研行业(来自名片和获奖)')
    df_user_tags = pd.read_excel(user_file, sheet_name='价值标签')
    df_user_address = pd.read_excel(user_file, sheet_name='办公地址(来自名片)')
    df_user_intro = pd.read_excel(user_file, sheet_name='人物简介')
    
    df_org_main = pd.read_excel(org_file, sheet_name='基本信息')
    df_org_scale = pd.read_excel(org_file, sheet_name='管理规模')
    df_org_value = pd.read_excel(org_file, sheet_name='价值画像')
    df_org_aux = pd.read_excel(org_file, sheet_name='辅助信息')
    df_org_tags = pd.read_excel(org_file, sheet_name='机构标签')
    
    # Process Users
    print("Patching rsc_users...")
    cursor.execute("SELECT uid, ext_data FROM rsc_users")
    users = cursor.fetchall()
    
    user_tags_dict = df_user_tags.groupby('uid')['用户标签'].apply(list).to_dict()
    
    for uid_tuple in users:
        uid = uid_tuple[0]
        ext_data_str = uid_tuple[1]
        ext_data = json.loads(ext_data_str) if ext_data_str else {}
        
        # Merge Main
        main_row = df_user_main[df_user_main['uid'] == uid]
        if not main_row.empty:
            row = main_row.iloc[0]
            ext_data['register_time'] = safe_val(row.get('注册时间'))
            ext_data['last_active_time'] = safe_val(row.get('最近活跃时间'))
            ext_data['org_type'] = safe_val(row.get('机构类型'))
            ext_data['cert_type'] = safe_val(row.get('认证类型'))
            
        # Merge Behavior
        beh_row = df_user_behavior[df_user_behavior['UID'] == uid]
        if not beh_row.empty:
            row = beh_row.iloc[0]
            ext_data['shenwan_1'] = safe_val(row.get('偏好行业(申万一级) 第1'))
            ext_data['shenwan_1_score'] = safe_val(row.get('偏好行业(申万一级) 第1_分值'))
            ext_data['shenwan_2'] = safe_val(row.get('偏好行业(申万一级) 第2'))
            ext_data['shenwan_2_score'] = safe_val(row.get('偏好行业(申万一级) 第2_分值'))
            ext_data['shenwan_3'] = safe_val(row.get('偏好行业(申万一级) 第3'))
            ext_data['shenwan_3_score'] = safe_val(row.get('偏好行业(申万一级) 第3_分值'))
            ext_data['pref_theme'] = safe_val(row.get('偏好主题'))
            ext_data['pref_track'] = safe_val(row.get('偏好赛道'))
            
        # Merge Industry
        ind_row = df_user_industry[df_user_industry['uid'] == uid]
        if not ind_row.empty:
            ext_data['agg_research_industry'] = safe_val(ind_row.iloc[0].get('✅汇总投研行业（多选）'))
            
        # Merge Tags
        if uid in user_tags_dict:
            ext_data['value_tags'] = user_tags_dict[uid]
            
        # Merge Address
        add_row = df_user_address[df_user_address['uid'] == uid]
        if not add_row.empty:
            row = add_row.iloc[0]
            ext_data['office_address'] = safe_val(row.get('办公地址'))
            ext_data['office_country'] = safe_val(row.get('办公-国家地区'))
            ext_data['office_province'] = safe_val(row.get('办公-省份'))
            ext_data['office_city'] = safe_val(row.get('办公-城市'))
            ext_data['mobile_country'] = safe_val(row.get('手机-国家地区'))
            ext_data['mobile_province'] = safe_val(row.get('手机-省份'))
            
        # Merge Intro
        intro_row = df_user_intro[df_user_intro['用户UID'] == uid]
        if not intro_row.empty:
            ext_data['personal_intro'] = safe_val(intro_row.iloc[0].get('个人介绍'))
            
        cursor.execute("UPDATE rsc_users SET ext_data = ? WHERE uid = ?", (json.dumps(ext_data, ensure_ascii=False), uid))
        
    # Process Orgs
    print("Patching rsc_orgs...")
    cursor.execute("SELECT oid, ext_data FROM rsc_orgs")
    orgs = cursor.fetchall()
    
    org_tags_dict = df_org_tags.groupby('机构OID')['机构标签'].apply(list).to_dict()
    
    for oid_tuple in orgs:
        oid = oid_tuple[0]
        ext_data_str = oid_tuple[1]
        ext_data = json.loads(ext_data_str) if ext_data_str else {}
        
        # Merge Main
        main_row = df_org_main[df_org_main['机构OID'] == oid]
        if not main_row.empty:
            row = main_row.iloc[0]
            ext_data['region'] = safe_val(row.get('国家地区'))
            ext_data['logo'] = safe_val(row.get('机构logo'))
            ext_data['amac_website'] = safe_val(row.get('中基协备案公示网站'))
            ext_data['website'] = safe_val(row.get('官网'))
            ext_data['email'] = safe_val(row.get('机构邮箱'))
            
        # Merge Scale
        scale_row = df_org_scale[df_org_scale['机构OID'] == oid]
        if not scale_row.empty:
            row = scale_row.iloc[0]
            ext_data['org_group'] = safe_val(row.get('机构分组'))
            ext_data['org_subtype'] = safe_val(row.get('机构子类型'))
            ext_data['aum'] = safe_val(row.get('管理规模(AUM)'))
            ext_data['office_location'] = safe_val(row.get('办公地点'))
            
        # Merge Value
        val_row = df_org_value[df_org_value['机构OID'] == oid]
        if not val_row.empty:
            row = val_row.iloc[0]
            ext_data['one_sentence_pos'] = safe_val(row.get('一句话定位✨'))
            ext_data['core_figures'] = safe_val(row.get('核心人物✨'))
            ext_data['value_score_desc'] = safe_val(row.get('✅价值评分描述'))
            ext_data['invest_pos'] = safe_val(row.get('✅投资定位'))
            ext_data['invest_style'] = safe_val(row.get('✅投资风格'))
            ext_data['is_foreign'] = safe_val(row.get('✅是否外资'))
            
        # Merge Aux
        aux_row = df_org_aux[df_org_aux['机构OID'] == oid]
        if not aux_row.empty:
            row = aux_row.iloc[0]
            ext_data['org_intro'] = safe_val(row.get('机构简介'))
            ext_data['rsc_profile_url'] = safe_val(row.get('🔚 || 机构档案RSC'))
            
        # Merge Tags
        if oid in org_tags_dict:
            ext_data['org_tags'] = org_tags_dict[oid]
            
        cursor.execute("UPDATE rsc_orgs SET ext_data = ? WHERE oid = ?", (json.dumps(ext_data, ensure_ascii=False), oid))
        
    conn.commit()
    conn.close()
    print("Patch complete.")

if __name__ == "__main__":
    patch_data()
```

- [ ] **Step 2: Run the script to update the database**

```bash
/Users/zhoupeng/Documents/rsc2026/backend/venv/bin/python /Users/zhoupeng/Documents/rsc2026/scripts/patch_rsc_data.py
```

### Task 2: Update Backend APIs for Advanced Filtering

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Expand `/api/rsc/experts` to accept and process new filter parameters using `json_extract`**

```python
# In backend/main.py, update the search_rsc_experts signature
@app.get("/api/rsc/experts")
def search_rsc_experts(
    query: str = "",
    tags: str = "",
    aum: str = "",
    is_matched: Optional[bool] = None,
    is_outdated: Optional[bool] = None,
    adv_org_type: str = "",
    adv_cert_type: str = "",
    adv_shenwan_1: str = "",
    adv_region: str = "",
    adv_is_foreign: str = "",
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    # ... inside the function, append where clauses for advanced filters
    if adv_org_type:
        where_clauses.append("json_extract(u.ext_data, '$.org_type') = ?")
        params.append(adv_org_type)
        
    if adv_cert_type:
        where_clauses.append("json_extract(u.ext_data, '$.cert_type') = ?")
        params.append(adv_cert_type)
        
    if adv_shenwan_1:
        where_clauses.append("json_extract(u.ext_data, '$.shenwan_1') = ?")
        params.append(adv_shenwan_1)
        
    if adv_region:
        where_clauses.append("json_extract(o.ext_data, '$.region') = ?")
        params.append(adv_region)
        
    if adv_is_foreign:
        where_clauses.append("json_extract(o.ext_data, '$.is_foreign') = ?")
        params.append(adv_is_foreign)
```

- [ ] **Step 2: Ensure `get_talent_detail` passes all the new `ext_data` keys to the frontend**

```python
# In backend/main.py, get_talent_detail for RSC source
        user_ext = {}
        if row["ext_data"]:
            try:
                user_ext = json.loads(row["ext_data"])
            except:
                pass
                
        org_ext = {}
        # Need to fetch o.ext_data as org_ext_data in the SQL query first!
        # Change SELECT u.*, o.value_score ... to SELECT u.*, o.value_score ..., o.ext_data as org_ext_data
        if row["org_ext_data"]:
            try:
                org_ext = json.loads(row["org_ext_data"])
            except:
                pass

        profile["rsc_info"].update({
            "intro": str(user_ext.get("personal_intro") or row["intro"] or ""),
            "highest_edu": str(row["highest_edu"] or ""),
            "university": str(row["university"] or ""),
            "behavior_tags": user_ext.get("behavior_tags", {}),
            "research_industries": user_ext.get("research_industries", []),
            "org_value_score": row["value_score"],
            "org_influence_score": row["influence_score"],
            "org_aum": row["aum"],
            
            # New Advanced Fields
            "register_time": user_ext.get("register_time", ""),
            "last_active_time": user_ext.get("last_active_time", ""),
            "org_type": user_ext.get("org_type", ""),
            "cert_type": user_ext.get("cert_type", ""),
            "shenwan_1": user_ext.get("shenwan_1", ""),
            "shenwan_1_score": user_ext.get("shenwan_1_score", ""),
            "shenwan_2": user_ext.get("shenwan_2", ""),
            "shenwan_2_score": user_ext.get("shenwan_2_score", ""),
            "shenwan_3": user_ext.get("shenwan_3", ""),
            "shenwan_3_score": user_ext.get("shenwan_3_score", ""),
            "pref_theme": user_ext.get("pref_theme", ""),
            "pref_track": user_ext.get("pref_track", ""),
            "value_tags": user_ext.get("value_tags", []),
            "agg_research_industry": user_ext.get("agg_research_industry", ""),
            "office_address": user_ext.get("office_address", ""),
            "office_country": user_ext.get("office_country", ""),
            "office_province": user_ext.get("office_province", ""),
            "office_city": user_ext.get("office_city", ""),
            "mobile_country": user_ext.get("mobile_country", ""),
            "mobile_province": user_ext.get("mobile_province", ""),
            
            # New Org Fields
            "org_region": org_ext.get("region", ""),
            "org_group": org_ext.get("org_group", ""),
            "org_subtype": org_ext.get("org_subtype", ""),
            "org_office_location": org_ext.get("office_location", ""),
            "org_is_foreign": org_ext.get("is_foreign", ""),
            "org_tags": org_ext.get("org_tags", []),
            "org_logo": org_ext.get("logo", ""),
            "org_amac_website": org_ext.get("amac_website", ""),
            "org_website": org_ext.get("website", ""),
            "org_email": org_ext.get("email", ""),
            "org_one_sentence_pos": org_ext.get("one_sentence_pos", ""),
            "org_core_figures": org_ext.get("core_figures", ""),
            "org_value_score_desc": org_ext.get("value_score_desc", ""),
            "org_invest_pos": org_ext.get("invest_pos", ""),
            "org_invest_style": org_ext.get("invest_style", ""),
            "org_intro": org_ext.get("org_intro", ""),
            "org_rsc_profile_url": org_ext.get("rsc_profile_url", "")
        })
```

### Task 3: Frontend Home Page - Advanced Filters Collapsible

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Add new filter state variables for RSC engine**
Add states like `advOrgType`, `advCertType`, `advShenwan`, `advRegion`, `advIsForeign`.
Update `buildSearchUrl` to append these parameters.

- [ ] **Step 2: Build the Collapsible Panel Component**
Add a "高级筛选" (Advanced Filters) toggle button next to the standard filters in `RSCFilterBar`.
When expanded, display a grid layout with dropdowns/inputs for the new fields.

### Task 4: Frontend Detail Page - Display Expanded Information

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Expand the RSC User Info Section**
In the right column, under the active Tab "机构与全景档案", update the "用户全景信息" section to include the newly fetched fields (register_time, active_time, shenwan_1 with score, pref_theme, value_tags, office/mobile geo-data).

- [ ] **Step 2: Expand the Org Portrait Section**
Update the "机构信息" section to include Region, Org group, subtype, AUM, Office location, Is foreign, Org tags.
Add "机构画像" (Org Portrait) sub-section showing the one-sentence positioning, core figures, investment positioning, and investment style.
Add tooltips (`title` attribute or custom tooltip component) for the value score description.
Add an external link for the RSC Profile URL if available.
