## 项目定位（一句话）

金融从业者/机构与投研偏好数据的检索与浏览工具：支持多源人才数据（RSC/SAC/AMAC）统一搜索、筛选、排序，并提供详情页与部分 AI 辅助筛选能力。

## 仓库结构

- 前端（Next.js）：[frontend/](file:///Users/zhoupeng/Documents/rsc2026/frontend)
- 后端（FastAPI）：[backend/](file:///Users/zhoupeng/Documents/rsc2026/backend)
- 数据抓取/处理（Python + SQLite）：[financial_scraper/](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper)
- 数据导入/迁移脚本：[scripts/](file:///Users/zhoupeng/Documents/rsc2026/scripts)
- 设计/规划文档：[/docs](file:///Users/zhoupeng/Documents/rsc2026/docs) 与 [/.trae/documents](file:///Users/zhoupeng/Documents/rsc2026/.trae/documents)

## 技术栈

- 前端：Next.js App Router + React + TypeScript + Tailwind（见 [package.json](file:///Users/zhoupeng/Documents/rsc2026/frontend/package.json)）
- 后端：FastAPI（入口 [main.py](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py)）
- 数据：SQLite（默认读取 `financial_scraper/financial_data_v1.db`，支持通过 `DB_URL` 下载缓存）

## 核心页面（面向产品/运营）

- 首页：搜索与 AI 辅助筛选入口 [page.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/page.tsx)
- Latest：最新变动/列表检索 [latest/](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/latest)
- Newest：最新入库/列表检索 [newest/](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/newest)
- 详情弹窗/详情页：人才详情与标签、轨迹信息 [TalentDetailView.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/components/TalentDetailView.tsx)
- 管理页（监控/质量面板）：[admin/page.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/admin/page.tsx)

## 核心接口（面向技术/AI/运维）

- 人才搜索：`GET /api/talents/search`
- 人才详情：`GET /api/talents/{source}/{id}`
- 标签/筛选：`GET /api/tags`、`GET /api/filters/schema`、`GET /api/stats`
- AI 辅助：`POST /api/chat/filter`

接口均由后端 FastAPI 提供（实现见 [main.py](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py)），前端通过 `NEXT_PUBLIC_API_BASE_URL` 指向后端公网地址。

## 运行方式（本地）

- 前端
  - 目录：`frontend`
  - 命令：`npm run dev`
  - 默认：`http://localhost:3000`
- 后端
  - 目录：`backend`
  - 命令：`uvicorn main:app --reload`
  - 默认：`http://127.0.0.1:8000`

## 环境变量（后端）

关键变量清单见 [backend/.env.example](file:///Users/zhoupeng/Documents/rsc2026/backend/.env.example)。

- 数据相关
  - `DB_URL`：部署环境无本地 DB 文件时，从该 URL 下载 SQLite 并缓存
  - `DB_PATH`：手工指定 SQLite 文件路径（优先级最高）
- 跨域
  - `CORS_ALLOW_ORIGINS`：逗号分隔域名白名单（不设置时等同 `*`）
- LLM
  - `DEEPSEEK_API_KEY`、`OPENAI_API_KEY` 等

## 上线部署（最基础方案）

详见：[vercel-render-free.md](file:///Users/zhoupeng/Documents/rsc2026/docs/deploy/vercel-render-free.md)。

