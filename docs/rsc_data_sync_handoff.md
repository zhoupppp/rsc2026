# RSC 数据引擎升级与金融人物库网站同步迭代交接文档

> **致人物库网站开发/对接人员：**
> 近期 RSC 平台数据源从简化版升级为包含完整画像的多 Sheet 复合 Excel。底层数据结构及交叉比对引擎已完成重构与数据落库。为确保前端人物库网站能够同步展示最新、最丰富的用户与机构画像，请参考以下数据变更说明进行同步迭代。

---

## 一、底层数据库 (`financial_data.db`) 核心变更

### 1. 新增全量源数据表
系统已放弃每次动态读取静态 Excel 的方式，改为将 RSC 数据持久化到 SQLite 数据库中。新增了两张核心宽表：

- **`rsc_users` (RSC 用户表)**
  - **主键**: `uid` (替代了以往可能存在的其它临时 ID)
  - **基础字段**: `name`, `cert_type`, `org_name`, `oid`, `org_short_name`, `position`, `department`, `cert_time`, `org_full_name`, `org_type`, `stock_code`, `last_active_time`, `register_time`
  - **扩展核心字段**: `gender` (性别), `intro` (个人介绍), `birthday` (出生日期), `highest_edu` (最高学历), `university` (毕业院校), `major` (所学专业)
  - **动态标签扩展**: `ext_data` (JSON TEXT)。该字段内存储了复杂的数据结构，例如：
    - `behavior_tags`: 行为画像标签及分值（如偏好行业等）
    - `value_tags`: 价值标签
    - `research_industries`: 投研行业多选结果

- **`rsc_orgs` (RSC 机构表)**
  - **主键**: `oid`
  - **基础字段**: `full_name`, `short_name`, `en_name`, `en_short_name`, `aliases`, `logo`, `region`, `website`, `email`, `biz_reg_no`, `credit_code`, `amac_record`, `amac_url`, `org_type`
  - **扩展核心字段**: `aum` (管理规模), `value_score` (价值评分), `influence_score` (影响力评分), `invest_position` (投资定位), `is_foreign` (是否外资)
  - **动态标签扩展**: `ext_data` (JSON TEXT)。包含了 `org_tags` (机构标签) 等信息。

### 2. 映射表 `rsc_user_mapping` 变更
原有的关联关系表 `rsc_user_mapping` 结构依然保留（联合主键：`practitioner_id` + `source_type`），但核心变化如下：
- `rsc_uid` 字段现在严格对齐 `rsc_users` 表中的真实 `uid`。
- `is_outdated` (0或1) 逻辑依然生效，代表该用户在官方库的最新履历显示其已跳槽或离职（待更新）。
- **建议**：后端的查询接口应当通过 `rsc_user_mapping.rsc_uid` 进一步 `LEFT JOIN rsc_users` 和 `rsc_orgs`，从而获取到用户的全部扩展画像。

---

## 二、网站后端 (API) 需要迭代的建议任务

1. **重构详情页接口 (`/api/talents/{source}/{id}`)**
   - **现状**：仅透出了 `is_rsc` 和 `is_outdated`。
   - **迭代**：需要 `JOIN rsc_users` 拿到该人物的 `intro` (简介)、`highest_edu`、`university` 等基础资料。
   - **迭代**：解析 `rsc_users.ext_data` 中的 JSON，提取 `behavior_tags` (偏好行业)、`research_industries` 等，作为单独的对象返回给前端展示。

2. **增加机构画像透出**
   - 通过 `rsc_users.oid` 关联 `rsc_orgs`，向前端一并返回该用户所属机构的 `value_score` (价值评分)、`influence_score` (影响力评分) 和 `aum` (管理规模)。

---

## 三、网站前端 (UI) 需要迭代的建议任务

1. **人物详情页 (Profile Detail) 扩展 RSC 面板**
   - **现状**：详情页右侧只有一个简单的“RSC 已认证”面板和跳转按钮。
   - **迭代 1 (基础信息扩充)**：在 RSC 专属面板或人物基础信息区，展示从新数据库拿到的**个人简介 (`intro`)**、**学历/毕业院校**。
   - **迭代 2 (画像标签可视化)**：新增一个“行为与价值画像”模块。将后端返回的 `behavior_tags`（如偏好行业第一、第二、第三等）用雷达图或 Tag 标签云的形式进行可视化呈现；展示 `research_industries` (投研行业)。
   - **迭代 3 (机构实力展示)**：如果该用户有机构 OID，展示其机构的**价值评分**、**影响力评分**和**管理规模**，增强用户的信任背书。

2. **Admin Dashboard / 大屏监控集成**
   - 数据层面现在已具备了强大的统计基础。建议在 Admin 端增加一个统计板块，通过读取 `rsc_users` 和 `rsc_user_mapping` 实时计算并展示：
     - 当前 RSC 用户总数。
     - 成功匹配官方从业库的人数及匹配率。
     - 标记为 `is_outdated = 1`（待更新/已跳槽）的异常用户数量，并提供一键导出或查看列表的功能。

---
> **总结：** 数据层已经准备好了极度丰富的“行为画像”、“价值标签”、“人物简介”和“机构评估”弹药，只需后端修改 JOIN 逻辑将字段透出，前端即可大幅丰富“金融人物”的详情页展现力。请安排相应的排期进行联调。