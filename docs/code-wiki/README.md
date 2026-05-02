# RSC2026 Code Wiki

本 Wiki 面向阅读代码与二次开发，整理仓库的整体架构、模块职责、关键接口与运行方式。

## 1. 项目概览

该仓库实现了一个“金融人才库检索与洞察”系统，核心目标是：

- 通过爬虫与离线数据导入，将 SAC/AMAC/RSC 等来源的人员与机构信息统一落到 SQLite。
- 提供 FastAPI 后端查询接口：搜索、详情、筛选项统计、数据质量/爬虫监控等。
- 提供 Next.js 前端：搜索（快捷/高级/AI 解析）、结果列表、详情页/弹层、最新入库、后台监控大屏。

## 2. 技术栈

- 前端：Next.js（App Router）+ React + TypeScript + Tailwind + shadcn/ui + SWR
  - 配置与依赖：[package.json](file:///Users/zhoupeng/Documents/rsc2026/frontend/package.json)
- 后端：FastAPI + Pydantic + sqlite3（标准库）
  - 入口：[main.py](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py)
- 爬虫与采集：requests/httpx + 并发线程池 + SQLite + 进度表（progress_tracking）
  - 目录：[financial_scraper/](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper)
- 离线 ETL/脚本：pandas/zhconv 等（主要用于 RSC Excel 导入、匹配、迁移）
  - 目录：[scripts/](file:///Users/zhoupeng/Documents/rsc2026/scripts)

## 3. 目录结构与职责

- [backend/](file:///Users/zhoupeng/Documents/rsc2026/backend)  
  FastAPI 服务（目前主要集中在单文件实现），负责查询与聚合、AI 解析入口、筛选器规则执行、监控接口。
- [frontend/](file:///Users/zhoupeng/Documents/rsc2026/frontend)  
  Next.js Web UI（App Router），通过 HTTP 直接访问后端 `http://127.0.0.1:8000`。
- [financial_scraper/](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper)  
  AMAC/SAC 数据抓取与入库（SQLite），支持断点续跑与 monitor 守护。
- [scripts/](file:///Users/zhoupeng/Documents/rsc2026/scripts)  
  RSC 数据导入、表结构迁移、RSC 与 SAC/AMAC 的匹配/过期检测与映射表生成。
- [docs/](file:///Users/zhoupeng/Documents/rsc2026/docs)、[.trae/documents/](file:///Users/zhoupeng/Documents/rsc2026/.trae/documents)  
  设计/规划/交接文档沉淀（非运行时必须）。

## 4. Wiki 导航

- [整体架构](./architecture.md)
- [后端（FastAPI）](./backend.md)
- [前端（Next.js）](./frontend.md)
- [爬虫与采集（financial_scraper）](./scraper.md)
- [数据库与表结构](./database.md)
- [离线脚本（scripts）](./scripts.md)
- [运行与开发](./how-to-run.md)

