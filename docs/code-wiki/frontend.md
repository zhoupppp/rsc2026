# 前端（Next.js）

## 1. 技术栈与入口

- Next.js App Router（`src/app`）+ React + TypeScript
- Tailwind + shadcn/ui
- 数据请求：SWR（浏览器端 `fetch`）
- 配置与依赖：[package.json](file:///Users/zhoupeng/Documents/rsc2026/frontend/package.json)

入口页面：

- 首页：[page.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/page.tsx)
- 全局布局：[layout.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/layout.tsx)

## 2. 路由与页面职责

### 2.1 首页（/）

- 文件：[page.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/page.tsx)
- 三种检索模式：
  - 快捷检索：姓名/机构 → 跳转 `/latest?...`
  - 高级筛选：多维条件（含 FilterBuilder）→ 生成 `adv_query` → 跳转 `/latest?...`
  - AI 对话：请求后端 `POST /api/chat/filter`，拿到结构化条件后确认跳转 `/latest?...`
- 与后端交互：
  - `GET /api/stats`、`GET /api/tags`、`GET /api/filters/schema`
  - `POST /api/chat/filter`
  - `GET /api/talents/{source}/{id}`（用于首页内嵌详情展示）

### 2.2 搜索结果（/latest）

- UI 逻辑主文件：[LatestClient.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/latest/LatestClient.tsx)
- 核心行为：
  - 将 URL Query 参数映射到后端 `GET /api/talents/search`
  - 支持“更多筛选”，通过 FilterBuilder 生成 `extra_adv_query` 并与基础 `adv_query` 合并
  - 支持详情弹层（overlay）与列表内左右切换、滑动手势关闭/切换

### 2.3 最新入库（/newest）

- UI 逻辑主文件：[NewestClient.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/newest/NewestClient.tsx)
- 核心行为：
  - 默认 `sort_by=latest_added` 拉取列表
  - 支持“仅看待更新”：构造 `adv_query` = `{"field":"is_outdated","op":"eq","value":"true"}`
  - 详情弹层交互与 `/latest` 类似

### 2.4 后台监控（/admin）

- 页面：[admin/page.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/admin/page.tsx)
- 定时轮询：
  - `GET /api/admin/data/quality`
  - `GET /api/admin/scraper/status`
  - `GET /api/admin/scraper/logs?type=...`

## 3. 关键组件

### 3.1 FilterBuilder（高级筛选器）

- 文件：[FilterBuilder.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/components/FilterBuilder.tsx)
- 数据结构：
  - GroupNode（`and/or` + children）
  - RuleNode（field/op/value）
- 输出：
  - `toAdvQuery(value)` 将 UI AST 序列化为后端可识别的 `adv_query` JSON 字符串

### 3.2 TalentDetailView（人员详情）

- 文件：[TalentDetailView.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/components/TalentDetailView.tsx)
- 请求：`GET /api/talents/{source}/{id}`
- 展示：
  - 基础信息（来源、证书、机构等）
  - `rsc_info` 深度画像（偏好行业、行为要点、机构画像等）
  - timeline（官方职业履历）
- 体验：
  - overlay 模式下提供复制链接、上一位/下一位预取（SWR mutate 预热）

## 4. 前端与后端的耦合点

### 4.1 后端地址写死

前端多处直接请求 `http://127.0.0.1:8000`（例如首页与列表页）。这意味着：

- 本地开发需要先启动后端并使用该 host/port。
- 若需要部署，通常要引入环境变量或 Next.js rewrite/proxy 层，否则需改代码中的固定 URL。

### 4.2 Next.js API Routes（check_*）

目录：`frontend/src/app/api/check*/route.ts`

示例：[check_sac/route.ts](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/api/check_sac/route.ts)

- 使用 `child_process.exec` 调用本机 `sqlite3` 命令行读取 DB，再请求后端详情接口做连通性验证。
- 其中 DB 路径是绝对路径（与当前机器用户名/目录绑定），属于强耦合的本地诊断工具。

## 5. 依赖关系（Node）

核心依赖见：[package.json](file:///Users/zhoupeng/Documents/rsc2026/frontend/package.json)

- Next/React：`next@16.x`、`react@19.x`
- UI：`tailwindcss`、`@base-ui/react`、`lucide-react`、`framer-motion`、`recharts`
- 数据请求：`swr`

