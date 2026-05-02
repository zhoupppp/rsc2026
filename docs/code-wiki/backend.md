# 后端（FastAPI）

## 1. 入口与运行方式

- 服务入口文件：[main.py](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py)
- FastAPI 实例：`app = FastAPI(...)`，[main.py:L15](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L15)
- SQLite 路径：`DB_PATH = .../financial_scraper/financial_data_v1.db`，[main.py:L25-L29](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L25-L29)

启动后端通常使用（在 `backend/` 目录下）：

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## 2. 核心全局与缓存

### 2.1 SQLite 连接

- `get_db_connection()`：[main.py:L30-L33](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L30-L33)  
  使用 `sqlite3.connect(DB_PATH, check_same_thread=False)` 并设置 `row_factory=sqlite3.Row`。

### 2.2 内存索引（用于加速筛选与统计）

内存索引定义：[main.py:L35-L43](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L35-L43)

- `tag_index: tag -> set(rsc_uid)`
- `aum_index: aum_level -> set(rsc_uid)`（由 `rsc_orgs.aum` 粗略分桶）
- `office_city_index / shenwan1_index / org_type_index`
- `outdated_rsc_uids`（来自 `rsc_user_mapping.is_outdated`）

构建逻辑：`build_memory_indices(cursor)`，[main.py:L993-L1060](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L993-L1060)

### 2.3 筛选统计缓存

- `filter_stats_cache`：[main.py:L44](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L44)
- TTL 约 300s：`get_filter_stats()`，[main.py:L1901-L1918](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L1901-L1918)

## 3. 数据模型（Pydantic）

定义位置：[main.py:L1061-L1090](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L1061-L1090)

- `SearchResultItem`：搜索列表项（统一抽象 SAC/AMAC/RSC）
- `SearchResponse`：列表返回（含分页与 meta）
- `ChatMessage` / `ChatFilterRequest`：AI 对话解析接口输入

## 4. API 设计

### 4.1 启动初始化

- `startup_event()`：[main.py:L1842-L1859](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L1842-L1859)
  - 开 WAL
  - 创建常用索引（name/updated_at/mapping）
  - 构建内存索引（tag/city/org_type/aum/outdated）

### 4.2 统计与筛选字段

- `GET /api/stats`：[get_stats](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L1860-L1888)  
  返回人才总量、机构量、分来源计数、最新更新时间。
- `GET /api/tags`：[get_tags](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L1890-L1899)  
  返回高频 `tags`（前 30）与 AUM 桶，用于前端快速筛选。
- `GET /api/filters/stats`：[get_filter_stats](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L1901-L1918)  
  计算“可选项 TopN”，用于驱动筛选 UI 的下拉候选。
- `GET /api/filters/schema`：[get_filter_schema](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L1920-L1964)  
  生成前端 FilterBuilder 所需字段 schema（字段、类型、ops、options）。

### 4.3 搜索接口（统一 SAC/AMAC/RSC）

- `GET /api/talents/search`：[search_talents](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L1965-L2199)

关键参数：

- 基本：`name`、`institution`、`page`、`size`
- 来源控制：`only_rsc`（仅返回已匹配 RSC 的 SAC/AMAC 记录）、`include_rsc`（额外 union RSC 用户）
- 快速条件：`tags`、`aum`、`adv_shenwan_1`、`adv_office_city`、`adv_org_type`
- 高级表达式：`adv_query`（JSON 字符串，见 4.5）
- 排序：`sort_by`（如 `relevance` / `latest_job_change` / `recent_active` 等，具体实现分支在函数内部）

实现要点：

- 三路 union：`sac_practitioners` + `amac_practitioners` +（可选）`rsc_users`，并通过窗口函数去重（同一 rsc_uid 或 source+id）。
- 当 `sort_by == "relevance"` 时，将部分 tag 条件视作“软偏好”参与相关性计算，而不是硬过滤：
  - 逻辑入口：`split_query_hard_soft()`、`compute_relevance_score()`，[main.py:L457-L507](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L457-L507)
  - 目的：避免因标签过窄导致 0 结果，同时让结果更贴近“意图”。

### 4.4 详情接口（统一 profile）

- `GET /api/talents/{source}/{talent_id}`：[get_talent_detail](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L2707-L3140)

输出结构（概念上）：

- `id/name/institution/source/gender/education/cert_no/avatar_url/origin_url`
- `rsc_info`：RSC 画像字段（用户画像 + 机构画像合并）
- `timeline`：职业履历列表（若可从 ext_data/raw_data 中构建）

RSC 分支要点：

- 从 `rsc_users` + `rsc_orgs` 拉取，并解析 `ext_data`、`org_ext_data` 组装 `rsc_info`，[main.py:L2712-L2839](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L2712-L2839)

SAC/AMAC 分支要点：

- 读取各自 practitioners 表的 `raw_data` 并抽取字段（代码在 RSC 分支之后继续）。

### 4.5 AI 对话解析接口（可选 LLM）

- `POST /api/chat/filter`：[chat_filter](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L1384)

行为分支：

- 若未配置 API Key：走规则兜底 + 候选建议  
  - 入口与兜底策略：[main.py:L1386-L1431](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L1386-L1431)
- 若配置 API Key：请求 `.../chat/completions`，期望 JSON 输出（`response_format: json_object`）
  - system prompt 定义在函数内部，且会注入数据库 Top 候选值提示（`compute_filter_stats`）

环境变量（均在 `chat_filter` 中读取）：

- `DEEPSEEK_API_KEY` / `OPENAI_API_KEY`
- `DEEPSEEK_BASE_URL` / `OPENAI_BASE_URL`（默认 `https://api.deepseek.com`）
- `DEEPSEEK_MODEL` / `OPENAI_MODEL`（默认 `deepseek-v4-flash`）
- `DEEPSEEK_SSL_VERIFY` / `OPENAI_SSL_VERIFY`
- `LLM_DEBUG`、`CHAT_FILTER_MAX_HISTORY`

### 4.6 管理与监控接口

- `GET /api/admin/data/quality`：[get_data_quality](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L3143-L3201)  
  返回 SAC/AMAC 的字段完整度、今日新增、RSC 匹配率与待更新数。
- `GET /api/admin/scraper/status`：[get_scraper_status](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L3202-L3223)  
  读取 `progress_tracking` 展示任务进度。
- `GET /api/admin/scraper/logs`：[get_scraper_logs](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L3224-L3243)  
  读取 `financial_scraper/*.log` 尾部 100 行供前端显示。

## 5. 高级筛选表达式（adv_query）

前端会把 FilterBuilder 生成的 JSON 作为 `adv_query` 参数传入后端：[toAdvQuery](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/components/FilterBuilder.tsx#L70-L74)

表达式模型（后端期望）：

- Group：`{"op": "and"|"or", "children": [Group|Rule, ...]}`
- Rule：
  - `{"field": "...", "op": "exists"|"not_exists"}`
  - `{"field": "...", "op": "in"|"not_in", "values": ["..."]}`
  - `{"field": "...", "op": "eq"|"neq"|"contains"|"not_contains"|"gt"|"gte"|"lt"|"lte", "value": "..."}`

后端处理链路：

- `normalize_filter_query()` / `normalize_filter_rule()`：清洗与白名单校验，[main.py:L369-L457](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L369-L457)
- `evaluate_filter_query_to_ids()`：将表达式求值为 rsc_uid 集合，[main.py:L507-L535](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L507-L535)

## 6. 依赖关系（从代码导入推断）

仓库未提供后端/爬虫统一的 `requirements.txt`；Python 依赖可从导入语句推断：

- 后端（`backend/main.py`）：`fastapi`、`pydantic`、标准库 `sqlite3/json/os/ssl/urllib/...`
- 脚本与爬虫（示例）：`pandas`、`requests`、`urllib3`、`httpx`、`zhconv`

建议将依赖整理为可复现的 requirements/lock（当前 Wiki 仅描述现状）。

