# 搜索结果页内嵌详情（返回零等待）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `/latest` 搜索结果页点击单人后，用“内嵌详情（抽屉/覆盖层）”展示档案；关闭详情时瞬间回到点击前的列表位置，不触发页面跳转与重新加载。

**Architecture:** 将首页现有的“人才详情视图”抽成可复用组件 `TalentDetailView`。`/latest` 内通过 URL 参数 `id/source` 控制详情开关（history pushState + popstate），列表页面不卸载，因此筛选条件、列表数据与滚动位置天然保留；同时支持直接访问 `/latest?id=...&source=...` 打开详情。

**Tech Stack:** Next.js App Router, React Client Components, SWR, Tailwind CSS, framer-motion（沿用现有动画体系）

---

## 现状分析（基于代码）

- 搜索结果页为 [LatestClient.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/latest/LatestClient.tsx)。
- 当前从 `/latest` 点击某个结果会跳转到首页详情（`/?id=...&source=...&from=latest...`），导致 `/latest` 组件卸载，返回时重新发请求与重新渲染，用户感知为“又重新加载中”。
- 首页详情 UI 和数据逻辑目前内嵌在 [page.tsx](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/page.tsx#L296-L1436) 中（SWR 拉取 detailData + 复杂渲染）。

---

## 文件结构调整

**新增**
- `frontend/src/components/TalentDetailView.tsx`：复用的“人才详情视图”，内部负责 SWR 拉取详情数据 + 现有详情 UI 渲染；通过 props 控制关闭/返回文案。

**修改**
- `frontend/src/app/page.tsx`：用 `TalentDetailView` 替换原内嵌详情块；保留原来首页的“选中人才/返回来源”逻辑，但把“返回动作”改为 props 回调。
- `frontend/src/app/latest/LatestClient.tsx`：列表点击不再跳转到 `/`，改为在 `/latest` 内更新 URL 并打开内嵌详情覆盖层；处理 popstate 以支持浏览器返回关闭详情；关闭时不触发重新请求列表。

---

### Task 1: 抽离 TalentDetailView 组件（复用首页现有完整详情）

**Files:**
- Create: `frontend/src/components/TalentDetailView.tsx`
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: 新建 TalentDetailView 组件骨架（props + SWR 拉取）**

创建文件 `frontend/src/components/TalentDetailView.tsx`，写入以下代码（后续步骤会把首页详情 JSX 迁移进来）：

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, AlertCircle, ExternalLink, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer } from "recharts";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export type TalentRef = { id: string; source: string };

export default function TalentDetailView({
  talent,
  backLabel,
  onClose,
}: {
  talent: TalentRef;
  backLabel: string;
  onClose: () => void;
}) {
  const { data: detailData, isLoading: isLoadingDetail } = useSWR(
    talent ? `http://127.0.0.1:8000/api/talents/${talent.source}/${talent.id}` : null,
    fetcher
  );

  const tabInitKeyRef = useRef<string>("");
  const [activeTab, setActiveTab] = useState<"timeline" | "org">("timeline");

  const hasTimeline = Array.isArray(detailData?.timeline) && detailData.timeline.length > 0;
  const hasOrg =
    !!detailData?.rsc_info &&
    !!(
      detailData.rsc_info.org_one_sentence_pos ||
      detailData.rsc_info.org_invest_pos ||
      detailData.rsc_info.org_invest_style ||
      detailData.rsc_info.org_core_figures ||
      detailData.rsc_info.org ||
      detailData.rsc_info.org_type ||
      detailData.rsc_info.org_region ||
      detailData.rsc_info.org_is_foreign ||
      detailData.rsc_info.org_group ||
      detailData.rsc_info.org_subtype ||
      detailData.rsc_info.org_office_location ||
      detailData.rsc_info.org_aum ||
      detailData.rsc_info.org_value_score ||
      detailData.rsc_info.org_influence_score ||
      detailData.rsc_info.org_rsc_profile_url ||
      (Array.isArray(detailData.rsc_info.org_tags) && detailData.rsc_info.org_tags.length > 0)
    );
  const resolvedTab: "timeline" | "org" = hasOrg && !hasTimeline ? "org" : !hasOrg && hasTimeline ? "timeline" : activeTab;
  const showSidebar = hasTimeline || hasOrg;

  useEffect(() => {
    if (!detailData || !talent) return;
    const key = `${talent.source}:${talent.id}`;
    if (tabInitKeyRef.current !== key) {
      tabInitKeyRef.current = key;
      setActiveTab(hasOrg ? "org" : "timeline");
      return;
    }
    if (activeTab === "org" && !hasOrg && hasTimeline) {
      setActiveTab("timeline");
      return;
    }
    if (activeTab === "timeline" && !hasTimeline && hasOrg) {
      setActiveTab("org");
      return;
    }
  }, [detailData, talent, hasOrg, hasTimeline, activeTab]);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 10 }}
        transition={{ duration: 0.2 }}
        className="w-full bg-white rounded-none border border-slate-200 overflow-hidden"
      >
        <div className="px-8 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <button
            onClick={onClose}
            className="text-sm font-medium text-slate-600 hover:text-slate-900 flex items-center gap-2 transition-colors border border-slate-200 bg-white/70 hover:bg-white px-3 py-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
          >
            <ArrowLeft className="w-4 h-4" />
            {backLabel}
          </button>
          <div className="flex items-center gap-4">
            <div className="text-xs text-slate-400 font-mono">ID: {talent.id}</div>
            {detailData && detailData.origin_url && (
              <a
                href={detailData.origin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs font-medium text-slate-500 hover:text-slate-800 flex items-center gap-1 transition-colors"
              >
                官方原档案 <ArrowRight className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>

        {isLoadingDetail ? (
          <div className="p-24 flex flex-col items-center justify-center space-y-4">
            <div className="w-8 h-8 border-2 border-slate-200 border-t-slate-800 rounded-full animate-spin"></div>
            <div className="text-sm text-slate-400">正在检索人员档案...</div>
          </div>
        ) : detailData ? (
          <div className="flex flex-col">
            {/* Step 2 会把首页完整详情 JSX 迁移到这里 */}
            <div className="p-10 text-slate-500">详情渲染迁移中...</div>
          </div>
        ) : (
          <div className="p-12 text-center text-slate-500">暂无详情数据</div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
```

- [ ] **Step 2: 将首页详情 JSX 迁移进 TalentDetailView**

从 `frontend/src/app/page.tsx` 复制详情渲染块，替换 `TalentDetailView.tsx` 中 `detailData ? (...) : (...)` 的“详情渲染迁移中...”占位区域：

- 复制范围（完整详情视图主体，不包含 Action Bar）：[page.tsx:L936-L1433](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/page.tsx#L936-L1433)
- 粘贴位置：`TalentDetailView.tsx` 内 `detailData ? (` 的分支里（紧接 `div className="flex flex-col">` 之后）

注意：该范围内引用到的变量 `resolvedTab / showSidebar / activeTab / setActiveTab` 已在 Step 1 中在组件内提供；如果发现缺失的 import（例如某些 lucide 图标、recharts 组件），按 TS 报错补齐 import。

- [ ] **Step 3: 首页用 TalentDetailView 替换原详情块（不改变其它逻辑）**

在 `frontend/src/app/page.tsx`：

1) 在文件顶部 import：

```tsx
import TalentDetailView, { type TalentRef } from "@/components/TalentDetailView";
```

2) 保持现有 `selectedTalent` 数据结构不变（已经是 `{id, source}`），把 `Talent Detail View` 的整个 JSX 替换为：

替换范围：[page.tsx:L883-L1436](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/page.tsx#L883-L1436)

替换代码：

```tsx
      <AnimatePresence>
        {selectedTalent && (
          <div className="w-full max-w-5xl mt-6">
            <TalentDetailView
              talent={selectedTalent as TalentRef}
              backLabel={fromList === "newest" ? "返回最新入库列表" : fromList === "latest" ? "返回搜索结果" : "返回搜索"}
              onClose={() => {
                setSelectedTalent(null);
                if (fromList === "latest") {
                  window.location.href = `/latest${backQuery || ""}`;
                  return;
                }
                if (fromList === "newest") {
                  window.location.href = `/newest${backQuery || ""}`;
                  return;
                }
                window.history.pushState({}, "", window.location.pathname);
              }}
            />
          </div>
        )}
      </AnimatePresence>
```

3) 删除首页中与“详情渲染块”绑定、但已被组件接管的部分（否则会出现未使用变量）：
- 删除 `// Detail API` 的 SWR 调用块：[page.tsx:L296-L301](file:///Users/zhoupeng/Documents/rsc2026/frontend/src/app/page.tsx#L296-L301)
- 删除 `hasTimeline/hasOrg/resolvedTab/showSidebar` 以及 `tabInitKeyRef` 相关逻辑（这些已进入组件；按 TS 报错逐一清理）

- [ ] **Step 4: 运行前端 build 验证 TS 与编译通过**

Run:

```bash
npm -C frontend run build
```

Expected: `Compiled successfully` 且包含 `/latest` 路由。

---

### Task 2: /latest 内嵌详情覆盖层 + URL 同步（返回零等待）

**Files:**
- Modify: `frontend/src/app/latest/LatestClient.tsx`

- [ ] **Step 1: 将列表项从 Link 跳转改为“打开详情（不离开 /latest）”**

在 `LatestClient.tsx` 中，找到列表项渲染处（`items.map(...)` 内）当前使用的：

```tsx
<Link href={`/?id=${item.id}&source=${item.source}&from=latest&back=${backParam}`}>...</Link>
```

替换为 `button`（或 `div role="button"`）并调用 `openDetail(item)`。

新增状态与方法（放在组件内 state 区域附近）：

```tsx
import TalentDetailView, { type TalentRef } from "@/components/TalentDetailView";

const [selectedTalent, setSelectedTalent] = useState<TalentRef | null>(null);

const openDetail = (id: string, source: string) => {
  const url = new URL(window.location.href);
  url.searchParams.set("id", id);
  url.searchParams.set("source", source);
  window.history.pushState({}, "", url.toString());
  setSelectedTalent({ id, source });
};

const closeDetail = () => {
  const url = new URL(window.location.href);
  const hasId = url.searchParams.get("id");
  const hasSource = url.searchParams.get("source");
  if (hasId && hasSource) {
    window.history.back();
    return;
  }
  setSelectedTalent(null);
};
```

列表项替换为（保留原 className 以保持视觉一致）：

```tsx
<button
  type="button"
  onClick={() => openDetail(String(item.id), String(item.source))}
  className="w-full text-left p-6 hover:bg-slate-50 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4 group"
>
  {/* 原 Link 内的内容原样保留 */}
</button>
```

- [ ] **Step 2: 支持直接访问 /latest?id=...&source=... 自动打开详情**

在 `LatestClient.tsx` 中新增一个 `useEffect`：

```tsx
useEffect(() => {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  const id = url.searchParams.get("id");
  const source = url.searchParams.get("source");
  if (id && source) {
    setSelectedTalent({ id, source });
  }
}, []);
```

- [ ] **Step 3: 监听 popstate，实现浏览器返回键关闭详情**

在 `LatestClient.tsx` 中新增 `useEffect`：

```tsx
useEffect(() => {
  const onPop = () => {
    const url = new URL(window.location.href);
    const id = url.searchParams.get("id");
    const source = url.searchParams.get("source");
    if (id && source) {
      setSelectedTalent({ id, source });
    } else {
      setSelectedTalent(null);
    }
  };
  window.addEventListener("popstate", onPop);
  return () => window.removeEventListener("popstate", onPop);
}, []);
```

- [ ] **Step 4: 在 /latest 中渲染覆盖层详情（不影响列表滚动位置）**

在 `LatestClient.tsx` 的列表区域外层（建议放在最底部 `return` 的末尾）追加：

```tsx
{selectedTalent && (
  <div className="fixed inset-0 z-40">
    <div className="absolute inset-0 bg-black/20" onClick={closeDetail} />
    <div className="absolute inset-x-0 top-0 bottom-0 overflow-y-auto">
      <div className="min-h-full px-6 sm:px-12 md:px-24 pt-6 pb-24 w-full max-w-5xl mx-auto">
        <TalentDetailView talent={selectedTalent} backLabel="返回搜索结果" onClose={closeDetail} />
      </div>
    </div>
  </div>
)}
```

要求：
- 打开详情时列表不卸载、不改 scroll，关闭详情不发起列表重新请求（由“不跳页”自然保证）。
- 点击遮罩关闭详情（onClick）。

- [ ] **Step 5: 运行前端 build 验证**

Run:

```bash
npm -C frontend run build
```

Expected: `Compiled successfully`。

---

## 验收标准（Acceptance Criteria）

- 在 `/latest` 搜索结果页点击任一人员：
  - 详情以内嵌覆盖层方式打开；
  - 关闭详情后立刻回到原列表滚动位置，无任何 loading 等待；
  - 浏览器返回键可关闭详情（而不是回到首页）。
- 直接访问 `/latest?id=<id>&source=<source>` 可直接打开对应详情覆盖层。
- `npm -C frontend run build` 成功。

---

## 回滚方式

- 若需快速回滚，只需在 `LatestClient.tsx` 恢复列表项 `Link` 跳转逻辑，并删除新增的详情覆盖层相关 state/effect。

