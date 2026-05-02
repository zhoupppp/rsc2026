# 整体架构

## 1. 组件视图

系统分为四个主要部分：

- 数据采集层：`financial_scraper/` 负责从 SAC/AMAC 官方站点抓取人员与机构数据，写入 SQLite，并通过 `progress_tracking` 记录断点进度。
- 数据整理层：`scripts/` 负责将 RSC 的 Excel 数据导入 SQLite，并将 RSC 用户与 SAC/AMAC 人员按姓名+机构履历做匹配，生成 `rsc_user_mapping` 与“待更新”标记。
- 服务层：`backend/` 提供统一的检索与详情 API，且在启动时构建内存索引以加速筛选与标签统计。
- 展示层：`frontend/` 提供 Web UI，直接请求后端 API 完成搜索/详情/筛选器渲染与后台监控展示。

## 2. 数据流（从采集到检索）

### 2.1 SAC/AMAC 抓取与入库

- SAC 抓取：[sac_scraper.py](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper/sac_scraper.py)  
  - 抓取机构列表（`sac_institutions`）→ 逐机构抓取从业人员（`sac_practitioners`）→ 写入 `progress_tracking` 支持断点续跑
- AMAC 抓取：[amac_scraper.py](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper/amac_scraper.py)  
  - 抓取机构列表（`amac_institutions`）→ 逐机构抓取从业人员（`amac_practitioners`）→ 写入 `progress_tracking`
- 监控守护：[monitor.py](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper/monitor.py)  
  - 定时检查数据增长与进度状态，必要时重启抓取进程，并输出日志文件供后台页面读取

### 2.2 RSC 数据导入与匹配

- Excel 导入（用户/机构）：[import_rsc_data.py](file:///Users/zhoupeng/Documents/rsc2026/scripts/import_rsc_data.py)
- 表结构扩展（为后端检索/画像字段做准备）：[migrate_rsc_tables.py](file:///Users/zhoupeng/Documents/rsc2026/scripts/migrate_rsc_tables.py)
- RSC ↔ SAC/AMAC 匹配与“待更新”检测：  
  - 通过姓名匹配候选 → 解析 SAC `regHistory` 或 AMAC `personCertHistoryList` → 与 RSC 机构名称集合做模糊匹配 → 写入映射表 `rsc_user_mapping`
  - 实现：[rsc_cross_check.py](file:///Users/zhoupeng/Documents/rsc2026/scripts/rsc_cross_check.py)

### 2.3 后端检索与详情服务

后端入口：[backend/main.py](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py)

- 以 `DB_PATH` 指向 SQLite 文件（默认 `financial_scraper/financial_data_v1.db`）。
- 在 `startup_event()` 中创建常用索引，并构建内存索引（tag/city/shenwan/org_type/aum/outdated）。
- `search_talents()` 负责统一检索：将 SAC/AMAC/RSC 合并为同一列表返回；支持 `adv_query` 表达式筛选与 `relevance` 相关性排序。
- `get_talent_detail()` 负责详情：返回统一 profile，其中 `rsc_info` 封装了 RSC 扩展画像、机构画像与 timeline。

### 2.4 前端 UI

前端入口：[frontend/src/app/page.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/page.tsx)

- 首页支持三种模式：快捷检索 / 高级筛选 / AI 对话解析（最终仍转为筛选参数与 `adv_query`）。
- 搜索结果页：[latest](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/latest/page.tsx) 通过 `/api/talents/search` 拉取列表，并以内嵌弹层展示详情。
- 最新入库页：[newest](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/newest/page.tsx) 以不同排序查看增量变化与“待更新”人群。
- 后台监控页：[admin](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/admin/page.tsx) 展示质量指标与抓取日志。

## 3. 运行时拓扑

- 浏览器访问 Next.js（默认 `http://localhost:3000`）
  - 前端直接请求 FastAPI（默认 `http://127.0.0.1:8000`）
- FastAPI 读取本地 SQLite（同机文件路径）
  - 若启用抓取守护，爬虫进程持续写入同一 SQLite 并更新 `progress_tracking` 与日志文件

## 4. 关键设计点

- “筛选器”分为两层：
  - 低成本内存索引过滤（城市/行业/机构类型/标签/AUM/待更新等常用维度）
  - 通用 `adv_query` AST 表达式（支持 AND/OR、in/eq/contains 等），在后端转为 SQL 或集合运算
- AI 对话解析：
  - 有 API KEY 时走 LLM（DeepSeek/OpenAI 兼容 `/chat/completions`）
  - 无 API KEY 时走规则+标签提示的兜底策略，并仍输出结构化筛选对象

