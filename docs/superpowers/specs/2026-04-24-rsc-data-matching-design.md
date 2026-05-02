# RSC 数据交叉比对重构设计文档 (Design Spec)

## 1. 目标与背景
现有的 RSC 数据比对逻辑是基于两份简化的、单 Sheet 的 Excel 静态文件。最新获取的数据升级为包含完整用户与机构画像的多 Sheet Excel 格式，并带有明确的 `uid` 和 `oid` 作为唯一主键。
本设计的核心目标是：
1. **数据持久化**：将多 Sheet 的新 Excel 数据清洗并落库到本地 SQLite 数据库中，以便后续 API 和脚本进行关联查询。
2. **比对算法升级**：基于新引入的机构库别名/曾用名系统，重构 `rsc_cross_check.py`，采用“OID 精确关联 + 字符串模糊匹配兜底”的双轨制策略，提升与 SAC/AMAC 爬虫数据的匹配成功率。

## 2. 架构设计与数据流

### 2.1 数据库建模 (`financial_data.db`)
新增两张核心主表以存储 RSC 原始数据：
- **`rsc_users` 表**：
  - `uid` (TEXT, PRIMARY KEY): 用户唯一标识。
  - `name` (TEXT): 姓名。
  - `cert_type` (TEXT): 认证类型（卖方分析师/机构投资者等）。
  - `org_name` (TEXT): 填写的机构名。
  - `oid` (TEXT): 关联的机构 ID。
  - `org_short_name`, `position`, `department`, `cert_time`, `org_full_name`, `org_type`, `stock_code`, `last_active_time`, `register_time` 等扩展字段。

- **`rsc_orgs` 表**：
  - `oid` (TEXT, PRIMARY KEY): 机构唯一标识。
  - `full_name` (TEXT): 机构全称。
  - `short_name` (TEXT): 机构简称。
  - `en_name`, `en_short_name` (TEXT): 英文名。
  - `aliases` (TEXT): 别名/曾用名（逗号分隔的字符串，用于比对扩展）。
  - 其他字段如 logo, 官网, 信用代码等。

*注意：第一阶段优先导入两个 Excel 文件的 Sheet1 核心数据，后续可随时根据需要建立 `rsc_user_tags` 等扩展表并补充导入脚本。*

### 2.2 数据导入脚本 (`scripts/import_rsc_data.py`)
- **功能**：读取新版 Excel，清洗表头和空值，并使用 `UPSERT` (INSERT OR REPLACE) 逻辑将数据全量写入上述两张表中。
- **依赖**：`pandas`。
- **执行频率**：当 RSC 平台提供新的数据包时手动运行，或未来通过 API 获取后定期调度。

### 2.3 交叉比对引擎重构 (`scripts/rsc_cross_check.py`)
核心逻辑调整为：
1. **获取待比对用户**：从 `rsc_users` 表中筛选 `cert_type` 包含“卖方分析师”或“机构投资者”的用户。
2. **获取对比用机构名集合 (Org Name Set)**：
   - 优先通过 `rsc_users.oid` 去 `rsc_orgs` 表中查询，将 `full_name`, `short_name`, `aliases` (按符号分割后) 统统加入待匹配集合中。
   - 将 `rsc_users` 本身的 `org_name` 和 `org_full_name` 也加入集合。
3. **人员锚定与匹配**：
   - 在 SAC/AMAC 表（如 `practitioners`）中通过 `name` 查出所有同名人员。
   - 遍历这些人员的历史履历，利用 `strip_company_tail` 等清洗函数，判断其履历中的机构名称是否命中了上一步构建的“Org Name Set”。
4. **状态判定与落库**：
   - 沿用现有的“比对最新任职时间与认证时间”逻辑判定 `is_outdated`。
   - 将结果（包含匹配方式是 OID 还是 模糊匹配）写入/更新 `rsc_user_mapping` 表。这里将映射表原有的 `rsc_uid` 统一对齐为新数据的真实 `uid`。
5. **输出报表**：
   - 生成 `outdated_rsc_users.xlsx` 和 `unmatched_rsc_users.xlsx` 供运营审查。

## 3. 容错与边界处理
- **OID 为空或不匹配**：如果用户表中的 OID 为空或在机构表中查不到，系统将自动降级使用用户表中原有的 `org_name` 进行原逻辑的字符串模糊匹配，防止数据断链。
- **别名解析**：机构库中的“别名/曾用名”字段可能包含多种分隔符（顿号、逗号、空格），需要在 SQL 或 Python 中统一处理清洗为列表。
- **时间格式**：Excel 导入时的各种不规范日期格式需在导入或比对时进行 `pd.to_datetime` 标准化，避免 `is_outdated` 判定抛错。

## 4. 交付清单
1. 数据库建表 DDL 语句。
2. `scripts/import_rsc_data.py` 数据导入脚本。
3. 更新后的 `scripts/rsc_cross_check.py` 脚本。
4. 在 README 或运维文档中更新执行命令与流程。
### 2.4 扩展数据落库 (Phase 2: Extension Data Ingestion)
对于新 Excel 中其余的 Sheet（人物简介、画像标签、价值画像、管理规模等），采用 **“核心字段合并 + 零散标签转 JSON 存入 ext_data”** 的策略：
1. **核心字段扩充**：
   - `rsc_users` 增加：`gender`, `intro`, `birthday`, `highest_edu`, `university`, `major`, `ext_data` (JSON TEXT)。
   - `rsc_orgs` 增加：`aum` (管理规模), `value_score` (价值评分), `influence_score` (影响力评分), `invest_position` (投资定位), `is_foreign` (是否外资), `ext_data` (JSON TEXT)。
2. **导入脚本 (`scripts/import_rsc_ext_data.py`)**：
   - 读取各个 Sheet 数据。
   - 使用 `UPDATE` 语句将提取的字段和构造的 JSON 字典合并入对应的主表中（依据 `uid` / `oid`）。

### 2.5 综合检查报表生成 (Phase 3: Comprehensive Reporting)
由于原有的比对脚本只输出“待更新(outdated)”和“未匹配(unmatched)”的两份异常报告，为满足人工全面查验履历和最新状态的需求，新增一个独立的数据报表生成脚本。
- **脚本名**：`scripts/generate_matched_report.py`
- **功能**：连接 `financial_data.db`，读取 `rsc_user_mapping` 表中所有成功关联（无论是SAC还是AMAC，无论是否过期）的记录。通过 `practitioner_id` 联表查询原始爬虫数据（`sac_practitioners` 和 `amac_practitioners`），重新解析历史履历。
- **输出格式**：输出一份单一的 Excel 文件 `matched_rsc_users_report.xlsx`。
- **核心列（Columns）**：
  - `UID` (用户唯一标识)
  - `姓名`
  - `认证类型` (从 rsc_users 获取)
  - `RSC原机构` (rsc_org)
  - `RSC认证时间` (rsc_cert_time)
  - `是否待更新` (is_outdated，TRUE表示已离职/跳槽)
  - `最新任职机构` (从履历中提取最晚一段)
  - `最新任职起始日期` (从履历中提取最晚一段)
  - `任职履历历史明细` (文本拼接格式：A公司(2018~2020) -> B公司(2020~present))
  - `官方查验URL` (拼接官网详情页链接)
  - `头像URL` (如有)
