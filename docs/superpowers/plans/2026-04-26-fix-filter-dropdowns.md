# Advanced Filters Dropdown Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`-[x]`) syntax for tracking.

**Goal:** Correct the options in the `<select>` dropdowns for the advanced filters on the Home Page to strictly match the unique values found in the source Excel files (`rsc_users` and `rsc_orgs`).

**Architecture:** Modify the hardcoded `<option>` elements in `frontend/src/app/page.tsx` for `机构类型`, `认证类型`, `申万一级行业`, `国家地区`, and `内外资`.

**Tech Stack:** Next.js, React

---

### Task 1: Update Dropdown Options in `page.tsx`

**Files:**
- Modify: `frontend/src/app/page.tsx`

-[x] **Step 1: Update 机构类型 (Org Type) Options**
Update the `<select>` for `advOrgType` with the full list from Excel.
```tsx
// Replace existing advOrgType <select> content with:
                      <select value={advOrgType} onChange={(e) => setAdvOrgType(e.target.value)} className="w-full h-8 px-2 text-xs border border-slate-200 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-slate-900 text-slate-700">
                        <option value="">不限</option>
                        <option value="财富管理公司">财富管理公司</option>
                        <option value="金融科技软件技术服务">金融科技软件技术服务</option>
                        <option value="财经媒体">财经媒体</option>
                        <option value="券商研究所">券商研究所</option>
                        <option value="私募证券投资基金管理人">私募证券投资基金管理人</option>
                        <option value="财务顾问机构">财务顾问机构</option>
                        <option value="私募股权/创业投资基金管理人">私募股权/创业投资基金管理人</option>
                        <option value="境外资产管理公司">境外资产管理公司</option>
                        <option value="境内公募基金管理公司">境内公募基金管理公司</option>
                        <option value="财经数据服务">财经数据服务</option>
                        <option value="证券公司">证券公司</option>
                        <option value="律师事务所">律师事务所</option>
                        <option value="实业投资">实业投资</option>
                        <option value="一般企业">一般企业</option>
                        <option value="银行">银行</option>
                        <option value="国家/政府投资平台">国家/政府投资平台</option>
                        <option value="其他私募投资基金管理人">其他私募投资基金管理人</option>
                        <option value="境外银行">境外银行</option>
                        <option value="协会/商会">协会/商会</option>
                        <option value="私募资产配置类管理人">私募资产配置类管理人</option>
                        <option value="保险公司">保险公司</option>
                        <option value="信托公司">信托公司</option>
                        <option value="其他私募投资基金管理人(未备案)">其他私募投资基金管理人(未备案)</option>
                        <option value="境外投资公司">境外投资公司</option>
                        <option value="私募基金管理人(已注销)">私募基金管理人(已注销)</option>
                        <option value="其他机构投资者">其他机构投资者</option>
                        <option value="QFII/RQFII">QFII/RQFII</option>
                        <option value="评级服务机构">评级服务机构</option>
                        <option value="财经公关服务">财经公关服务</option>
                        <option value="政府单位及监管机构">政府单位及监管机构</option>
                        <option value="其他研究机构">其他研究机构</option>
                        <option value="主权财富基金">主权财富基金</option>
                        <option value="金融控股集团">金融控股集团</option>
                        <option value="券商资管">券商资管</option>
                        <option value="投资银行">投资银行</option>
                        <option value="保险资产管理公司">保险资产管理公司</option>
                        <option value="会计师事务所">会计师事务所</option>
                        <option value="券商自营">券商自营</option>
                        <option value="期货公司">期货公司</option>
                        <option value="高等院校/基金会">高等院校/基金会</option>
                        <option value="公募资管">公募资管</option>
                        <option value="独立第三方销售机构">独立第三方销售机构</option>
                        <option value="企业财务公司">企业财务公司</option>
                        <option value="养老基金">养老基金</option>
                        <option value="QDII/QDII2">QDII/QDII2</option>
                        <option value="中央银行">中央银行</option>
                        <option value="未分类">未分类</option>
                      </select>
```

-[x] **Step 2: Update 认证类型 (Cert Type) Options**
```tsx
// Replace existing advCertType <select> content with:
                      <select value={advCertType} onChange={(e) => setAdvCertType(e.target.value)} className="w-full h-8 px-2 text-xs border border-slate-200 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-slate-900 text-slate-700">
                        <option value="">不限</option>
                        <option value="机构投资者">机构投资者</option>
                        <option value="媒体">媒体</option>
                        <option value="服务机构">服务机构</option>
                        <option value="个人">个人</option>
                        <option value="上市公司">上市公司</option>
                        <option value="卖方分析师">卖方分析师</option>
                        <option value="金融机构">金融机构</option>
                        <option value="未分类">未分类</option>
                      </select>
```

-[x] **Step 3: Update 申万一级行业 (Shenwan) Options**
Change the input to a select based on the Excel unique values.
```tsx
// Replace existing advShenwan <input> with <select>:
                      <select value={advShenwan} onChange={(e) => setAdvShenwan(e.target.value)} className="w-full h-8 px-2 text-xs border border-slate-200 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-slate-900 text-slate-700">
                        <option value="">不限</option>
                        <option value="电子">电子</option>
                        <option value="轻工制造">轻工制造</option>
                        <option value="非银金融">非银金融</option>
                        <option value="房地产">房地产</option>
                        <option value="汽车">汽车</option>
                        <option value="有色金属">有色金属</option>
                        <option value="社会服务">社会服务</option>
                        <option value="医药生物">医药生物</option>
                        <option value="传媒">传媒</option>
                        <option value="计算机">计算机</option>
                        <option value="交通运输">交通运输</option>
                        <option value="机械设备">机械设备</option>
                        <option value="建筑材料">建筑材料</option>
                        <option value="电力设备">电力设备</option>
                        <option value="商贸零售">商贸零售</option>
                        <option value="银行">银行</option>
                        <option value="建筑装饰">建筑装饰</option>
                        <option value="食品饮料">食品饮料</option>
                        <option value="公用事业">公用事业</option>
                        <option value="通信">通信</option>
                        <option value="纺织服饰">纺织服饰</option>
                        <option value="美容护理">美容护理</option>
                        <option value="石油石化">石油石化</option>
                        <option value="农林牧渔">农林牧渔</option>
                        <option value="综合">综合</option>
                        <option value="家用电器">家用电器</option>
                        <option value="基础化工">基础化工</option>
                        <option value="环保">环保</option>
                        <option value="国防军工">国防军工</option>
                        <option value="煤炭">煤炭</option>
                        <option value="钢铁">钢铁</option>
                      </select>
```

-[x] **Step 4: Update 国家地区 (Region) Options**
```tsx
// Replace existing advRegion <select> content with:
                      <select value={advRegion} onChange={(e) => setAdvRegion(e.target.value)} className="w-full h-8 px-2 text-xs border border-slate-200 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-slate-900 text-slate-700">
                        <option value="">不限</option>
                        <option value="中国大陆">中国大陆</option>
                        <option value="中国香港">中国香港</option>
                        <option value="中国台湾">中国台湾</option>
                        <option value="中国澳门">中国澳门</option>
                        <option value="新加坡">新加坡</option>
                        <option value="美国">美国</option>
                        <option value="英国">英国</option>
                        <option value="韩国">韩国</option>
                        <option value="欧洲">欧洲</option>
                        <option value="瑞士">瑞士</option>
                        <option value="英属维尔京群岛">英属维尔京群岛</option>
                        <option value="开曼群岛">开曼群岛</option>
                        <option value="法国">法国</option>
                        <option value="以色列">以色列</option>
                        <option value="挪威">挪威</option>
                        <option value="加拿大">加拿大</option>
                        <option value="尼日利亚">尼日利亚</option>
                        <option value="印度尼西亚">印度尼西亚</option>
                        <option value="日本">日本</option>
                        <option value="葡萄牙">葡萄牙</option>
                        <option value="澳大利亚">澳大利亚</option>
                        <option value="马来西亚">马来西亚</option>
                        <option value="德国">德国</option>
                        <option value="丹麦">丹麦</option>
                        <option value="爱尔兰">爱尔兰</option>
                        <option value="意大利">意大利</option>
                        <option value="南非">南非</option>
                        <option value="菲律宾">菲律宾</option>
                        <option value="阿联酋">阿联酋</option>
                        <option value="卡塔尔">卡塔尔</option>
                        <option value="泰国">泰国</option>
                        <option value="肯尼亚">肯尼亚</option>
                        <option value="巴西">巴西</option>
                        <option value="瑞典">瑞典</option>
                        <option value="卢森堡">卢森堡</option>
                        <option value="俄罗斯">俄罗斯</option>
                        <option value="哈萨克斯坦">哈萨克斯坦</option>
                        <option value="荷兰">荷兰</option>
                        <option value="越南">越南</option>
                        <option value="根西岛">根西岛</option>
                        <option value="新西兰">新西兰</option>
                        <option value="印度">印度</option>
                        <option value="哥伦比亚">哥伦比亚</option>
                        <option value="波多黎各">波多黎各</option>
                        <option value="芬兰">芬兰</option>
                        <option value="巴哈马群岛">巴哈马群岛</option>
                        <option value="多米尼加共和国">多米尼加共和国</option>
                        <option value="奥地利">奥地利</option>
                        <option value="未知地区">未知地区</option>
                      </select>
```

-[x] **Step 5: Update 内外资 (Is Foreign) Options**
```tsx
// Replace existing advIsForeign <select> content with:
                      <select value={advIsForeign} onChange={(e) => setAdvIsForeign(e.target.value)} className="w-full h-8 px-2 text-xs border border-slate-200 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-slate-900 text-slate-700">
                        <option value="">不限</option>
                        <option value="纯外资机构  ">纯外资机构</option>
                      </select>
```
*(Note: The excel data currently only shows "纯外资机构  " as a unique value with spaces. We will use `纯外资机构` but might need to adjust backend matching if space-sensitive)*

-[x] **Step 6: Backend Exact Matching for Spaces**
Modify `backend/main.py` if necessary to use `LIKE` or `TRIM()` for `adv_is_foreign` to handle trailing spaces in the database.
```python
    if adv_is_foreign:
        where_clauses.append("TRIM(json_extract(o.ext_data, '$.is_foreign')) = TRIM(?)")
        params.append(adv_is_foreign)
```

-[x] **Step 7: Commit changes**
```bash
git add frontend/src/app/page.tsx backend/main.py
git commit -m "fix(ui): align advanced filter dropdown options with exact excel data"
```
