"use client";

import Link from "next/link";
import { useState, useEffect, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Search, Users, Building2, Briefcase, ArrowRight, ArrowLeft, AlertCircle, ExternalLink, Clock, Shield, Target, Tags, Sparkles, ChevronDown, ChevronUp } from "lucide-react";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import RecentFollowCompanies from "@/components/RecentFollowCompanies";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from "recharts";
import FilterBuilder, { toAdvQuery, type FilterBuilderValue } from "@/components/FilterBuilder";
import { ModeBar } from "@/components/home/ModeBar";
import type { HomeMode, HomeView } from "@/components/home/types";
import { API_BASE_URL } from "@/lib/api";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function Home() {
  const router = useRouter();
  
  const [homeView, setHomeView] = useState<HomeView>("showcase");
  const [mode, setMode] = useState<HomeMode>("search");
  const [showAssistDrawer, setShowAssistDrawer] = useState(false);
  const [showTrendPanel, setShowTrendPanel] = useState(false);
  const [showAiConfirmDetails, setShowAiConfirmDetails] = useState(false);

  // Manual Search States
  const [nameQuery, setNameQuery] = useState("");
  const [instQuery, setInstQuery] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [marketOnlyRsc, setMarketOnlyRsc] = useState(false);
  const [rscIsMatched, setRscIsMatched] = useState("all");
  const [advOrgTypes, setAdvOrgTypes] = useState<string[]>([]);
  const [marketTags, setMarketTags] = useState<string[]>([]);
  const [advShenwan1s, setAdvShenwan1s] = useState<string[]>([]);
  const [advOfficeCities, setAdvOfficeCities] = useState<string[]>([]);
  const [manualFilter, setManualFilter] = useState<FilterBuilderValue>({ type: "group", id: "root", op: "and", children: [] });

  // AI Chat States
  type ChatMessage = { role: 'user' | 'assistant', content: string };
  type ChatCandidate = { id: string; title: string; confidence?: number; estimated_total?: number; sort_by?: string; filters?: Record<string, any>; query?: any; rationale?: string; relax_level?: number };
  type ChatQuickReply = { id: string; label: string; patch?: { filters?: Record<string, any>; query?: any; sort_by?: string }; rationale?: string };
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatting, setIsChatting] = useState(false);
  const [lastAiQuery, setLastAiQuery] = useState<string | null>(null);
  const [pendingQuery, setPendingQuery] = useState<string | null>(null);
  const [pendingFilters, setPendingFilters] = useState<Record<string, string> | null>(null);
  const [pendingAdvQuery, setPendingAdvQuery] = useState<string | null>(null);
  const [pendingSortBy, setPendingSortBy] = useState<string | null>(null);
  const [pendingCandidates, setPendingCandidates] = useState<ChatCandidate[] | null>(null);
  const [pendingQuickReplies, setPendingQuickReplies] = useState<ChatQuickReply[] | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const filterLabelMap: Record<string, string> = {
    adv_office_city: '办公城市',
    adv_shenwan_1: '申万一级行业',
    adv_org_type: '机构类型',
    name: '姓名',
    institution: '机构',
    tags: '标签',
  };

  const renderAstNode = (node: any, depth = 0): React.ReactNode => {
    if (!node) return null;
    if (node.op === 'and' || node.op === 'or') {
      return (
        <div className={`flex flex-col gap-2 ${depth > 0 ? 'ml-4 pl-3 border-l-2 border-slate-100' : ''}`}>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{node.op === 'and' ? '全部满足 (AND)' : '满足任一 (OR)'}</div>
          <div className="flex flex-col gap-2">
            {node.children?.map((child: any, idx: number) => (
              <div key={idx}>{renderAstNode(child, depth + 1)}</div>
            ))}
          </div>
        </div>
      );
    }
    // Rule node
    const fieldName = filterLabelMap[node.field] || node.field;
    let opName = node.op;
    const opMap: Record<string, string> = {
      eq: '等于', neq: '不等于', contains: '包含', not_contains: '不包含',
      in: '属于', not_in: '不属于', exists: '存在', not_exists: '不存在'
    };
    opName = opMap[node.op] || node.op;
    let valStr = '';
    if (node.values) valStr = node.values.join(' 或 ');
    else if (node.value !== undefined) valStr = String(node.value);

    return (
      <div className="inline-flex items-center gap-1.5 text-[12px] bg-slate-50 border border-slate-200 px-2.5 py-1.5 text-slate-700">
        <span className="font-medium">{fieldName}</span>
        <span className="text-slate-400 text-[10px]">{opName}</span>
        {valStr && <span className="font-bold text-slate-900">{valStr}</span>}
      </div>
    );
  };

  const [isFocused, setIsFocused] = useState(false);
  const [selectedTalent, setSelectedTalent] = useState<any>(null);
  const [fromList, setFromList] = useState<"latest" | "newest" | null>(null);
  const [backQuery, setBackQuery] = useState<string>("");
  const [activeTab, setActiveTab] = useState<'timeline' | 'org'>('timeline');
  const tabInitKeyRef = useRef<string>("");
  const prevHasTimelineRef = useRef(false);
  const [showAllBehavior, setShowAllBehavior] = useState(false);
  const [showAllTimeline, setShowAllTimeline] = useState(false);

  type RecentSearch = { name: string; institution: string; ts: number };
  const RECENT_KEY = "rsc_home_recent_searches";
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const raw = window.localStorage.getItem(RECENT_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed
        .map((it: unknown) => {
          const obj = it as { name?: unknown; institution?: unknown; ts?: unknown };
          return { name: String(obj.name || ""), institution: String(obj.institution || ""), ts: Number(obj.ts || 0) };
        })
        .filter((it: RecentSearch) => !!it.name || !!it.institution)
        .slice(0, 10);
    } catch {
      return [];
    }
  });

  // Scroll to bottom when messages change
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const enterWorkbench = () => {
    setHomeView("workbench");
  };

  const pushRecentSearch = (next: { name: string; institution: string }) => {
    const n = next.name.trim();
    const i = next.institution.trim();
    if (!n && !i) return;
    const item: RecentSearch = { name: n, institution: i, ts: Date.now() };
    setRecentSearches((prev) => {
      const dedup = prev.filter((x) => !(x.name === item.name && x.institution === item.institution));
      const merged = [item, ...dedup].slice(0, 10);
      if (typeof window !== "undefined") {
        try {
          window.localStorage.setItem(RECENT_KEY, JSON.stringify(merged));
        } catch {}
      }
      return merged;
    });
  };

  const resetAiState = () => {
    setMessages([]);
    setChatInput("");
    setIsChatting(false);
    setLastAiQuery(null);
    setPendingQuery(null);
    setPendingFilters(null);
    setPendingAdvQuery(null);
    setPendingSortBy(null);
    setPendingCandidates(null);
    setPendingQuickReplies(null);
    setIsConfirming(false);
  };

  const handleExitWorkbench = () => {
    setHomeView("showcase");
    setMode("search");
    setShowAssistDrawer(false);
    setShowTrendPanel(false);
    setShowAiConfirmDetails(false);
    setIsFocused(false);
    setNameQuery("");
    setInstQuery("");
    setShowAdvanced(false);
    setMarketOnlyRsc(false);
    setRscIsMatched("all");
    setAdvOrgTypes([]);
    setMarketTags([]);
    setAdvShenwan1s([]);
    setAdvOfficeCities([]);
    setManualFilter({ type: "group", id: "root", op: "and", children: [] });
    setSelectedTalent(null);
    setFromList(null);
    setBackQuery("");
    resetAiState();
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onGoHome = () => handleExitWorkbench();
    window.addEventListener("rsc:go-home", onGoHome);
    return () => window.removeEventListener("rsc:go-home", onGoHome);
  }, []);

  // Chat Submit Handler
  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isChatting) return;

    const userMsg = chatInput.trim();
    setLastAiQuery(userMsg);
    setPendingQuery(null);
    setPendingFilters(null);
    setPendingAdvQuery(null);
    setPendingSortBy(null);
    setPendingCandidates(null);
    setPendingQuickReplies(null);
    const newMessages: ChatMessage[] = [...messages, { role: 'user', content: userMsg }];
    setMessages(newMessages);
    setChatInput("");
    setIsChatting(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/chat/filter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newMessages })
      });
      const data = await res.json();

      if (data.type === 'clarify') {
        setMessages(prev => [...prev, { role: 'assistant', content: data.message }]);
        setPendingCandidates(Array.isArray(data.candidates) ? data.candidates : null);
        setPendingQuickReplies(Array.isArray(data.quick_replies) ? data.quick_replies : null);
      } else if (data.type === 'search') {
        const filters: Record<string, string> = {};
        if (data.filters) {
          Object.entries(data.filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
              filters[key] = String(value);
            }
          });
        }

        setPendingQuery(userMsg);
        setPendingFilters(filters);
        if (data.query) {
          setPendingAdvQuery(JSON.stringify(data.query));
        } else {
          setPendingAdvQuery(null);
        }
        setPendingSortBy(data.sort_by ? String(data.sort_by) : null);

        const summary = Object.entries(filters)
          .map(([k, v]) => `${filterLabelMap[k] || k}：${v}`)
          .join('；');

        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: data.message ? `${data.message} ${summary ? `我理解你的需求为：${summary}。请确认是否开始检索？` : '我提取到了一些筛选条件，请确认是否开始检索？'}` : (summary ? `我理解你的需求为：${summary}。请确认是否开始检索？` : '我提取到了一些筛选条件，请确认是否开始检索？') }
        ]);
      }
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: 'assistant', content: '抱歉，系统出现错误，请稍后重试。' }]);
    } finally {
      setIsChatting(false);
    }
  };

  const handleConfirmSearch = () => {
    if (!pendingFilters || !pendingQuery || isConfirming) return;
    setIsConfirming(true);
    setMessages(prev => [...prev, { role: 'assistant', content: '正在为您跳转到筛选结果...' }]);

    const params = new URLSearchParams();
    Object.entries(pendingFilters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, value);
      }
    });
    if (pendingAdvQuery) {
      params.append('adv_query', pendingAdvQuery);
    }
    if (pendingSortBy) {
      params.append('sort_by', pendingSortBy);
    }
    params.set('ai_query', pendingQuery);

    setTimeout(() => {
      router.push(`/latest?${params.toString()}`);
      setPendingQuery(null);
      setPendingFilters(null);
      setPendingAdvQuery(null);
      setIsConfirming(false);
    }, 800);
  };

  const handleModifySearch = () => {
    if (!pendingFilters || isConfirming) return;
    setPendingQuery(null);
    setPendingFilters(null);
    setPendingAdvQuery(null);
    setPendingSortBy(null);
    setMessages(prev => [...prev, { role: 'assistant', content: '好的，你想修改哪个条件？也可以直接补充一句话。' }]);
  };

  const applyCandidate = (cand: any) => {
    const rawFilters = (cand && cand.filters) ? cand.filters : {};
    const filters: Record<string, string> = {};
    Object.entries(rawFilters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && String(value).trim() !== "") {
        filters[key] = String(value);
      }
    });
    setPendingQuery(lastAiQuery);
    setPendingFilters(filters);
    setPendingSortBy(cand?.sort_by ? String(cand.sort_by) : "relevance");
    if (cand?.query) {
      setPendingAdvQuery(JSON.stringify(cand.query));
    } else {
      setPendingAdvQuery(null);
    }
    setPendingCandidates(null);
    setPendingQuickReplies(null);
  };

  const applyQuickReply = (qr: any) => {
    const patch = qr?.patch || {};
    const baseCand = pendingCandidates && pendingCandidates.length > 0 ? pendingCandidates[0] : null;
    const baseFilters = baseCand?.filters || {};
    const merged: Record<string, any> = { ...baseFilters, ...(patch.filters || {}) };
    Object.keys(merged).forEach((k) => {
      if (merged[k] === undefined || merged[k] === null || String(merged[k]).trim() === "") delete merged[k];
    });
    const filters: Record<string, string> = {};
    Object.entries(merged).forEach(([key, value]) => {
      if (value !== undefined && value !== null && String(value).trim() !== "") {
        filters[key] = String(value);
      }
    });
    const q = patch.query !== undefined ? patch.query : baseCand?.query;
    setPendingQuery(lastAiQuery);
    setPendingFilters(filters);
    setPendingSortBy(patch.sort_by ? String(patch.sort_by) : (baseCand?.sort_by ? String(baseCand.sort_by) : "relevance"));
    if (q) setPendingAdvQuery(JSON.stringify(q));
    else setPendingAdvQuery(null);
    setPendingCandidates(null);
    setPendingQuickReplies(null);
  };

  const handleQuickSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const n = nameQuery.trim();
    const i = instQuery.trim();
    const params = new URLSearchParams();
    if (n) params.append("name", n);
    if (i) params.append("institution", i);
    pushRecentSearch({ name: n, institution: i });
    router.push(`/latest?${params.toString()}`);
  };

  // Manual Submit Handler
  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams();
    const builder = toAdvQuery(manualFilter);
    const hasAdvanced =
      marketOnlyRsc ||
      rscIsMatched !== "all" ||
      advOrgTypes.length > 0 ||
      marketTags.length > 0 ||
      advShenwan1s.length > 0 ||
      advOfficeCities.length > 0 ||
      !!builder;

    if (!hasAdvanced) {
      if (nameQuery.trim()) params.append("name", nameQuery.trim());
      if (instQuery.trim()) params.append("institution", instQuery.trim());
      pushRecentSearch({ name: nameQuery.trim(), institution: instQuery.trim() });
      router.push(`/latest?${params.toString()}`);
      return;
    }

    const children: any[] = [];
    if (nameQuery.trim()) children.push({ field: "name", op: "contains", value: nameQuery.trim() });
    if (instQuery.trim()) children.push({ field: "institution", op: "contains", value: instQuery.trim() });
    if (advOrgTypes.length > 0) children.push({ field: "adv_org_type", op: "in", values: advOrgTypes });
    if (marketTags.length > 0) children.push({ field: "tags", op: "in", values: marketTags });
    if (advShenwan1s.length > 0) children.push({ field: "adv_shenwan_1", op: "in", values: advShenwan1s });
    if (advOfficeCities.length > 0) children.push({ field: "adv_office_city", op: "in", values: advOfficeCities });

    if (rscIsMatched === "false") children.push({ field: "is_outdated", op: "eq", value: "true" });
    if (rscIsMatched === "true") children.push({ field: "is_outdated", op: "eq", value: "false" });

    if (builder) {
      try {
        children.push(JSON.parse(builder));
      } catch {}
    }

    const qObj = children.length === 1 ? children[0] : { op: "and", children };
    params.append("adv_query", JSON.stringify(qObj));
    if (marketOnlyRsc) params.append("only_rsc", "true");
    pushRecentSearch({ name: nameQuery.trim(), institution: instQuery.trim() });
    router.push(`/latest?${params.toString()}`);
  };

  // Stats
  const { data: stats } = useSWR(`${API_BASE_URL}/api/stats`, fetcher, {
    revalidateOnFocus: false,
    refreshInterval: 5000, // 自动轮询：每5秒刷新一次数据大盘
  });

  const { data: filterOptions } = useSWR(`${API_BASE_URL}/api/tags`, fetcher, {
    revalidateOnFocus: false,
  });
  const { data: filterSchema } = useSWR(`${API_BASE_URL}/api/filters/schema`, fetcher, {
    revalidateOnFocus: false,
  });

  // Check URL params on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const id = urlParams.get('id');
      const source = urlParams.get('source');
      if (id && source) {
        setSelectedTalent({ id, source });
      }
      
      const from = urlParams.get("from");
      if (from === "latest" || from === "newest") {
        setFromList(from);
      }
      const back = urlParams.get("back");
      if (back) {
        try {
          setBackQuery(decodeURIComponent(back));
        } catch {
          setBackQuery("");
        }
      }
    }
  }, []);

  // Update URL when selected talent changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      if (selectedTalent) {
        url.searchParams.set('id', selectedTalent.id);
        url.searchParams.set('source', selectedTalent.source);
        if (fromList) {
          url.searchParams.set("from", fromList);
        }
        if (backQuery) {
          url.searchParams.set("back", backQuery);
        }
        window.history.pushState({}, '', url.toString());
      }
    }
  }, [selectedTalent]);

  // Detail API
  const { data: detailData, isLoading: isLoadingDetail } = useSWR(
    selectedTalent ? `${API_BASE_URL}/api/talents/${selectedTalent.source}/${selectedTalent.id}` : null,
    fetcher
  );

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

  const behaviorSummary = (() => {
    const fromField = detailData?.rsc_info?.behavior_summary;
    if (fromField) return String(fromField);
    const fromTags = detailData?.rsc_info?.behavior_tags?.["行为汇总"];
    if (fromTags) return String(fromTags);
    return "";
  })();

  const behaviorBullets = useMemo(() => {
    if (!behaviorSummary) return [];
    return behaviorSummary
      .split(/[；;。.\n、，,]/g)
      .map((s) => s.trim())
      .filter(Boolean);
  }, [behaviorSummary]);

  const recentFollowCompanies = useMemo(() => {
    const list = (detailData?.rsc_info as any)?.recent_follow_companies;
    if (!Array.isArray(list)) return [];
    return list.map((x: any) => String(x || "").trim()).filter(Boolean).slice(0, 20);
  }, [detailData?.rsc_info]);

  const valueScoreRaw = (detailData?.rsc_info as any)?.org_value_score;
  const influenceScoreRaw = (detailData?.rsc_info as any)?.org_influence_score;
  const hasValueScore = valueScoreRaw !== undefined && valueScoreRaw !== null && String(valueScoreRaw).trim() !== "";
  const hasInfluenceScore = influenceScoreRaw !== undefined && influenceScoreRaw !== null && String(influenceScoreRaw).trim() !== "";
  const valueScoreDisplay = hasValueScore ? String(valueScoreRaw).trim() : "";
  const influenceScoreDisplay = hasInfluenceScore ? String(influenceScoreRaw).trim() : "";
  const scoreToRadar = (v: any) => {
    const s = String(v ?? "").trim();
    const n = Number(s);
    if (Number.isFinite(n)) return Math.max(50, Math.min(100, n));
    const g = s.toUpperCase();
    if (g === "A") return 90;
    if (g === "B") return 75;
    if (g === "C") return 60;
    if (g === "D") return 50;
    return 50;
  };
  const valueScoreForRadar = hasValueScore ? scoreToRadar(valueScoreRaw) : 50;
  const influenceScoreForRadar = hasInfluenceScore ? scoreToRadar(influenceScoreRaw) : 50;

  const timelineDisplay = useMemo(() => {
    const events = Array.isArray(detailData?.timeline) ? detailData.timeline : [];
    const isCurrent = (e: any) => e?.end_date === "至今" || e?.status === "正常";
    const current = events.filter(isCurrent);
    const history = events.filter((e: any) => !isCurrent(e));
    const sortKey = (e: any) => `${e?.start_date || ""}`.replace(/[^\d]/g, "");
    current.sort((a: any, b: any) => sortKey(b).localeCompare(sortKey(a)));
    history.sort((a: any, b: any) => sortKey(b).localeCompare(sortKey(a)));
    const historyMax = 3;
    const visibleHistory = showAllTimeline ? history : history.slice(0, historyMax);
    return { items: [...current, ...visibleHistory], hasHidden: history.length > historyMax };
  }, [detailData?.timeline, showAllTimeline]);

  const shenwanPrefs = (() => {
    const r = detailData?.rsc_info;
    if (!r) return [];
    const items = [
      { name: r.shenwan_1, score: r.shenwan_1_score },
      { name: r.shenwan_2, score: r.shenwan_2_score },
      { name: r.shenwan_3, score: r.shenwan_3_score },
    ]
      .map((it) => {
        const s = Number.parseFloat(String(it.score ?? ""));
        const score = Number.isFinite(s) && s > 0 ? s : 1;
        return { name: String(it.name ?? "").trim(), score };
      })
      .filter((it) => !!it.name);

    const maxScore = Math.max(1, ...items.map((it) => it.score));
    const denom = Math.log1p(maxScore) || 1;
    return items.map((it, idx) => {
      const norm = Math.max(0, Math.min(1, Math.log1p(it.score) / denom));
      return { ...it, norm, pct: norm, rank: idx + 1 };
    });
  })();

  const shenwanPillSegments = (() => {
    if (!shenwanPrefs || shenwanPrefs.length === 0) return [];
    const items = shenwanPrefs.slice(0, 3);
    const total = items.reduce((acc, it) => acc + (Number.isFinite(it.score) ? it.score : 0), 0);
    const raw = total > 0 ? items.map((it) => it.score / total) : items.map(() => 1 / items.length);
    const minPct = 0.08;
    let adj = raw.map((p) => Math.max(p, minPct));
    const sum = adj.reduce((a, b) => a + b, 0);
    if (sum > 1) {
      const idxMax = adj.reduce((best, p, idx) => (p > adj[best] ? idx : best), 0);
      const excess = sum - 1;
      adj[idxMax] = Math.max(minPct, adj[idxMax] - excess);
      const sum2 = adj.reduce((a, b) => a + b, 0);
      if (sum2 > 1.0001) {
        adj = adj.map((p) => p / sum2);
      }
    }
    const colors = ["rgba(200,169,126,0.35)", "rgba(200,169,126,0.22)", "rgba(200,169,126,0.12)"];
    return items.map((it, idx) => ({
      name: it.name,
      pct: adj[idx],
      bg: colors[idx] || colors[colors.length - 1],
      label: adj[idx] < 0.12 ? (() => { const s = String(it.name || "").trim().slice(0, 1); return s ? `${s}…` : ""; })() : it.name,
    }));
  })();

  useEffect(() => {
    if (!detailData || !selectedTalent) return;
    const key = `${selectedTalent.source}:${selectedTalent.id}`;
    if (tabInitKeyRef.current !== key) {
      tabInitKeyRef.current = key;
      setShowAllBehavior(false);
      setShowAllTimeline(false);
      setActiveTab(hasTimeline ? "timeline" : "org");
      return;
    }
    if (activeTab === "org" && !hasOrg && hasTimeline) {
      setActiveTab("timeline");
      return;
    }
    if (activeTab === "timeline" && !hasTimeline && hasOrg) {
      setActiveTab("org");
    }
  }, [detailData, selectedTalent, hasOrg, hasTimeline, activeTab]);

  useEffect(() => {
    if (prevHasTimelineRef.current) return;
    if (!hasTimeline) return;
    prevHasTimelineRef.current = true;
    if (activeTab === "org" && hasOrg) {
      setActiveTab("timeline");
    }
  }, [activeTab, hasOrg, hasTimeline]);

  let activeDaysStr = '';
  let isActiveWithin30Days = false;
  if (detailData?.rsc_info?.last_active_time) {
    const activeDate = new Date(detailData.rsc_info.last_active_time);
    if (!isNaN(activeDate.getTime())) {
      const days = Math.floor((new Date().getTime() - activeDate.getTime()) / (1000 * 3600 * 24));
      if (days === 0) {
        activeDaysStr = '今日活跃';
        isActiveWithin30Days = true;
      } else if (days > 0) {
        if (days < 100) {
          activeDaysStr = `${days}天前活跃`;
        } else if (days < 365) {
          activeDaysStr = `${Math.max(1, Math.floor(days / 30))}个月前活跃`;
        } else {
          activeDaysStr = `${Math.max(1, Math.floor(days / 365))}年前活跃`;
        }
        isActiveWithin30Days = days <= 30;
      }
    }
  }

  const headline = (() => {
    const parts: string[] = [];
    const org = detailData?.institution || detailData?.rsc_info?.cert_org;
    if (org) parts.push(String(org));
    const title = detailData?.rsc_info?.title;
    if (title) parts.push(String(title));
    if (shenwanPrefs?.[0]?.name) parts.push(`偏好行业：${shenwanPrefs[0].name}`);
    if (activeDaysStr) parts.push(activeDaysStr);
    return parts.filter(Boolean).join(" · ");
  })();

  return (
    <div className="min-h-screen flex flex-col items-center p-6 sm:px-12 md:px-24 pt-12 pb-24 w-full max-w-7xl mx-auto font-sans relative">
      
      {/* Background decoration */}
      {homeView === "showcase" && (
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[100vw] h-[500px] bg-gradient-to-b from-slate-100 to-transparent -z-10 pointer-events-none" />
      )}
      
      {!selectedTalent && (
        <>
          {/* Header */}
          {homeView === "showcase" && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              className="w-full text-center space-y-5 mb-10 mt-6"
            >
              <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-slate-900">
                精准连接 <span className="text-slate-500 font-light">资本市场</span>
              </h1>

              <div className="space-y-3">
                <p className="text-slate-500 max-w-2xl mx-auto text-base leading-relaxed">
                  助力上市公司 IR 团队高效建立投资者档案
                </p>
                <div className="flex items-center justify-center gap-3">
                  <div className="flex items-center gap-1.5 text-xs uppercase tracking-widest font-medium text-slate-500 bg-slate-50 px-3 py-1.5 rounded-none border border-slate-200">
                    <Shield className="w-3.5 h-3.5" />
                    <span>基于SAC 、AMAC 与RSC 金融数据库权威来源</span>
                  </div>
                </div>
                <div className="h-3" />
              </div>
            </motion.div>
          )}

          <motion.div 
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="w-full max-w-3xl mx-auto relative z-20"
          >
            <div className="w-full bg-white border border-slate-200 shadow-sm">
              <div className="px-6 pt-5 pb-4 border-b border-slate-100 space-y-4">
                <ModeBar
                  homeView={homeView}
                  mode={mode}
                  onModeChange={(m) => {
                    setMode(m);
                    if (m === "filter") setShowAdvanced(true);
                    enterWorkbench();
                  }}
                  onExit={handleExitWorkbench}
                />
                <div>
                  <div className="text-sm font-semibold text-slate-900">
                    {mode === "search"
                      ? "按姓名/机构快速定位"
                      : mode === "filter"
                        ? "组合条件精准定位"
                        : "一句话描述目标人群"}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {mode === "search"
                      ? "适合已知目标人或机构的高频检索。"
                      : mode === "filter"
                        ? "进入即展开筛选条件，支持一键清空。"
                        : "先对话识别条件，再确认检索。"}
                  </div>
                </div>
              </div>
              <div className="px-6 py-5">
                <AnimatePresence mode="wait">
              {mode === "ai" ? (
                <motion.div
                  key="ai-search"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                  className="w-full"
                >
                  {/* Message List */}
                  {messages.length > 0 && (
                    <div 
                      className="bg-white/80 backdrop-blur-md border border-slate-200 p-6 rounded-none shadow-sm mb-6 flex flex-col gap-4 max-h-[400px] overflow-y-auto custom-scrollbar" 
                      ref={chatContainerRef}
                    >
                      {messages.map((msg, i) => (
                        <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-[80%] p-4 text-sm ${msg.role === 'user' ? 'bg-slate-900 text-white rounded-none' : 'bg-slate-100 text-slate-800 rounded-none border border-slate-200'}`}>
                            {msg.content}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {!pendingFilters && (pendingCandidates || pendingQuickReplies) && (
                    <div className="bg-white border border-slate-200 shadow-sm p-5 mb-6">
                      <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">
                        选择一个方向继续
                      </div>
                      {pendingQuickReplies && pendingQuickReplies.length > 0 && (
                        <div className="flex flex-wrap gap-2 mb-4">
                          {pendingQuickReplies.map((qr) => (
                            <button
                              key={qr.id}
                              type="button"
                              onClick={() => applyQuickReply(qr)}
                              className="px-3 py-1.5 text-sm border border-slate-200 bg-slate-50 text-slate-800 hover:border-slate-300"
                            >
                              {qr.label}
                            </button>
                          ))}
                        </div>
                      )}
                      {pendingCandidates && pendingCandidates.length > 0 && (
                        <div className="grid grid-cols-1 gap-3">
                          {pendingCandidates.map((cand) => (
                            <div key={cand.id} className="border border-slate-200 bg-white p-4">
                              <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                  <div className="text-sm font-semibold text-slate-900">{cand.title}</div>
                                  <div className="text-xs text-slate-500 mt-1">
                                    预计 {cand.estimated_total ?? 0} 人 · {cand.sort_by || "relevance"}
                                  </div>
                                  {cand.rationale && <div className="text-xs text-slate-500 mt-2">{cand.rationale}</div>}
                                </div>
                                <button
                                  type="button"
                                  onClick={() => applyCandidate(cand)}
                                  className="shrink-0 px-3 py-2 text-sm font-medium bg-slate-900 text-white hover:bg-slate-800"
                                >
                                  用这个方案
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Chat Input */}
                  <form onSubmit={handleChatSubmit} className="relative group w-full">
                    <div className={`relative transition-shadow duration-500 ease-out bg-white flex items-center border border-slate-200 ${isFocused ? 'shadow-xl ring-1 ring-slate-900' : 'shadow-sm hover:shadow-md'}`}>
                      <div className="absolute inset-y-0 left-6 flex items-center pointer-events-none">
                        <Sparkles className={`w-5 h-5 transition-colors duration-300 ${isFocused ? 'text-slate-900' : 'text-slate-400'}`} />
                      </div>
                      <input
                        type="text"
                        className="w-full h-16 pl-14 pr-16 bg-transparent border-0 text-lg placeholder:text-slate-400 focus:outline-none focus:ring-0 text-slate-800 rounded-none"
                        placeholder="告诉我你想找什么样的金融人才，例如：'帮我找上海的医药行业研究员'…"
                        value={chatInput}
                        name="ai_query"
                        autoComplete="off"
                        aria-label="AI 智能检索输入"
                        onChange={(e) => setChatInput(e.target.value)}
                        onFocus={() => {
                          setIsFocused(true);
                          enterWorkbench();
                        }}
                        onBlur={() => setIsFocused(false)}
                        disabled={isChatting}
                      />
                      <button 
                        type="submit"
                        disabled={!chatInput.trim() || isChatting}
                        aria-label="发送"
                        className="absolute inset-y-0 right-2 flex items-center justify-center w-12 h-12 text-slate-400 hover:text-slate-900 disabled:opacity-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
                      >
                        {isChatting ? (
                          <div className="w-5 h-5 border-2 border-slate-300 border-t-slate-900 rounded-full animate-spin"></div>
                        ) : (
                          <ArrowRight className="w-6 h-6" />
                        )}
                      </button>
                    </div>
                  </form>

                  {messages.length > 0 && (
                    <div className="mt-3 flex justify-end">
                      <button
                        type="button"
                        onClick={resetAiState}
                        className="text-xs font-medium text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-1.5 bg-white"
                      >
                        清空对话
                      </button>
                    </div>
                  )}
                </motion.div>
              ) : mode === "filter" ? (
                <motion.div
                  key="filter-search"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                  className="w-full"
                >
                  <form onSubmit={handleManualSubmit} className="space-y-6">
                    {/* Basic Inputs */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">姓名</label>
                        <Input 
                          placeholder="请输入人员姓名" 
                          value={nameQuery}
                          name="name"
                          autoComplete="name"
                          onChange={e => setNameQuery(e.target.value)}
                          onFocus={enterWorkbench}
                          className="h-12 text-base rounded-none border-slate-200 focus-visible:ring-slate-900"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">机构</label>
                        <Input 
                          placeholder="请输入机构名称" 
                          value={instQuery}
                          name="institution"
                          autoComplete="organization"
                          onChange={e => setInstQuery(e.target.value)}
                          onFocus={enterWorkbench}
                          className="h-12 text-base rounded-none border-slate-200 focus-visible:ring-slate-900"
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-between gap-3">
                      <button
                        type="button"
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="text-xs font-medium text-slate-500 flex items-center gap-1 hover:text-slate-900 transition-colors"
                      >
                        {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        {showAdvanced ? "收起筛选" : "展开筛选"}
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setNameQuery("");
                          setInstQuery("");
                          setMarketOnlyRsc(false);
                          setRscIsMatched("all");
                          setAdvOrgTypes([]);
                          setMarketTags([]);
                          setAdvShenwan1s([]);
                          setAdvOfficeCities([]);
                          setManualFilter({ type: "group", id: "root", op: "and", children: [] });
                          setShowAdvanced(true);
                        }}
                        className="text-xs font-medium text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-1.5 bg-white"
                      >
                        清空全部
                      </button>
                    </div>

                    {/* Advanced Filters */}
                    <AnimatePresence>
                      {showAdvanced && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="pt-4 border-t border-slate-100 grid grid-cols-1 gap-6">
                            <div className="space-y-4">
                              <div className="flex items-center justify-between">
                                <label className="text-sm font-medium text-slate-700">仅显示 RSC 认证</label>
                                <input 
                                  type="checkbox" 
                                  checked={marketOnlyRsc}
                                  onChange={e => setMarketOnlyRsc(e.target.checked)}
                                  className="w-4 h-4 rounded-none border-slate-300 text-slate-900 focus:ring-slate-900"
                                />
                              </div>
                              
                              <div>
                                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">执业履历匹配状态</label>
                                <select 
                                  value={rscIsMatched}
                                  onChange={e => setRscIsMatched(e.target.value)}
                                  className="w-full text-sm border-slate-200 rounded-none focus:ring-slate-900 focus:border-slate-900 p-2 border"
                                >
                                  <option value="all">不限</option>
                                  <option value="true">完全匹配</option>
                                  <option value="false">存在不一致 (待更新)</option>
                                </select>
                              </div>
                            </div>
                            
                            <div className="space-y-4">
                              <div>
                                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">机构类型 (可多选)</label>
                                <div className="flex flex-wrap gap-2">
                                  {[
                                    { label: "公募基金", value: "公募基金" },
                                    { label: "私募基金", value: "私募基金" },
                                    { label: "券商资管", value: "券商资管" },
                                    { label: "保险资管", value: "保险资管" },
                                    { label: "信托公司", value: "信托公司" },
                                    { label: "银行理财", value: "银行理财" },
                                    { label: "证券公司 (研究所)", value: "证券公司" },
                                  ].map((opt) => (
                                    <button
                                      key={opt.value}
                                      type="button"
                                      onClick={() => {
                                        setAdvOrgTypes((prev) =>
                                          prev.includes(opt.value) ? prev.filter((t) => t !== opt.value) : [...prev, opt.value]
                                        );
                                      }}
                                      className={`text-[11px] px-2 py-1 rounded-none border transition-colors ${
                                        advOrgTypes.includes(opt.value)
                                          ? "bg-slate-800 border-slate-900 text-white"
                                          : "bg-white border-slate-200 text-slate-500 hover:border-slate-300"
                                      }`}
                                    >
                                      {opt.label}
                                    </button>
                                  ))}
                                </div>
                              </div>

                              <div>
                                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">热门关注赛道 (可多选)</label>
                                <div className="flex flex-wrap gap-2">
                                  {filterOptions?.tags?.slice(0, 8).map((tag: string) => (
                                    <button
                                      key={tag}
                                      type="button"
                                      onClick={() => {
                                        setMarketTags(prev => 
                                          prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
                                        );
                                      }}
                                      className={`text-[11px] px-2 py-1 rounded-none border transition-colors ${
                                        marketTags.includes(tag) 
                                          ? 'bg-slate-800 border-slate-900 text-white' 
                                          : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'
                                      }`}
                                    >
                                      {tag}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            </div>
                            
                            <div className="space-y-4">
                              <div>
                                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">关注行业 (申万一级，可多选)</label>
                                <div className="flex flex-wrap gap-2">
                                  {[
                                    "医药生物",
                                    "电子",
                                    "计算机",
                                    "食品饮料",
                                    "电力设备",
                                    "机械设备",
                                    "汽车",
                                    "非银金融",
                                    "银行",
                                    "家用电器",
                                    "传媒",
                                    "通信",
                                    "基础化工",
                                    "国防军工",
                                    "交通运输",
                                  ].map((opt) => (
                                    <button
                                      key={opt}
                                      type="button"
                                      onClick={() => {
                                        setAdvShenwan1s((prev) => (prev.includes(opt) ? prev.filter((t) => t !== opt) : [...prev, opt]));
                                      }}
                                      className={`text-[11px] px-2 py-1 rounded-none border transition-colors ${
                                        advShenwan1s.includes(opt)
                                          ? "bg-slate-800 border-slate-900 text-white"
                                          : "bg-white border-slate-200 text-slate-500 hover:border-slate-300"
                                      }`}
                                    >
                                      {opt}
                                    </button>
                                  ))}
                                </div>
                              </div>
                              <div>
                                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">办公城市</label>
                                <div className="flex flex-wrap gap-2">
                                  {["上海", "北京", "深圳", "广州", "杭州", "成都", "南京", "香港"].map((opt) => (
                                    <button
                                      key={opt}
                                      type="button"
                                      onClick={() => {
                                        setAdvOfficeCities((prev) => (prev.includes(opt) ? prev.filter((t) => t !== opt) : [...prev, opt]));
                                      }}
                                      className={`text-[11px] px-2 py-1 rounded-none border transition-colors ${
                                        advOfficeCities.includes(opt)
                                          ? "bg-slate-800 border-slate-900 text-white"
                                          : "bg-white border-slate-200 text-slate-500 hover:border-slate-300"
                                      }`}
                                    >
                                      {opt}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            </div>
                          </div>
                          <div className="mt-6 pt-6 border-t border-slate-100">
                            <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">自定义筛选器（多维条件）</div>
                            {filterSchema?.fields ? (
                              <FilterBuilder schema={filterSchema.fields} value={manualFilter} onChange={setManualFilter} />
                            ) : (
                              <div className="text-xs text-slate-400">筛选字段加载中...</div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    <button 
                      type="submit"
                      className="w-full bg-slate-900 text-white py-3 font-medium hover:bg-slate-800 transition-colors flex items-center justify-center gap-2"
                    >
                      <Search className="w-4 h-4" /> 搜索档案
                    </button>
                  </form>
                </motion.div>
              ) : (
                <motion.div
                  key="quick-search"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                  className="w-full"
                >
                  <form
                    onSubmit={(e) => {
                      enterWorkbench();
                      handleQuickSubmit(e);
                    }}
                    className="space-y-5"
                  >
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                      <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">姓名</label>
                        <Input
                          placeholder="请输入人员姓名"
                          value={nameQuery}
                          name="name"
                          autoComplete="name"
                          onChange={(e) => setNameQuery(e.target.value)}
                          onFocus={enterWorkbench}
                          className="h-12 text-base rounded-none border-slate-200 focus-visible:ring-slate-900"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">机构</label>
                        <Input
                          placeholder="请输入机构名称"
                          value={instQuery}
                          name="institution"
                          autoComplete="organization"
                          onChange={(e) => setInstQuery(e.target.value)}
                          onFocus={enterWorkbench}
                          className="h-12 text-base rounded-none border-slate-200 focus-visible:ring-slate-900"
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      className="w-full bg-slate-900 text-white py-3.5 font-medium hover:bg-slate-800 transition-colors flex items-center justify-center gap-2"
                    >
                      <Search className="w-4 h-4" /> 搜索档案
                    </button>
                  </form>
                </motion.div>
              )}
            </AnimatePresence>
              </div>

              <div className="border-t border-slate-100 px-6 py-4 space-y-4">
                {mode === "ai" && pendingQuery && pendingFilters && (
                  <div className="bg-white border border-slate-200 px-4 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-slate-900">已识别筛选条件</div>
                        <div className="text-xs text-slate-500 mt-1">请确认后开始检索。</div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          onClick={() => setShowAiConfirmDetails((v) => !v)}
                          className="text-xs font-medium text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-1.5 bg-slate-50"
                        >
                          {showAiConfirmDetails ? "收起条件" : "查看条件"}
                        </button>
                        <button
                          type="button"
                          onClick={handleModifySearch}
                          disabled={isConfirming}
                          className="text-xs font-medium border border-slate-200 text-slate-700 hover:border-slate-300 disabled:opacity-50 transition-colors px-3 py-1.5 bg-white"
                        >
                          修改补充
                        </button>
                        <button
                          type="button"
                          onClick={handleConfirmSearch}
                          disabled={isConfirming}
                          className="text-xs font-medium bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50 transition-colors px-3 py-1.5"
                        >
                          确认检索
                        </button>
                      </div>
                    </div>

                    {showAiConfirmDetails && (
                      <div className="mt-3">
                        {pendingAdvQuery ? (
                          <div className="text-sm">{renderAstNode(JSON.parse(pendingAdvQuery))}</div>
                        ) : (
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(pendingFilters).map(([k, v]) => (
                              <span key={k} className="text-[11px] px-2 py-1 border border-slate-200 bg-slate-50 text-slate-700">
                                {filterLabelMap[k] || k}: {v}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <div>
                  <button
                    type="button"
                    onClick={() => setShowAssistDrawer((v) => !v)}
                    className="w-full flex items-center justify-between gap-3 bg-slate-50 border border-slate-200 px-4 py-3 text-left hover:bg-white transition-colors"
                  >
                    <span className="text-sm font-medium text-slate-700">辅助</span>
                    <span className="text-slate-400">{showAssistDrawer ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}</span>
                  </button>

                  {showAssistDrawer && (
                    <div className="mt-4 space-y-6">
                      <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">热门赛道</div>
                        <div className="flex flex-wrap gap-2">
                          {(filterOptions?.tags || []).slice(0, 12).map((tag: string) => (
                            <button
                              key={tag}
                              type="button"
                              onClick={() => {
                                setMarketTags([tag]);
                                setMode("filter");
                                setShowAdvanced(true);
                                enterWorkbench();
                              }}
                              className="text-[11px] px-2 py-1 rounded-none border border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                            >
                              {tag}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">最近检索</div>
                        {recentSearches.length === 0 ? (
                          <div className="text-xs text-slate-400">暂无记录</div>
                        ) : (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {recentSearches.slice(0, 6).map((it) => (
                              <button
                                key={`${it.name}|${it.institution}|${it.ts}`}
                                type="button"
                                onClick={() => {
                                  setNameQuery(it.name);
                                  setInstQuery(it.institution);
                                  enterWorkbench();
                                }}
                                className="text-left border border-slate-200 bg-white px-3 py-2 hover:bg-slate-50 transition-colors"
                              >
                                <div className="text-sm font-medium text-slate-800 min-w-0 truncate">
                                  {it.name || "—"} {it.institution ? <span className="text-slate-400 font-normal">·</span> : null}{" "}
                                  <span className="text-slate-600 font-normal">{it.institution || ""}</span>
                                </div>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>

                      {homeView === "showcase" && (
                        <div>
                          <div className="flex items-center justify-between gap-3">
                            <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest">趋势看板</div>
                            <button
                              type="button"
                              onClick={() => setShowTrendPanel((v) => !v)}
                              className="text-xs font-medium text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-1.5 bg-white"
                            >
                              {showTrendPanel ? "收起" : "展开"}
                            </button>
                          </div>

                          {showTrendPanel && (
                            <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
                              <Link
                                href="/newest"
                                className="lg:col-span-1 bg-white border border-slate-200 rounded-none p-6 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-slate-50 transition-colors group relative overflow-hidden"
                              >
                                <div className="absolute top-0 right-0 w-16 h-16 bg-slate-50 rounded-bl-full -mr-8 -mt-8 group-hover:scale-150 transition-transform duration-500"></div>
                                <Users className="w-6 h-6 text-slate-400 mb-4 group-hover:text-slate-900 transition-colors relative z-10" />
                                <div className="text-3xl font-semibold text-slate-800 group-hover:text-slate-900 transition-colors tracking-tight relative z-10">
                                  {stats ? stats.total_talents.toLocaleString() : "…"}
                                </div>
                                <div className="text-xs uppercase tracking-widest text-slate-400 mt-3 font-medium flex items-center gap-1 group-hover:text-slate-600 transition-colors relative z-10">
                                  已收录专业人员 <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                                </div>
                                <div className="mt-5 flex gap-6 text-[10px] uppercase tracking-wider text-slate-400 relative z-10">
                                  <span>SAC: {stats ? (stats.sac_talents / 1000).toFixed(1) + "k" : "…"}</span>
                                  <span>AMAC: {stats ? (stats.amac_talents / 1000).toFixed(1) + "k" : "…"}</span>
                                </div>
                              </Link>

                              <div className="lg:col-span-1 bg-white border border-slate-200 rounded-none p-5">
                                <div className="flex items-center justify-between mb-3">
                                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                                    <Tags className="w-3.5 h-3.5" /> 热门关注赛道
                                  </h3>
                                </div>
                                <div className="flex flex-wrap gap-2 mt-3">
                                  {filterOptions && filterOptions.tags ? (
                                    filterOptions.tags.slice(0, 10).map((tag: string, idx: number) => (
                                      <span
                                        key={tag}
                                        className={`text-xs px-2 py-1 rounded-none border ${
                                          idx < 3 ? "bg-amber-50 text-amber-700 border-amber-200 font-medium" : "bg-slate-50 text-slate-600 border-slate-100"
                                        }`}
                                      >
                                        {tag}
                                      </span>
                                    ))
                                  ) : (
                                    <div className="w-full text-center text-xs text-slate-400 py-4">加载中…</div>
                                  )}
                                </div>
                              </div>

                              <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-none p-5 text-white relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-6 opacity-10">
                                  <Target className="w-24 h-24" />
                                </div>
                                <div className="flex items-center justify-between mb-5 relative z-10">
                                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                                    <Clock className="w-3.5 h-3.5" /> 机构高频词
                                  </h3>
                                </div>
                                <div className="space-y-4 relative z-10">
                                  <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                                    <span className="text-sm">百亿级管理规模</span>
                                    <span className="text-xs text-emerald-400 font-mono">+12%</span>
                                  </div>
                                  <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                                    <span className="text-sm">新能源与硬科技</span>
                                    <span className="text-xs text-emerald-400 font-mono">+8%</span>
                                  </div>
                                  <div className="flex justify-between items-center">
                                    <span className="text-sm">量化对冲策略</span>
                                    <span className="text-xs text-emerald-400 font-mono">+15%</span>
                                  </div>
                                </div>
                                <Link href="/newest" className="absolute bottom-5 right-5 text-[10px] uppercase tracking-widest text-slate-400 hover:text-white flex items-center gap-1 transition-colors">
                                  查看最新异动 <ArrowRight className="w-3 h-3" />
                                </Link>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
          
          {/* Footer Update Time */}
          <AnimatePresence>
            {homeView === "showcase" && !selectedTalent && stats && stats.last_updated_at && (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="w-full flex items-center justify-center gap-4 mt-16 text-xs text-slate-400"
              >
                <span>数据最新一次抓取更新时间：{stats.last_updated_at}</span>
                <Link href="/admin" className="text-slate-300 hover:text-brand-500 transition-colors underline decoration-slate-200 underline-offset-4">
                  后台数据大屏
                </Link>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}

      {/* Talent Detail View */}
      <AnimatePresence>
        {selectedTalent && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.2 }}
            className="w-full max-w-5xl mt-6 bg-white rounded-none border border-slate-200 overflow-hidden"
          >
            {/* Action Bar */}
            <div className="px-8 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <button 
                onClick={() => {
                  setSelectedTalent(null);
                  if (fromList === "latest") {
                    window.location.href = `/latest${backQuery || ""}`;
                    return;
                  }
                  if (fromList === "newest") {
                    window.location.href = `/newest${backQuery || ""}`;
                    return;
                  }
                  window.history.pushState({}, '', window.location.pathname);
                }}
                className="text-sm font-medium text-slate-600 hover:text-slate-900 flex items-center gap-2 transition-colors border border-slate-200 bg-white/70 hover:bg-white px-3 py-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
              >
                <ArrowLeft className="w-4 h-4" />
                {fromList === "newest" ? "返回最新入库列表" : fromList === "latest" ? "返回搜索结果" : "返回搜索"}
              </button>
              <div className="flex items-center gap-4">
                <div className="text-xs text-slate-400 font-mono">
                  ID: {selectedTalent.id}
                </div>
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
                {/* Optional Warning Banner */}
                {detailData?.rsc_info?.is_outdated && (
                  <motion.div 
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    transition={{ duration: 0.3, delay: 0.1 }}
                    className="bg-amber-50 border-b border-amber-100 px-8 py-3 flex items-start gap-3"
                  >
                    <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-medium text-amber-800">官方履历发生异动</h4>
                      <p className="text-xs text-amber-700/80 mt-0.5">
                        系统检测到该人员近期可能发生职业变动，RSC 档案标记为待更新状态。建议在路演沟通前重新核实。
                      </p>
                    </div>
                  </motion.div>
                )}

                <div className="flex flex-col md:flex-row">
                  {/* Left Column: Summary */}
                  <div className={`w-full p-10 flex flex-col items-start text-left bg-white ${showSidebar ? "md:w-[65%] md:border-r border-slate-200" : ""}`}>
                    <motion.div 
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.2 }}
                      className="flex items-center gap-4 mb-8 w-full"
                    >
                      {detailData.avatar_url ? (
                        <img 
                          src={detailData.avatar_url} 
                          alt={detailData.name} 
                          width={80}
                          height={80}
                          className="w-20 h-20 rounded-full object-cover bg-slate-100 shrink-0" 
                          onError={(e) => {
                            e.currentTarget.style.display = 'none';
                            e.currentTarget.nextElementSibling?.classList.remove('hidden');
                          }}
                        />
                      ) : null}
                      <div className={`w-20 h-20 rounded-full bg-slate-100 flex items-center justify-center text-3xl font-light text-slate-400 shrink-0 ${detailData?.avatar_url ? 'hidden' : ''}`}>
                        {detailData?.name && detailData.name.length > 0 ? detailData.name.charAt(0) : ''}
                      </div>
                      <div className="w-full">
                        <div className="flex items-center gap-3 mb-2 flex-wrap">
                          <h2 className="text-4xl font-semibold text-slate-900 tracking-tight">{detailData?.name || ''}</h2>
                          {detailData?.rsc_info && (
                            <Badge variant="outline" className="bg-slate-900 text-white hover:bg-slate-800 border-none px-2 py-0.5 font-medium rounded-none">
                              RSC 认证
                            </Badge>
                          )}
                          {detailData?.rsc_info?.value_tags && detailData.rsc_info.value_tags.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              {detailData.rsc_info.value_tags.map((tag: string, i: number) => (
                                <Badge key={i} variant="outline" className="text-[10px] bg-amber-50 text-amber-700 rounded-none border-amber-200 font-normal px-1.5">{tag}</Badge>
                              ))}
                            </div>
                          )}
                          {activeDaysStr && (
                            <Badge variant="outline" className={`border-none px-2 py-0.5 font-medium rounded-none ${isActiveWithin30Days ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-600'}`}>
                              {activeDaysStr}
                            </Badge>
                          )}
                        </div>
                        {headline && (
                          <div className="text-sm text-slate-600 line-clamp-2 text-pretty" title={headline}>
                            {headline}
                          </div>
                        )}
                        {detailData?.rsc_info && (
                          <div className="mt-4 space-y-1.5 text-sm text-slate-600">
                            {detailData.rsc_info.cert_org && (
                              <div className="flex items-center gap-2">
                                <span className="text-slate-400 w-16">机构：</span>
                                <span className="font-medium text-slate-800">{detailData.rsc_info.cert_org}</span>
                              </div>
                            )}
                            {detailData.rsc_info.title && (
                              <div className="flex items-center gap-2">
                                <span className="text-slate-400 w-16">职务：</span>
                                <span className="font-medium text-slate-800">
                                  {detailData.rsc_info.title}
                                  {detailData.rsc_info.department ? `（${detailData.rsc_info.department}）` : ''}
                                </span>
                              </div>
                            )}
                            {(detailData.rsc_info.cert_type || detailData.rsc_info.cert_time) && (
                              <div className="flex items-center gap-2">
                                <span className="text-slate-400 w-16">认证：</span>
                                <span>
                                  {detailData.rsc_info.cert_type && <span className="mr-2">{detailData.rsc_info.cert_type}</span>}
                                  {detailData.rsc_info.cert_time && <span className="text-slate-500">{detailData.rsc_info.cert_time}</span>}
                                </span>
                              </div>
                            )}
                            {detailData?.rsc_info?.uid && (
                              <div className="pt-1">
                                <a
                                  href={`https://console.roadshowchina.cn/user/registered-v2/examine?id=${detailData.rsc_info.uid}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1.5 border border-slate-200 bg-white text-slate-700 px-3 py-1.5 text-xs font-medium hover:bg-slate-50 transition-colors"
                                >
                                  发起对话 <ArrowRight className="w-3 h-3" />
                                </a>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </motion.div>



                    {/* RSC Extended Profile - Aha Moment */}
                    {detailData?.rsc_info && (
                      <motion.div 
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: 0.2 }}
                        className="mt-10 w-full"
                      >
                        <div className="flex justify-between items-center mb-4 border-b border-slate-900 pb-2">
                          <h3 className="text-[11px] font-semibold text-slate-900 uppercase tracking-widest">
                            RSC 深度画像
                          </h3>
                        </div>
                        
                        <div className="space-y-6">
                          {/* 雷达图与机构实力区域 */}
                          {(hasValueScore || hasInfluenceScore || detailData.rsc_info.org_aum) && (
                            <div className="flex flex-col md:flex-row gap-6 items-center">
                              {/* Radar Chart */}
                              {(hasValueScore || hasInfluenceScore) && (
                                <div className="w-full md:w-1/2 h-40 -ml-6 -mt-4">
                                  <ResponsiveContainer width="100%" height="100%">
                                    <RadarChart cx="50%" cy="50%" outerRadius="70%" 
                                      data={[
                                        { subject: '价值分', A: valueScoreForRadar, fullMark: 100 },
                                        { subject: '影响力', A: influenceScoreForRadar, fullMark: 100 },
                                        { subject: '活跃度', A: 85, fullMark: 100 },
                                        { subject: '专业度', A: 90, fullMark: 100 },
                                        { subject: '资金量', A: detailData.rsc_info.org_aum ? 95 : 60, fullMark: 100 },
                                      ]}
                                    >
                                      <PolarGrid stroke="#f1f5f9" />
                                      <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 10 }} />
                                      <Radar name="能力值" dataKey="A" stroke="#8C6A4B" fill="#F5F2EB" fillOpacity={0.6} />
                                    </RadarChart>
                                  </ResponsiveContainer>
                                </div>
                              )}
                              
                              <div className="w-full md:w-1/2 flex flex-col justify-center gap-4">
                                <div className="text-[10px] text-slate-500 mb-1 border-b border-slate-100 pb-1">所在机构实力</div>
                                {detailData.rsc_info.org_aum && (
                                  <div className="flex flex-col">
                                    <span className="text-xl font-semibold text-slate-900">{detailData.rsc_info.org_aum}</span>
                                    <span className="text-[10px] text-slate-400">管理规模</span>
                                  </div>
                                )}
                                <div className="flex gap-4">
                                  {hasValueScore && (
                                    <div className="flex flex-col" title={detailData.rsc_info.org_value_score_desc || "综合考量机构投资实力、投研产出与市场活跃度"}>
                                      <span className="text-base font-semibold text-slate-800">{valueScoreDisplay}</span>
                                      <span className="text-[10px] text-slate-400 border-b border-dashed border-slate-300 cursor-help w-fit">价值评分</span>
                                    </div>
                                  )}
                                  {hasInfluenceScore && (
                                    <div className="flex flex-col" title={detailData.rsc_info.org_influence_score_desc || "综合考量机构在资本市场的发声、关注度及影响力表现"}>
                                      <span className="text-base font-semibold text-slate-800">{influenceScoreDisplay}</span>
                                      <span className="text-[10px] text-slate-400 border-b border-dashed border-slate-300 cursor-help w-fit">影响力</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          )}

                          {shenwanPrefs.length > 0 && (
                            <div>
                              <div className="text-[10px] text-slate-500 mb-2">关注行业</div>
                              <div className="h-8 rounded-full overflow-hidden border border-slate-200 flex bg-white">
                                {shenwanPillSegments.map((seg, idx) => (
                                  <div
                                    key={`${idx}-${seg.name}`}
                                    title={seg.name}
                                    className={`h-8 flex items-center justify-center px-3 min-w-0 text-slate-800 ${idx < shenwanPillSegments.length - 1 ? "border-r border-white/50" : ""}`}
                                    style={{ width: `${(seg.pct * 100).toFixed(2)}%`, backgroundColor: seg.bg }}
                                  >
                                    <span className="text-[11px] font-medium truncate">{seg.label}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {recentFollowCompanies.length > 0 && <RecentFollowCompanies companies={recentFollowCompanies} />}

                          {behaviorBullets.length > 0 && (
                            <div className="border border-slate-200 bg-slate-50 p-4">
                              <div className="flex items-center justify-between mb-2">
                                <div className="text-[10px] text-slate-500 uppercase tracking-widest">行为要点</div>
                                {behaviorBullets.length > 3 && (
                                  <button type="button" className="text-[10px] text-slate-500 hover:text-slate-900" onClick={() => setShowAllBehavior((v) => !v)}>
                                    {showAllBehavior ? "收起" : "展开"}
                                  </button>
                                )}
                              </div>
                              <div className="space-y-1.5">
                                {(showAllBehavior ? behaviorBullets : behaviorBullets.slice(0, 3)).map((t, i) => (
                                  <div key={i} className="flex items-start gap-2 text-sm text-slate-700">
                                    <span className="mt-[6px] w-1 h-1 bg-slate-400 shrink-0" />
                                    <span className="whitespace-normal break-words">{t}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {((detailData.rsc_info.behavior_tags && Object.keys(detailData.rsc_info.behavior_tags).length > 0) || (detailData.rsc_info.research_industries && detailData.rsc_info.research_industries.length > 0)) && (
                            <div>
                              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">投资偏好 & 研究行业</div>
                              <div className="flex flex-wrap gap-1.5">
                                {detailData.rsc_info.behavior_tags['偏好策略'] && String(detailData.rsc_info.behavior_tags['偏好策略']).split(',').map((t: string) => <Badge key={t} variant="outline" className="rounded-none bg-slate-100 text-slate-600 border-slate-200 text-xs font-normal px-2">{t}</Badge>)}
                                {detailData.rsc_info.research_industries && Array.isArray(detailData.rsc_info.research_industries) && detailData.rsc_info.research_industries.map((t: string) => <Badge key={t} variant="outline" className="rounded-none bg-slate-800 text-white border-transparent text-xs font-normal px-2">{t}</Badge>)}
                              </div>
                            </div>
                          )}

                          {detailData.rsc_info.intro && (
                            <div>
                              <div className="text-[10px] text-slate-500 mb-2">个人简介</div>
                              <p className="text-sm text-slate-600 leading-relaxed">
                                {detailData.rsc_info.intro}
                              </p>
                            </div>
                          )}

                          {/* 用户全景信息 移到左侧 */}
                          <div className="pt-8 mt-8 border-t border-slate-100">
                            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4 border-b border-slate-100 pb-2">用户全景信息</h4>
                            <div className="grid grid-cols-1 gap-x-8 gap-y-3 text-sm">
                              {detailData.rsc_info.uid && (
                                <div className="flex items-start gap-4">
                                  <span className="text-slate-400 w-20">RSC UID</span>
                                  <span className="text-slate-900 font-mono break-words">{detailData.rsc_info.uid}</span>
                                </div>
                              )}
                              {detailData.rsc_info.register_time && (
                                <div className="flex items-start gap-4">
                                  <span className="text-slate-400 w-20">注册时间</span>
                                  <span className="text-slate-900 break-words">{detailData.rsc_info.register_time}</span>
                                </div>
                              )}
                              {detailData.rsc_info.org_type && (
                                <div className="flex items-start gap-4">
                                  <span className="text-slate-400 w-20">机构类型</span>
                                  <span className="text-slate-900 break-words">{detailData.rsc_info.org_type}</span>
                                </div>
                              )}
                              {detailData.rsc_info.highest_edu && (
                                <div className="flex items-start gap-4">
                                  <span className="text-slate-400 w-20">最高学历</span>
                                  <span className="text-slate-900 break-words">{detailData.rsc_info.highest_edu}</span>
                                </div>
                              )}
                              {detailData.rsc_info.university && (
                                <div className="flex items-start gap-4 min-w-0">
                                  <span className="text-slate-400 w-20">毕业院校</span>
                                  <span className="text-slate-900 min-w-0 truncate" title={detailData.rsc_info.university}>{detailData.rsc_info.university}</span>
                                </div>
                              )}
                              {detailData.rsc_info.agg_research_industry && (
                                <div className="flex items-start gap-4 min-w-0">
                                  <span className="text-slate-400 w-20">汇总投研行业</span>
                                  <span className="text-slate-900 min-w-0 truncate" title={detailData.rsc_info.agg_research_industry}>{detailData.rsc_info.agg_research_industry}</span>
                                </div>
                              )}
                              {behaviorSummary && (
                                <div className="flex items-start gap-4">
                                  <span className="text-slate-400 w-20">行为汇总</span>
                                  <span className="text-slate-900 text-sm whitespace-normal break-words">{behaviorSummary}</span>
                                </div>
                              )}
                              {detailData.rsc_info.office_address && (
                                <div className="flex items-start gap-4">
                                  <span className="text-slate-400 w-20">办公地址</span>
                                  <span className="text-slate-900 text-sm whitespace-normal break-words">{detailData.rsc_info.office_address}</span>
                                </div>
                              )}
                              {(detailData.rsc_info.mobile_country || detailData.rsc_info.mobile_province) && (
                                <div className="flex items-start gap-4">
                                  <span className="text-slate-400 w-20">手机归属地</span>
                                  <span className="text-slate-900 break-words">{[detailData.rsc_info.mobile_country, detailData.rsc_info.mobile_province].filter(Boolean).join(" · ")}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                    {/* Basic Info (Moved below preferences) */}
                    <div className="w-full space-y-5 pt-8 mt-8 border-t border-slate-100">
                      <div className="flex flex-col">
                        <span className="text-[11px] text-slate-400 uppercase tracking-widest mb-1">当前机构</span>
                        <span className="text-base font-medium text-slate-800">{detailData.institution}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="flex flex-col">
                          <span className="text-[11px] text-slate-400 uppercase tracking-widest mb-1">数据来源</span>
                          <span className="text-sm text-slate-700">{detailData.source}</span>
                        </div>
                        {detailData.education && (
                          <div className="flex flex-col">
                            <span className="text-[11px] text-slate-400 uppercase tracking-widest mb-1">学历</span>
                            <span className="text-sm text-slate-700">{detailData.education}</span>
                          </div>
                        )}
                        {detailData.gender && (
                          <div className="flex flex-col">
                            <span className="text-[11px] text-slate-400 uppercase tracking-widest mb-1">性别</span>
                            <span className="text-sm text-slate-700">{detailData.gender}</span>
                          </div>
                        )}
                        {detailData.cert_no && detailData.cert_no !== "暂无" && (
                          <div className="flex flex-col">
                            <span className="text-[11px] text-slate-400 uppercase tracking-widest mb-1">证书编号</span>
                            <span className="text-sm font-mono text-slate-500">{detailData.cert_no}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Timeline & Ext Data */}
                  {showSidebar && (
                    <div className="w-full md:w-[35%] p-10 bg-slate-50 relative flex flex-col h-full border-l border-slate-200">
                      {hasOrg ? (
                        <div className="mb-6 flex gap-4 border-b border-slate-200">
                          <button
                            className={`pb-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 disabled:opacity-40 disabled:cursor-not-allowed ${resolvedTab === 'timeline' ? 'border-b-2 border-slate-900 text-slate-900' : 'text-slate-400 hover:text-slate-600'}`}
                            onClick={() => {
                              if (!hasTimeline) return;
                              setActiveTab('timeline');
                            }}
                            disabled={!hasTimeline}
                          >
                            官方职业履历
                          </button>
                          <button
                            className={`pb-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 ${resolvedTab === 'org' ? 'border-b-2 border-slate-900 text-slate-900' : 'text-slate-400 hover:text-slate-600'}`}
                            onClick={() => setActiveTab('org')}
                          >
                            机构全景档案
                          </button>
                        </div>
                      ) : (
                        <div className="mb-6">
                          <div className="text-sm font-medium text-slate-900">官方职业履历</div>
                          <div className="mt-2 border-b border-slate-200" />
                        </div>
                      )}
                      
                      <div className="flex-1 overflow-y-auto pr-2">
                        {resolvedTab === 'timeline' ? (
                          detailData.timeline && detailData.timeline.length > 0 ? (
                            <div>
                              <motion.div 
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ duration: 0.5, delay: 0.3 }}
                                className="relative border-l border-slate-200 ml-2 space-y-8 flex-grow"
                              >
                                {timelineDisplay.items.map((event: any, idx: number) => {
                                  const isCurrent = event.end_date === "至今" || event.status === "正常";
                                  return (
                                    <div key={`${idx}-${event.institution}-${event.start_date}`} className={`relative pl-8 transition-opacity ${isCurrent ? 'opacity-100' : 'opacity-60 grayscale-[50%]'}`}>
                                      <div className={`absolute -left-[4px] top-1.5 w-[7px] h-[7px] rounded-full ${isCurrent ? 'bg-slate-900' : 'bg-slate-300'}`} />
                                      
                                      <div className={`-ml-3 pl-3 pr-2 py-2 ${isCurrent ? 'bg-white border border-slate-200' : ''}`}>
                                        <div className="flex flex-col gap-1">
                                          <span className="text-[11px] font-mono text-slate-400">
                                            {event.start_date || "?"} — {event.end_date}
                                          </span>
                                          <h4 className={`text-base font-medium ${isCurrent ? 'text-slate-900' : 'text-slate-600'}`}>
                                            {event.institution}
                                          </h4>
                                        </div>
                                        
                                        <div className="flex items-center gap-2 mt-1">
                                          <span className="text-sm text-slate-500">
                                            {event.role || "专业人员"}
                                          </span>
                                          {event.status && event.status !== "正常" && (
                                            <span className="text-[10px] text-slate-400 border border-slate-200 px-1.5 py-0.5 rounded-none">
                                              {event.status}
                                            </span>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  );
                                })}
                              </motion.div>
                              {timelineDisplay.hasHidden && (
                                <button type="button" className="mt-4 text-xs text-slate-500 hover:text-slate-900" onClick={() => setShowAllTimeline((v) => !v)}>
                                  {showAllTimeline ? "收起" : "展开全部"}
                                </button>
                              )}
                            </div>
                          ) : (
                            <div className="flex flex-col items-center justify-center h-full text-slate-400 py-12">
                              <Search className="w-8 h-8 mb-4 opacity-20" />
                              <p className="text-sm">该用户暂无 SAC/AMAC 官方执业履历记录</p>
                            </div>
                          )
                        ) : (
                          hasOrg && detailData?.rsc_info && (
                            <motion.div 
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              transition={{ duration: 0.3 }}
                              className="space-y-6"
                            >
                              {/* 机构画像 Org Portrait */}
                              {(detailData.rsc_info.org_one_sentence_pos || detailData.rsc_info.org_invest_pos || detailData.rsc_info.org_invest_style || detailData.rsc_info.org_core_figures) && (
                                <div className="bg-white border border-slate-200 p-4">
                                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 border-b border-slate-100 pb-2">机构画像</h4>
                                  <div className="space-y-3 text-sm">
                                    {detailData.rsc_info.org_one_sentence_pos && (
                                      <div>
                                        <span className="text-[10px] text-slate-400 block mb-1">一句话定位</span>
                                        <p className="text-slate-900 text-sm font-medium whitespace-normal break-words">{detailData.rsc_info.org_one_sentence_pos}</p>
                                      </div>
                                    )}
                                    {detailData.rsc_info.org_core_figures && (
                                      <div>
                                        <span className="text-[10px] text-slate-400 block mb-1">核心人物</span>
                                        <p className="text-slate-900 text-sm font-medium whitespace-normal break-words">{detailData.rsc_info.org_core_figures}</p>
                                      </div>
                                    )}
                                    {detailData.rsc_info.org_invest_pos && (
                                      <div>
                                        <span className="text-[10px] text-slate-400 block mb-1">投资定位</span>
                                        <p className="text-slate-900 text-sm font-medium whitespace-normal break-words">{detailData.rsc_info.org_invest_pos}</p>
                                      </div>
                                    )}
                                    {detailData.rsc_info.org_invest_style && (
                                      <div>
                                        <span className="text-[10px] text-slate-400 block mb-1">投资风格</span>
                                        <p className="text-slate-900 text-sm font-medium whitespace-normal break-words">{detailData.rsc_info.org_invest_style}</p>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}

                              <div className="bg-white border border-slate-200 p-4">
                                <div className="flex justify-between items-center mb-3 border-b border-slate-100 pb-2">
                                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">机构信息</h4>
                                  {detailData.rsc_info.org_rsc_profile_url && (
                                    <a href={detailData.rsc_info.org_rsc_profile_url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-blue-600 hover:underline flex items-center gap-1">
                                      查看 RSC 机构主页 <ExternalLink className="w-3 h-3" />
                                    </a>
                                  )}
                                </div>
                                {detailData.rsc_info.org && <div className="text-sm font-medium text-slate-900 whitespace-normal break-words">{detailData.rsc_info.org}</div>}
                                <div className="mt-3 grid grid-cols-1 gap-3 text-sm">
                                  {detailData.rsc_info.org_type && (
                                    <div>
                                      <div className="text-[10px] text-slate-400">机构类型</div>
                                      <div className="text-sm text-slate-900 font-medium whitespace-normal break-words">{detailData.rsc_info.org_type}</div>
                                    </div>
                                  )}
                                  {detailData.rsc_info.org_region && (
                                    <div>
                                      <div className="text-[10px] text-slate-400">国家/地区</div>
                                      <div className="text-sm text-slate-900 font-medium whitespace-normal break-words">{detailData.rsc_info.org_region}</div>
                                    </div>
                                  )}
                                  {detailData.rsc_info.org_is_foreign && (
                                    <div>
                                      <div className="text-[10px] text-slate-400">内外资</div>
                                      <div className="text-sm text-slate-900 font-medium whitespace-normal break-words">{detailData.rsc_info.org_is_foreign}</div>
                                    </div>
                                  )}
                                  {detailData.rsc_info.org_group && (
                                    <div>
                                      <div className="text-[10px] text-slate-400">机构分组</div>
                                      <div className="text-sm text-slate-900 font-medium whitespace-normal break-words">{detailData.rsc_info.org_group}</div>
                                    </div>
                                  )}
                                  {detailData.rsc_info.org_subtype && (
                                    <div>
                                      <div className="text-[10px] text-slate-400">机构子类型</div>
                                      <div className="text-sm text-slate-900 font-medium whitespace-normal break-words">{detailData.rsc_info.org_subtype}</div>
                                    </div>
                                  )}
                                  {detailData.rsc_info.org_aum && (
                                    <div>
                                      <div className="text-[10px] text-slate-400">管理规模</div>
                                      <div className="text-sm text-slate-900 font-medium whitespace-normal break-words">{detailData.rsc_info.org_aum}</div>
                                    </div>
                                  )}
                                  {detailData.rsc_info.org_office_location && (
                                    <div>
                                      <div className="text-[10px] text-slate-400">办公地点</div>
                                      <div className="text-sm text-slate-900 font-medium whitespace-normal break-words">{detailData.rsc_info.org_office_location}</div>
                                    </div>
                                  )}
                                  {detailData.rsc_info.org_value_score && (
                                    <div title={detailData.rsc_info.org_value_score_desc || "综合考量机构投资实力、投研产出与市场活跃度"}>
                                      <div className="text-[10px] text-slate-400 border-b border-dashed border-slate-300 cursor-help w-fit">机构能力分</div>
                                      <div className="text-sm text-slate-900 font-medium whitespace-normal break-words">{detailData.rsc_info.org_value_score}</div>
                                    </div>
                                  )}
                                  {detailData.rsc_info.org_influence_score && (
                                    <div title="综合考量机构在资本市场的发声、关注度及影响力表现">
                                      <div className="text-[10px] text-slate-400 border-b border-dashed border-slate-300 cursor-help w-fit">机构影响力分</div>
                                      <div className="text-sm text-slate-900 font-medium whitespace-normal break-words">{detailData.rsc_info.org_influence_score}</div>
                                    </div>
                                  )}
                                  {detailData.rsc_info.org_tags && detailData.rsc_info.org_tags.length > 0 && (
                                    <div className="pt-2 border-t border-slate-100 flex flex-wrap gap-1.5">
                                      {detailData.rsc_info.org_tags.map((tag: string, i: number) => (
                                        <Badge key={i} variant="outline" className="text-[10px] bg-slate-50 text-slate-600 rounded-none border-slate-200 font-normal px-1.5">{tag}</Badge>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </motion.div>
                          )
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}
