# 离线脚本（scripts/）

目录：[scripts/](file:///Users/zhoupeng/Documents/rsc2026/scripts)

该目录聚焦“离线数据加工”：导入 RSC 数据、迁移表结构、跨库对账与匹配、报表生成等。它通常在后端/前端运行前执行，用于构建或修复 SQLite 中的关键表。

## 1. RSC 数据导入

- [import_rsc_data.py](file:///Users/zhoupeng/Documents/rsc2026/scripts/import_rsc_data.py)
  - 从 Excel 导入 `rsc_users` 与 `rsc_orgs`
  - DB 默认：`financial_scraper/financial_data.db`（脚本内 `DB_PATH`）
  - 依赖：`pandas`（读取 Excel）

## 2. RSC 表结构迁移（扩展字段）

- [migrate_rsc_tables.py](file:///Users/zhoupeng/Documents/rsc2026/scripts/migrate_rsc_tables.py)
  - 为 `rsc_users/rsc_orgs` 增加后端检索与画像所需字段（`ext_data`、评分、AUM 等）

## 3. RSC ↔ SAC/AMAC 匹配与“待更新”检测

- [rsc_cross_check.py](file:///Users/zhoupeng/Documents/rsc2026/scripts/rsc_cross_check.py)
  - 从 `rsc_users`（特定 cert_type）筛选目标用户
  - 用姓名从 `sac_practitioners/amac_practitioners` 找同名候选
  - 解析人员历史履历：
    - SAC：`raw_data.regHistory`
    - AMAC：`raw_data.personCertHistoryList`
  - 与 RSC 的机构名称集合做模糊匹配（包含简繁转换、去后缀、包含判断等）
  - 生成：
    - `rsc_user_mapping`（后端用于“RSC 已认证”和“待更新”标记）
    - `outdated_rsc_users.xlsx`、`unmatched_rsc_users.xlsx`（人工复核用）
  - 依赖：`pandas`、`zhconv`

## 4. 其他脚本类型（目录内常见用途）

该仓库根目录与 `scripts/` 下还有大量一次性或修复脚本，例如：

- DB 检查/修复：`check_schema.py`、`update_db.py`、`patch_*`
- 报表生成：`generate_matched_report.py`
- 数据导入/对账：`import_rsc_ext_data.py`、`rsc_cross_check.py`

这些脚本多数是“项目演进过程中的运维/数据修补工具”，是否需要在正式流程中纳入自动化，需要结合当前数据生产方式做裁剪。

