## 目标

将当前项目以“最基础、可公开访问、尽量纯免费”的方式上线用于内测/演示：

- 前端：Vercel（Next.js）
- 后端：Render Free Web Service（FastAPI）
- 数据：SQLite（现有 `financial_data_v1.db`），通过“启动时按需下载”的方式提供，避免把 459MB 数据库提交到代码仓库

## 约束与风险

- Render Free Web Service 会在不活跃后休眠，首个请求可能有冷启动延迟（演示可接受）。
- SQLite 全量库约 459MB，若每次重新部署都重新下载，会拉长部署与首个可用时间；但通常同一实例生命周期内可复用本地文件缓存。
- 当前后端 CORS 为 `allow_origins=["*"]`，演示期可以先保留；正式上线需要收敛为前端域名白名单。
- 前端目前硬编码 `http://127.0.0.1:8000`（多处），上线必须改为可配置 `NEXT_PUBLIC_API_BASE_URL`。

## 架构

- 浏览器 → Vercel（Next.js 静态/SSR）
- Vercel 前端通过 `NEXT_PUBLIC_API_BASE_URL` 请求 Render 后端
- Render 后端启动时：
  - 优先使用本地 `DB_PATH`（若存在）
  - 若不存在且配置了 `DB_URL`：下载 SQLite 到本地可写目录并作为 `DB_PATH`

## 配置规范

### 前端（Vercel）

- `NEXT_PUBLIC_API_BASE_URL`：指向 Render 后端公开 URL，例如 `https://<service>.onrender.com`

### 后端（Render）

- `PORT`：Render 注入（启动命令使用 `$PORT`）
- `DB_PATH`（可选）：SQLite 文件路径（默认走项目内路径逻辑）
- `DB_URL`（可选但推荐）：SQLite 下载链接（GitHub Release Asset 等公开直链）
- `CORS_ALLOW_ORIGINS`（可选，推荐）：以逗号分隔的允许域名列表；未设置时保持当前 `*`

## 数据发布策略（纯免费）

推荐使用 GitHub Release 作为数据库文件分发：

1. 在仓库创建一个 Release（例如 `data-v1`）
2. 上传 `financial_scraper/financial_data_v1.db` 作为 Release Asset
3. 在 Render 后端配置 `DB_URL` 为该 Asset 的直链

## 落地改造清单（最小集）

1. 前端
   - 新增统一的 API base URL 读取（`NEXT_PUBLIC_API_BASE_URL`），替换所有硬编码 `127.0.0.1:8000`
2. 后端
   - 增加 `requirements.txt` 以便 Render 自动识别 Python 项目依赖
   - 增加 DB 下载与本地缓存逻辑（受 `DB_URL` 控制）
   - 增加可配置 CORS（可选）
3. 文档
   - 新增《上线手册》：Vercel 与 Render 的创建、环境变量配置、验证与回滚

## 验证标准

- 前端 Vercel URL 打开后可正常加载首页、Latest/Newest、详情弹窗
- 前端请求走公网后端（非 localhost），无跨域报错
- 后端 `/api/health`（或类似自检接口）可用
- 后端在无本地 DB 文件时能通过 `DB_URL` 拉取并成功提供搜索接口

