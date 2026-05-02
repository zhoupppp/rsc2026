import pandas as pd
import json

user_file = "/Users/zhoupeng/Documents/rsc2026/rsc用户/RSC用户：完整信息_认证、名片、投研行业、行为偏好、价值标签 -26.04.24全部用户.xlsx"
org_file = "/Users/zhoupeng/Documents/rsc2026/rsc用户/RSC机构库：完整信息_基础、画像、标签 2025.09.xlsx"

user_xl = pd.ExcelFile(user_file)
org_xl = pd.ExcelFile(org_file)

print("User Sheets:", user_xl.sheet_names)
print("Org Sheets:", org_xl.sheet_names)

for sheet in user_xl.sheet_names:
    print(f"\nUser Sheet '{sheet}' Columns:")
    print(list(pd.read_excel(user_file, sheet_name=sheet, nrows=0).columns))
    
for sheet in org_xl.sheet_names:
    print(f"\nOrg Sheet '{sheet}' Columns:")
    print(list(pd.read_excel(org_file, sheet_name=sheet, nrows=0).columns))
