# 数据库与表结构（SQLite）

## 1. 数据库文件与用途

仓库内存在多套脚本/服务对不同 DB 文件名的引用（需要在实际运行时统一）：

- 后端默认读取：`financial_scraper/financial_data_v1.db`  
  - 定义：[backend/main.py:L25-L29](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L25-L29)
- 部分离线脚本读取：`financial_scraper/financial_data.db`  
  - 示例：[import_rsc_data.py:L5](file:///Users/zhoupeng/Documents/rsc2026/scripts/import_rsc_data.py#L5)
- financial_scraper 默认写入：`financial_data_v2.db`（在 `financial_scraper/` 目录内）  
  - 定义：[database.py:L11-L18](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper/database.py#L11-L18)

建议：以“后端读取的 DB”为单一事实来源，运行爬虫/脚本时也写入同一文件；否则前端/后端看到的数据不会随抓取更新。

## 2. 关键表与职责（后端查询视角）

后端主要查询/依赖以下表（见 [search_talents](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L1965) 与 [get_talent_detail](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L2707)）：

- `sac_institutions` / `sac_practitioners`
  - `raw_data` 为 JSON 字符串，包含人员详情与履历（例如 `regHistory`）
- `amac_institutions` / `amac_practitioners`
  - `raw_data` 为 JSON 字符串，包含人员详情与证书历史（例如 `personCertHistoryList`）
- `rsc_users`
  - RSC 用户基础字段 + `ext_data`（JSON 字符串，包含画像/偏好/标签/timeline 等）
- `rsc_orgs`
  - RSC 机构基础字段 + `aum/value_score/influence_score/...` + `ext_data`（机构画像 JSON）
- `rsc_user_mapping`
  - 将 SAC/AMAC 的 `practitioner_id` 映射到 RSC 的 `uid`，并带 `is_outdated`（用于“待更新”标记）
- `progress_tracking`
  - 记录爬虫/管道进度，用于后台监控与 monitor 守护进程判断完成状态

## 3. Schema 来源（代码中的建表语句）

### 3.1 financial_scraper/database.py（采集侧建表）

- 创建与索引见：[database.py:L33-L123](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper/database.py#L33-L123)
- 包含：
  - `amac_institutions(practitioner_id/name/raw_data/created_at/updated_at)`
  - `amac_practitioners(...)`
  - `sac_institutions(...)`
  - `sac_practitioners(...)`
  - `progress_tracking(task_name,last_processed_id/status,raw_data,updated_at)`
  - `unified_personnel(person_id,source,raw_data,...)`

### 3.2 scripts/import_rsc_data.py（RSC 用户/机构导入）

- 初始建表见：[import_rsc_data.py:L9-L49](file:///Users/zhoupeng/Documents/rsc2026/scripts/import_rsc_data.py#L9-L49)
  - `rsc_users`（uid/name/cert_type/org_name/oid/...）
  - `rsc_orgs`（oid/full_name/short_name/region/website/...）

### 3.3 scripts/migrate_rsc_tables.py（RSC 字段扩展）

- 增加字段见：[migrate_rsc_tables.py:L21-L37](file:///Users/zhoupeng/Documents/rsc2026/scripts/migrate_rsc_tables.py#L21-L37)
  - `rsc_users`: gender/intro/birthday/highest_edu/university/major/ext_data
  - `rsc_orgs`: aum/value_score/influence_score/invest_position/is_foreign/ext_data

### 3.4 scripts/rsc_cross_check.py（映射表）

- `rsc_user_mapping` 建表与 upsert：见 [rsc_cross_check.py:L291-L315](file:///Users/zhoupeng/Documents/rsc2026/scripts/rsc_cross_check.py#L291-L315)
  - 主键：`(practitioner_id, source_type)`
  - 关键字段：`rsc_uid`、`rsc_org`、`rsc_cert_time`、`is_outdated`

## 4. 后端内存索引与 DB 字段的关系

内存索引来自 `rsc_users.ext_data` 与 `rsc_orgs.aum`，并与映射表结合：

- `tag_index`：从 `ext_data` 的行为偏好/投研行业/价值标签等抽取（`extract_user_tags`）
- `office_city_index`：`ext_data.office_city`
- `shenwan1_index`：`ext_data.shenwan_1`
- `org_type_index`：`ext_data.org_type` 归一化后
- `aum_index`：`rsc_orgs.aum` 文本分桶（`>100亿` / `50-100亿` / `20-50亿` / `0-20亿`）
- `outdated_rsc_uids`：`rsc_user_mapping.is_outdated = 1`

相关实现：

- 索引构建：[build_memory_indices](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L993-L1060)
- 标签抽取：[extract_user_tags](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L69-L101)

