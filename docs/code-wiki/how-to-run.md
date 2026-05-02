# 运行与开发

本页描述仓库当前代码形态下的“可运行方式”。由于仓库未提供统一的 Python 依赖锁定文件（requirements/poetry/pipenv），以下以“从代码导入推断 + 常见运行命令”为主，实际以你本地环境为准。

## 1. 前置条件

- Node.js + npm（前端）
- Python 3.x（后端与脚本/爬虫）
- SQLite（建议同时具备 sqlite3 CLI，部分 Next.js check 路由会调用它）
- 可用的 SQLite 数据库文件（至少包含 `sac_practitioners` 与 `amac_practitioners` 等表）

数据库文件路径默认约定：

- 后端读取：`financial_scraper/financial_data_v1.db`（见 [main.py:L25-L29](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L25-L29)）

## 2. 启动后端（FastAPI）

1) 进入后端目录：

```bash
cd backend
```

2) 安装依赖（示例，按你的环境调整）：

- 至少需要：`fastapi`、`uvicorn`、`pydantic`

3) 启动：

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

4) 验证接口：

- `GET http://127.0.0.1:8000/api/stats`
- `GET http://127.0.0.1:8000/api/tags`

## 3. 启动前端（Next.js）

1) 进入前端目录：

```bash
cd frontend
```

2) 安装依赖并启动：

```bash
npm install
npm run dev
```

3) 打开：

- `http://localhost:3000`

注意：前端代码中后端地址是硬编码 `http://127.0.0.1:8000`（例如 [page.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/page.tsx) 与 [LatestClient.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/latest/LatestClient.tsx)），因此需要确保后端以该地址可访问。

## 4. 运行爬虫（可选）

爬虫位于 `financial_scraper/`，典型运行方式：

- 单独运行 SAC 抓取：

```bash
cd financial_scraper
python sac_scraper.py
```

- 单独运行 AMAC 抓取：

```bash
cd financial_scraper
python amac_scraper.py
```

- 运行 monitor 守护（会按间隔检查并重启抓取进程，写入日志）：

```bash
cd financial_scraper
python monitor.py
```

注意：

- `financial_scraper/database.py` 默认 DB 名为 `financial_data_v2.db`，[database.py:L11-L18](file:///Users/zhoupeng/Documents/rsc2026/financial_scraper/database.py#L11-L18)。
- 若希望“抓取结果立即被后端检索到”，需要确保爬虫写入的 DB 与后端读取的 DB 是同一个文件，详见 [database.md](./database.md)。

## 5. 导入/生成 RSC 数据（可选）

典型流程：

1) 导入 RSC 用户与机构（需要 Excel 源文件路径可用）：

- [import_rsc_data.py](file:///Users/zhoupeng/Documents/rsc2026/scripts/import_rsc_data.py)

2) 扩展 RSC 表结构（为 ext_data/评分等字段预留）：

- [migrate_rsc_tables.py](file:///Users/zhoupeng/Documents/rsc2026/scripts/migrate_rsc_tables.py)

3) 做跨库匹配并生成映射表 + 待更新标记：

- [rsc_cross_check.py](file:///Users/zhoupeng/Documents/rsc2026/scripts/rsc_cross_check.py)

## 6. AI 对话检索（可选）

后端接口：`POST /api/chat/filter`，[chat_filter](file:///Users/zhoupeng/Documents/rsc2026/backend/main.py#L1384)

若要启用 LLM，需要设置环境变量（示例）：

```bash
export DEEPSEEK_API_KEY="..."
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-v4-flash"
```

未设置 key 时，后端会走规则兜底，仍会输出结构化筛选对象供前端确认跳转。

