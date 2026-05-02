import pandas as pd
import json

user_file = "/Users/zhoupeng/Documents/rsc2026/rsc用户/RSC用户：完整信息_认证、名片、投研行业、行为偏好、价值标签 -26.04.24全部用户.xlsx"
org_file = "/Users/zhoupeng/Documents/rsc2026/rsc用户/RSC机构库：完整信息_基础、画像、标签 2025.09.xlsx"

def print_unique_values(file_path, sheet_name, column_name):
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    if column_name in df.columns:
        # If it's a comma-separated field, we should split it
        all_vals = []
        for val in df[column_name].dropna():
            for v in str(val).split(','):
                if v.strip():
                    all_vals.append(v.strip())
        unique_vals = sorted(list(set(all_vals)))
        print(f"\n--- {sheet_name} : {column_name} ---")
        for val in unique_vals:
            print(val)
    else:
        print(f"Column '{column_name}' not found in sheet '{sheet_name}'")

print_unique_values(org_file, '管理规模', '机构分组')
print_unique_values(org_file, '管理规模', '机构子类型')
print_unique_values(user_file, '画像标签(来自行为)', '偏好主题')
print_unique_values(user_file, '画像标签(来自行为)', '偏好赛道')
print_unique_values(user_file, '投研行业(来自名片和获奖)', '✅汇总投研行业（多选）')