import pandas as pd
import json

user_file = "/Users/zhoupeng/Documents/rsc2026/rsc用户/RSC用户：完整信息_认证、名片、投研行业、行为偏好、价值标签 -26.04.24全部用户.xlsx"
org_file = "/Users/zhoupeng/Documents/rsc2026/rsc用户/RSC机构库：完整信息_基础、画像、标签 2025.09.xlsx"

def print_unique_values(file_path, sheet_name, column_name):
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    if column_name in df.columns:
        unique_vals = df[column_name].dropna().unique()
        print(f"\n--- {sheet_name} : {column_name} ---")
        for val in unique_vals:
            print(val)
    else:
        print(f"Column '{column_name}' not found in sheet '{sheet_name}'")

print_unique_values(user_file, 'RSC全部用户20260424', '机构类型')
print_unique_values(user_file, 'RSC全部用户20260424', '认证类型')
print_unique_values(user_file, '画像标签(来自行为)', '偏好行业(申万一级) 第1')

print_unique_values(org_file, '基本信息', '国家地区')
print_unique_values(org_file, '价值画像', '✅是否外资')
