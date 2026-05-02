## 概览

目标：使用纯免费（或至少“无需付费即可长期运行”）的方式完成上线演示。

- 前端：Vercel（Next.js）
- 后端：Render Free Web Service（FastAPI）
- 数据库：SQLite（通过后端启动时按 `DB_URL` 下载）

## 前端（Vercel）

### 1) 导入项目

1. 在 Vercel 连接 Git 仓库
2. Root Directory 选择：`frontend`

### 2) 环境变量

- `NEXT_PUBLIC_API_BASE_URL`
  - 值：Render 后端 URL（例如 `https://xxx.onrender.com`）

### 3) 构建与启动

- Build Command：`npm run build`
- Output：保持默认（Next.js）

## 后端（Render）

### 1) 创建 Web Service

1. 在 Render 选择 New → Web Service
2. 连接 Git 仓库
3. Root Directory：`backend`

### 2) 启动命令

- Build Command：`pip install -r requirements.txt`
- Start Command：`uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3) 环境变量

- `DB_URL`（推荐）
  - 值：SQLite 下载直链（建议使用 GitHub Release Asset）
  - 后端会将其下载到仓库根目录下的 `data/financial_data_v1.db`
- `CORS_ALLOW_ORIGINS`（推荐）
  - 值：Vercel 前端域名，例如 `https://your-app.vercel.app`
  - 多个域名用逗号分隔
- LLM 可选（如使用 AI 功能）
  - `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` 等（见 [backend/.env.example](file:///Users/zhoupeng/Documents/rsc2026/backend/.env.example)）

## 数据（GitHub Release 方式）

1. 在 GitHub 仓库创建一个 Release（例如 `data-v1`）
2. 上传文件：`financial_scraper/financial_data_v1.db`
3. 将 Release Asset 的下载直链填入 Render 的 `DB_URL`

## 上线验证

1. 打开 Vercel 站点首页
2. 进入 Latest/Newest 能拉到列表数据
3. 打开详情弹窗能正常加载
4. 若首次访问后端较慢，属于 Render Free 冷启动 + DB 首次下载的正常现象

## 回滚策略

- 前端：Vercel Dashboard → Deployments → 选择历史部署 → Promote to Production
- 后端：Render Dashboard → Deploys → 选择历史部署 → Rollback / Redeploy

