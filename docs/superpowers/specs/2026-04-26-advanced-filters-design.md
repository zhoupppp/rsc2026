## Update to Brainstorming Context

The user's requested data fields are indeed present in the provided `.xlsx` files (`RSC用户：完整信息_认证、名片、投研行业、行为偏好、价值标签 -26.04.24全部用户.xlsx` and `RSC机构库：完整信息_基础、画像、标签 2025.09.xlsx`), distributed across multiple sheets.

However, the SQLite database (`financial_data_v1.db`) we currently use only has a subset of these fields in `rsc_users` and `rsc_orgs` tables, mostly stored in the `ext_data` JSON column. 

**Critical Decision**: Before we can build the frontend filters and detail page, we *must* update the data pipeline (the SQLite database). 
Option 1: Re-import everything from the Excel files into the SQLite database.
Option 2: Write a Python script to patch the existing SQLite database by reading the missing columns from the Excel files and updating the `ext_data` JSON columns.

Given we are working with `financial_data_v1.db` and the user wants to see this immediately, patching the database with the new fields from the Excel files is the necessary first step.

### Step 1: Data Pipeline Patch (Backend)
Write a script `scripts/patch_rsc_data.py` that:
1. Loads all sheets from the two Excel files.
2. For each `uid` in `rsc_users`, extracts the new fields:
   - From "RSC全部用户20260424": `注册时间`, `最近活跃时间`, `机构类型`, `认证类型`
   - From "画像标签(来自行为)": `偏好行业(申万一级) 第1`, `第1_分值`, `第2`, `第2_分值`, `第3`, `第3_分值`
   - From "投研行业(来自名片和获奖)": `✅汇总投研行业（多选）`
   - From "价值标签": `用户标签` (group by uid)
   - From "办公地址(来自名片)": `办公地址`, `办公-国家地区`, `办公-省份`, `办公-城市`, `手机-国家地区`, `手机-省份`
   - From "人物简介": `个人介绍`
3. Updates `rsc_users.ext_data` JSON with these new fields.
4. For each `oid` in `rsc_orgs`, extracts:
   - From "基本信息": `国家地区`, `机构logo`, `中基协备案公示网站`, `官网`, `机构邮箱`
   - From "管理规模": `机构分组`, `机构子类型`, `管理规模(AUM)`, `办公地点`
   - From "价值画像": `一句话定位✨`, `核心人物✨`, `✅价值评分描述`, `✅投资定位`, `✅投资风格`, `✅是否外资`
   - From "辅助信息": `机构简介`, `🔚 || 机构档案RSC`
   - From "机构标签": `机构标签` (group by oid)
5. Updates `rsc_orgs.ext_data` JSON with these new fields.

### Step 2: Backend API Update (`main.py`)
Update `/api/rsc/experts` to parse the new `ext_data` keys and support filtering by them. Since building 20 memory indices is inefficient and complex, we should refactor `/api/rsc/experts` to use SQLite's `json_extract()` for filtering directly, or build specific indices for the most common ones and use `json_extract()` for the rest.

### Step 3: Frontend Home Page UI
Implement a "Advanced Filters" (高级筛选) Drawer/Panel using Shadcn UI's `Collapsible` or a custom sliding panel below the search bar. This panel will contain all 20+ filter dropdowns/selects.

### Step 4: Frontend Detail Page UI
Expand the right column (which we just built) into sections:
- User Info Section
- Org Portrait Section
Render all the new fields beautifully with standard labels and values.
