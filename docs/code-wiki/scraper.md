# 爬虫与采集（financial_scraper）

目录：[financial_scraper/](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper)

该模块负责从 SAC/AMAC 官方站点抓取机构与从业人员信息并写入 SQLite，同时通过 `progress_tracking` 表实现断点续跑与管道级完成标记。

## 1. 数据库封装

- 文件：[database.py](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper/database.py)
- 核心类：`Database`
  - 打开 SQLite（WAL + synchronous=NORMAL）
  - 初始化表：
    - `amac_institutions` / `amac_practitioners`
    - `sac_institutions` / `sac_practitioners`
    - `progress_tracking`
    - `unified_personnel`（统一人员表，当前在仓库中更多是预留）
  - 提供 `execute_query/fetch_all/fetch_one`

注意：该文件默认 DB 名为 `financial_data_v2.db`，而后端默认读取 `financial_data_v1.db`（见 [main.py:L25-L29](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L25-L29)）。实际运行需要确保“采集写入的 DB”与“后端读取的 DB”一致，详见 [database.md](./database.md)。

## 2. SAC 抓取

- 文件：[sac_scraper.py](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper/sac_scraper.py)
- 核心类：`SACScraper`
  - `fetch_org_list()`：从 `https://gs.sac.net.cn/publicity/v2/getOrgList` 拉取机构列表
  - `fetch_person_list(org_id)`：按机构拉取人员列表（分页）
  - `fetch_person_detail(uuid)`：拉取人员详情（含变更记录）
  - `sync_institutions()`：写入 `sac_institutions`（raw_data 含 status 字段）
  - `scrape_practitioners_for_org(org_id)`：写入 `sac_practitioners`，并将分页进度写入 `progress_tracking`
  - `run()`：并发处理 pending 机构（线程池），完成后写入 `progress_tracking.task_name=sac_pipeline,status=completed`

## 3. AMAC 抓取

- 文件：[amac_scraper.py](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper/amac_scraper.py)
- 核心类：`AmacScraper`
  - `scrape_institutions()`：抓取机构列表并写入 `amac_institutions`
  - `scrape_practitioners_for_org()`：逐机构抓取人员并写入 `amac_practitioners`
  - `run_full_pipeline()`：并发抓取所有机构人员，完成后写入 `progress_tracking.task_name=amac_pipeline,status=completed`

## 4. 监控守护与日志

- 文件：[monitor.py](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper/monitor.py)
- 设计目标：
  - 每隔一段时间（代码中为 20 分钟）检查抓取进程是否异常退出或“卡住”（数据无增长）
  - 必要时重启抓取进程
  - 输出日志：`monitor.log`、`amac_scraper.log`、`sac_scraper.log`

后端提供日志读取接口：[get_scraper_logs](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L3224-L3243)，前端后台页面展示这些日志：[admin/page.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/admin/page.tsx)。

## 5. 依赖关系（从代码导入推断）

该模块涉及的第三方依赖主要包括：

- `httpx`（SAC 抓取）、`requests` + `urllib3`（AMAC 抓取）
- `concurrent.futures`（并发）
- `sqlite3`（持久化）

