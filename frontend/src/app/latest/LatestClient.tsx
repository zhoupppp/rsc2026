"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import useSWR from "swr";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  Clock,
  Building2,
  Briefcase,
  ArrowRight,
  Shield,
  AlertCircle,
  Search,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import FilterBuilder, { toAdvQuery, type FilterBuilderValue } from "@/components/FilterBuilder";
import TalentDetailView, { type TalentRef } from "@/components/TalentDetailView";
import { API_BASE_URL } from "@/lib/api";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function LatestClient() {
  const searchParams = useSearchParams();
  const aiQuery = searchParams?.get("ai_query");
  const nameQuery = searchParams?.get("name") || "";
  const instQuery = searchParams?.get("institution") || "";
  const baseAdvQuery = searchParams?.get("adv_query") || "";
  const advOrgTypeParam = searchParams?.get("adv_org_type") || "";

  const loadingQuotes = useMemo(
    () => [
      "优秀的投资者关系管理，是让不确定性变得可定价。",
      "资本市场奖励清晰的叙事，更奖励可验证的信息。",
      "IR 不是“讲故事”，而是持续、透明、可追溯的沟通。",
      "把事实讲清楚，把预期对齐，把节奏稳定住。",
      "市场不缺信息，缺的是结构化的理解与信任。",
      "长期主义在二级市场的表达，往往是高频、真实、耐心的披露。",
    ],
    []
  );
  const [loadingQuoteIndex, setLoadingQuoteIndex] = useState(0);

  const getInitialState = () => {
    if (searchParams) {
      const pageParam = searchParams.get("page");
      const onlyRscParam = searchParams.get("only_rsc");
      const tagsParam = searchParams.get("tags");
      const aumParam = searchParams.get("aum");
      const sortByParam = searchParams.get("sort_by");
      const extraAdvQueryParam = searchParams.get("extra_adv_query");
      const orgSubtypeParam = searchParams.get("org_subtype");
      const certTypeParam = searchParams.get("cert_type");
      const advOrgType = searchParams.get("adv_org_type");
      return {
        page: pageParam ? parseInt(pageParam) : 1,
        onlyRsc: onlyRscParam === "true",
        tags: tagsParam ? tagsParam.split(",") : [],
        aum: aumParam ? aumParam.split(",") : [],
        sortBy: sortByParam || "",
        extraAdvQuery: extraAdvQueryParam || "",
        orgSubtypes: orgSubtypeParam ? orgSubtypeParam.split(",").filter(Boolean) : [],
        certTypes: certTypeParam ? certTypeParam.split(",").filter(Boolean) : [],
        advOrgType: advOrgType || "",
      };
    }
    return { page: 1, onlyRsc: false, tags: [], aum: [], sortBy: "", extraAdvQuery: "", orgSubtypes: [], certTypes: [], advOrgType: "" };
  };

  const initialState = getInitialState();
  const [page, setPage] = useState(initialState.page);
  const [onlyRsc, setOnlyRsc] = useState(initialState.onlyRsc);
  const [selectedTags, setSelectedTags] = useState<string[]>(initialState.tags);
  const [selectedAums, setSelectedAums] = useState<string[]>(initialState.aum);
  const [sortBy, setSortBy] = useState<string>(initialState.sortBy);
  const [advOrgType, setAdvOrgType] = useState<string>(initialState.advOrgType || advOrgTypeParam);
  const [showMoreFilters, setShowMoreFilters] = useState(false);
  const [showAiSource, setShowAiSource] = useState(false);
  const [extraFilter, setExtraFilter] = useState<FilterBuilderValue>({ type: "group", id: "root", op: "and", children: [] });
  const [extraAdvQuery, setExtraAdvQuery] = useState<string>(initialState.extraAdvQuery);
  const [selectedOrgSubtypes, setSelectedOrgSubtypes] = useState<string[]>(initialState.orgSubtypes);
  const [selectedCertTypes, setSelectedCertTypes] = useState<string[]>(initialState.certTypes);
  const [selectedTalent, setSelectedTalent] = useState<TalentRef | null>(null);
  const openedByPushRef = useRef(false);
  const overlayScrollRef = useRef<HTMLDivElement | null>(null);
  const touchRef = useRef<{ x: number; y: number; active: boolean }>({ x: 0, y: 0, active: false });

  const buySideOrg = "公募基金,私募基金,券商资管,保险资管,银行理财";
  const sellSideOrg = "证券公司";
  const intentLabel = advOrgType === buySideOrg ? "买方（机构投资者）" : advOrgType === sellSideOrg ? "卖方（券商研究）" : "不限";

  useEffect(() => {
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("page", page.toString());
      url.searchParams.set("only_rsc", onlyRsc.toString());
      if (sortBy) url.searchParams.set("sort_by", sortBy);
      else url.searchParams.delete("sort_by");

      if (selectedTags.length > 0) url.searchParams.set("tags", selectedTags.join(","));
      else url.searchParams.delete("tags");

      if (selectedAums.length > 0) url.searchParams.set("aum", selectedAums.join(","));
      else url.searchParams.delete("aum");

      if (advOrgType) url.searchParams.set("adv_org_type", advOrgType);
      else url.searchParams.delete("adv_org_type");

      if (extraAdvQuery) {
        url.searchParams.set("extra_adv_query", extraAdvQuery);
      } else {
        url.searchParams.delete("extra_adv_query");
      }

      if (selectedOrgSubtypes.length > 0) url.searchParams.set("org_subtype", selectedOrgSubtypes.join(","));
      else url.searchParams.delete("org_subtype");

      if (selectedCertTypes.length > 0) url.searchParams.set("cert_type", selectedCertTypes.join(","));
      else url.searchParams.delete("cert_type");

      window.history.replaceState({}, "", url.toString());
    }
  }, [page, onlyRsc, selectedTags, selectedAums, sortBy, advOrgType, extraAdvQuery, selectedOrgSubtypes, selectedCertTypes]);

  const { data: filterOptions } = useSWR(`${API_BASE_URL}/api/tags`, fetcher, {
    revalidateOnFocus: false,
  });
  const { data: filterSchema } = useSWR(`${API_BASE_URL}/api/filters/schema`, fetcher, {
    revalidateOnFocus: false,
  });

  const schemaFields = filterSchema?.fields;
  const fieldsByKey = useMemo(() => {
    const m = new Map<string, any>();
    (schemaFields || []).forEach((f: any) => {
      if (f?.key) m.set(String(f.key), f);
    });
    return m;
  }, [schemaFields]);

  const orgSubtypeOptions = useMemo(() => {
    const opts = fieldsByKey.get("org_subtype")?.options || [];
    return Array.isArray(opts) ? opts.slice(0, 12) : [];
  }, [fieldsByKey]);

  const certTypeOptions = useMemo(() => {
    const opts = fieldsByKey.get("cert_type")?.options || [];
    return Array.isArray(opts) ? opts.slice(0, 12) : [];
  }, [fieldsByKey]);

  const buildSearchUrl = () => {
    let url = `${API_BASE_URL}/api/talents/search?page=${page}&size=20`;

    if (searchParams) {
      searchParams.forEach((value, key) => {
        if (
          ![
            "page",
            "size",
            "only_rsc",
            "tags",
            "aum",
            "sort_by",
            "adv_query",
            "extra_adv_query",
            "ai_query",
            "org_subtype",
            "cert_type",
            "id",
            "source",
            "back",
          ].includes(key)
        ) {
          url += `&${key}=${encodeURIComponent(value)}`;
        }
      });
    }

    if (aiQuery || nameQuery || instQuery || baseAdvQuery) url += `&include_rsc=true`;
    if (onlyRsc) url += `&only_rsc=true`;
    if (selectedTags.length > 0) url += `&tags=${encodeURIComponent(selectedTags.join(","))}`;
    if (selectedAums.length > 0) url += `&aum=${encodeURIComponent(selectedAums.join(","))}`;
    if (sortBy) url += `&sort_by=${encodeURIComponent(sortBy)}`;
    if (advOrgType) url += `&adv_org_type=${encodeURIComponent(advOrgType)}`;

    let advQueryStr = baseAdvQuery;
    const quickChildren: any[] = [];
    if (selectedOrgSubtypes.length > 0) quickChildren.push({ field: "org_subtype", op: "in", values: selectedOrgSubtypes });
    if (selectedCertTypes.length > 0) quickChildren.push({ field: "cert_type", op: "in", values: selectedCertTypes });
    if (quickChildren.length > 0) {
      const quickObj = quickChildren.length === 1 ? quickChildren[0] : { op: "and", children: quickChildren };
      try {
        if (advQueryStr) advQueryStr = JSON.stringify({ op: "and", children: [JSON.parse(advQueryStr), quickObj] });
        else advQueryStr = JSON.stringify(quickObj);
      } catch {}
    }
    if (extraAdvQuery) {
      try {
        const extraObj = JSON.parse(extraAdvQuery);
        if (advQueryStr) {
          advQueryStr = JSON.stringify({ op: "and", children: [JSON.parse(advQueryStr), extraObj] });
        } else {
          advQueryStr = JSON.stringify(extraObj);
        }
      } catch {}
    }
    if (advQueryStr) url += `&adv_query=${encodeURIComponent(advQueryStr)}`;
    return url;
  };

  const { data, error, isLoading } = useSWR(buildSearchUrl(), fetcher);

  const defaultSort = useMemo(() => {
    if (sortBy) return sortBy;
    if (aiQuery || nameQuery || instQuery || baseAdvQuery) return "relevance";
    return "latest_job_change";
  }, [aiQuery, nameQuery, instQuery, baseAdvQuery, sortBy]);

  useEffect(() => {
    if (!sortBy) setSortBy(defaultSort);
  }, [defaultSort]);

  useEffect(() => {
    const q = toAdvQuery(extraFilter);
    setExtraAdvQuery(q || "");
    setPage(1);
  }, [extraFilter]);

  useEffect(() => {
    if (!isLoading) return;
    const id = window.setInterval(() => {
      setLoadingQuoteIndex((i) => (i + 1) % loadingQuotes.length);
    }, 2400);
    return () => window.clearInterval(id);
  }, [isLoading, loadingQuotes.length]);

  const openDetail = (id: string, source: string) => {
    const url = new URL(window.location.href);
    url.searchParams.set("id", id);
    url.searchParams.set("source", source);
    openedByPushRef.current = true;
    window.history.pushState({}, "", url.toString());
    setSelectedTalent({ id, source });
  };

  const closeDetail = () => {
    if (openedByPushRef.current) {
      openedByPushRef.current = false;
      window.history.back();
      return;
    }
    const url = new URL(window.location.href);
    url.searchParams.delete("id");
    url.searchParams.delete("source");
    window.history.replaceState({}, "", url.toString());
    setSelectedTalent(null);
  };

  useEffect(() => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    const id = url.searchParams.get("id");
    const source = url.searchParams.get("source");
    if (id && source) {
      openedByPushRef.current = false;
      setSelectedTalent({ id, source });
    }
  }, []);

  useEffect(() => {
    const onPop = () => {
      const url = new URL(window.location.href);
      const id = url.searchParams.get("id");
      const source = url.searchParams.get("source");
      if (id && source) {
        openedByPushRef.current = false;
        setSelectedTalent({ id, source });
      } else {
        openedByPushRef.current = false;
        setSelectedTalent(null);
      }
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const hasData = !!data && Array.isArray((data as any)?.items);
  const items = hasData ? (data as any).items : [];
  const selectedIndex = useMemo(() => {
    if (!selectedTalent) return -1;
    return items.findIndex((it: any) => String(it?.id) === String(selectedTalent.id) && String(it?.source) === String(selectedTalent.source));
  }, [items, selectedTalent]);
  const canPrev = selectedIndex > 0;
  const canNext = selectedIndex >= 0 && selectedIndex < items.length - 1;
  const prevTalent = useMemo(() => {
    if (!canPrev) return undefined;
    const it = items[selectedIndex - 1];
    if (!it) return undefined;
    return { id: String(it.id), source: String(it.source) } satisfies TalentRef;
  }, [canPrev, items, selectedIndex]);
  const nextTalent = useMemo(() => {
    if (!canNext) return undefined;
    const it = items[selectedIndex + 1];
    if (!it) return undefined;
    return { id: String(it.id), source: String(it.source) } satisfies TalentRef;
  }, [canNext, items, selectedIndex]);
  const shareUrl = useMemo(() => {
    if (!selectedTalent) return "";
    if (typeof window === "undefined") return "";
    const listUrl = new URL(window.location.href);
    listUrl.searchParams.delete("id");
    listUrl.searchParams.delete("source");
    const qs = listUrl.searchParams.toString();
    const back = qs ? `?${qs}` : "";
    const detailUrl = new URL("/", window.location.origin);
    detailUrl.searchParams.set("id", String(selectedTalent.id));
    detailUrl.searchParams.set("source", String(selectedTalent.source));
    detailUrl.searchParams.set("from", "latest");
    if (back) detailUrl.searchParams.set("back", back);
    return detailUrl.toString();
  }, [selectedTalent?.id, selectedTalent?.source]);

  const positionText = useMemo(() => {
    if (!selectedTalent) return "";
    const total = items.length;
    if (!Number.isFinite(selectedIndex) || selectedIndex < 0 || total <= 0) return "";
    return `${selectedIndex + 1}/${total}`;
  }, [items.length, selectedIndex, selectedTalent]);

  const navigateIndex = (idx: number) => {
    const it = items[idx];
    if (!it) return;
    const id = String(it.id);
    const source = String(it.source);
    const url = new URL(window.location.href);
    url.searchParams.set("id", id);
    url.searchParams.set("source", source);
    window.history.replaceState({}, "", url.toString());
    setSelectedTalent({ id, source });
  };

  const onPrev = () => {
    if (!canPrev) return;
    navigateIndex(selectedIndex - 1);
  };

  const onNext = () => {
    if (!canNext) return;
    navigateIndex(selectedIndex + 1);
  };

  useEffect(() => {
    if (!selectedTalent) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        closeDetail();
        return;
      }
      const t = e.target as HTMLElement | null;
      const tag = (t?.tagName || "").toUpperCase();
      const isEditable = !!t?.isContentEditable || tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
      if (isEditable) return;

      if (e.key === "ArrowLeft") {
        if (!canPrev) return;
        e.preventDefault();
        onPrev();
        return;
      }
      if (e.key === "ArrowRight") {
        if (!canNext) return;
        e.preventDefault();
        onNext();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedTalent, canPrev, canNext, selectedIndex, items]);

  const onOverlayTouchStart = (e: React.TouchEvent) => {
    if (!selectedTalent) return;
    if (e.touches.length !== 1) return;
    const t = e.target as HTMLElement | null;
    const tag = (t?.tagName || "").toUpperCase();
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    touchRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY, active: true };
  };

  const onOverlayTouchEnd = (e: React.TouchEvent) => {
    if (!selectedTalent) return;
    if (!touchRef.current.active) return;
    touchRef.current.active = false;
    if (e.changedTouches.length !== 1) return;

    const dx = e.changedTouches[0].clientX - touchRef.current.x;
    const dy = e.changedTouches[0].clientY - touchRef.current.y;
    const adx = Math.abs(dx);
    const ady = Math.abs(dy);

    const isHorizontal = adx >= 60 && adx > ady * 1.2;
    const isDownClose = dy >= 90 && ady > adx * 1.2 && (overlayScrollRef.current?.scrollTop || 0) <= 0;

    if (isDownClose) {
      closeDetail();
      return;
    }

    if (!isHorizontal) return;
    if (dx > 0) {
      if (canPrev) onPrev();
      return;
    }
    if (dx < 0) {
      if (canNext) onNext();
    }
  };

  return (
    <div className="min-h-screen font-sans">
      <div className="sticky top-0 z-30 bg-white/90 backdrop-blur border-b border-slate-200">
        <div className="px-6 sm:px-12 md:px-24 py-3 w-full max-w-5xl mx-auto flex items-center justify-between gap-4">
          <Link href="/" className="text-sm font-medium text-slate-600 hover:text-slate-900 flex items-center gap-2 transition-colors">
            <ArrowLeft className="w-4 h-4" /> 返回首页
          </Link>
          <div className="text-xs text-slate-400">
            {hasData ? `共 ${Number((data as any)?.total || 0).toLocaleString()} 条` : " "}
          </div>
        </div>
      </div>

      <div className="p-6 sm:px-12 md:px-24 pt-8 pb-24 w-full max-w-5xl mx-auto">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-semibold text-slate-900 flex items-center gap-3">搜索结果</h1>
            <p className="text-slate-500 mt-2">
              {(nameQuery || instQuery) && (
                <>
                  {(nameQuery && `姓名包含「${nameQuery}」`) || ""}
                  {nameQuery && instQuery ? "，" : ""}
                  {(instQuery && `机构包含「${instQuery}」`) || ""}
                </>
              )}
              {!nameQuery && !instQuery && "按条件筛选平台专业人员"}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer text-sm font-medium text-slate-700 bg-slate-50 px-4 py-2 rounded-none border border-slate-200 hover:bg-slate-100 transition-colors">
              <input
                type="checkbox"
                checked={onlyRsc}
                onChange={(e) => {
                  setOnlyRsc(e.target.checked);
                  setPage(1);
                }}
                className="w-4 h-4 rounded-none border-slate-300 text-slate-900 focus:ring-slate-900"
              />
              仅看 RSC 已认证
            </label>

            <div className="flex items-center border border-slate-200 bg-white">
              <button
                type="button"
                onClick={() => {
                  setAdvOrgType("");
                  if (!sortBy) setSortBy("relevance");
                  setPage(1);
                }}
                className={`px-3 py-2 text-sm font-medium ${advOrgType ? "text-slate-600 hover:text-slate-900" : "bg-slate-900 text-white"}`}
              >
                不限
              </button>
              <button
                type="button"
                onClick={() => {
                  setAdvOrgType(buySideOrg);
                  setSortBy("relevance");
                  setPage(1);
                }}
                className={`px-3 py-2 text-sm font-medium border-l border-slate-200 ${
                  advOrgType === buySideOrg ? "bg-slate-900 text-white" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                买方
              </button>
              <button
                type="button"
                onClick={() => {
                  setAdvOrgType(sellSideOrg);
                  setSortBy("relevance");
                  setPage(1);
                }}
                className={`px-3 py-2 text-sm font-medium border-l border-slate-200 ${
                  advOrgType === sellSideOrg ? "bg-slate-900 text-white" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                卖方
              </button>
            </div>

            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(1);
              }}
              className="text-sm border border-slate-200 rounded-none px-3 py-2 bg-white text-slate-700"
            >
              <option value="relevance">默认：相关性排序</option>
              <option value="latest_job_change">最新任职变动</option>
              <option value="recent_active">最近活跃</option>
              <option value="latest_cert">最新认证</option>
              <option value="latest_register">最新注册</option>
            </select>
          </div>
        </div>

        {aiQuery && (
          <div className="bg-white border border-slate-200 px-4 py-3 mb-6 flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className={`text-sm text-slate-700 ${showAiSource ? "" : "truncate"}`}>AI 检索来源：{aiQuery}</div>
              <div className="text-xs text-slate-500 mt-1">意图：{intentLabel}</div>
            </div>
            <button
              type="button"
              onClick={() => setShowAiSource((v) => !v)}
              className="text-xs font-medium text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-1.5 bg-slate-50 shrink-0"
            >
              {showAiSource ? "收起" : "展开"}
            </button>
          </div>
        )}

        <div className="bg-white border border-slate-200 p-4 mb-6 relative z-20">
          <div className="flex items-center justify-between gap-4">
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-widest flex items-center gap-1">
              <Search className="w-3.5 h-3.5" /> 快捷筛选
            </span>
            <div className="flex items-center gap-2">
              {(selectedOrgSubtypes.length > 0 || selectedCertTypes.length > 0) && (
                <button
                  type="button"
                  onClick={() => {
                    setSelectedOrgSubtypes([]);
                    setSelectedCertTypes([]);
                    setPage(1);
                  }}
                  className="text-xs font-medium text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-1.5 bg-white"
                >
                  清空快捷筛选
                </button>
              )}
              <button
                type="button"
                onClick={() => setShowMoreFilters((v) => !v)}
                className="text-xs font-medium text-slate-500 hover:text-slate-900 flex items-center gap-1 border border-slate-200 px-3 py-1.5 bg-slate-50"
              >
                <SlidersHorizontal className="w-3.5 h-3.5" />
                更多筛选
                {showMoreFilters ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          <div className="mt-4 space-y-3">
            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-[11px] text-slate-400 font-semibold uppercase tracking-widest mr-2">机构子类</span>
              {orgSubtypeOptions.length > 0 ? (
                orgSubtypeOptions.map((opt: string) => (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => {
                      setSelectedOrgSubtypes((prev) => (prev.includes(opt) ? prev.filter((x) => x !== opt) : [...prev, opt]));
                      setPage(1);
                    }}
                    className={`text-[11px] px-3 py-1.5 rounded-none border transition-all ${
                      selectedOrgSubtypes.includes(opt)
                        ? "bg-slate-800 border-slate-900 text-white font-medium"
                        : "bg-white border-slate-200 text-slate-500 hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    {opt}
                  </button>
                ))
              ) : (
                <span className="text-[11px] text-slate-400">加载中...</span>
              )}
            </div>

            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-[11px] text-slate-400 font-semibold uppercase tracking-widest mr-2">认证类型</span>
              {certTypeOptions.length > 0 ? (
                certTypeOptions.map((opt: string) => (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => {
                      setSelectedCertTypes((prev) => (prev.includes(opt) ? prev.filter((x) => x !== opt) : [...prev, opt]));
                      setPage(1);
                    }}
                    className={`text-[11px] px-3 py-1.5 rounded-none border transition-all ${
                      selectedCertTypes.includes(opt)
                        ? "bg-amber-50 border-amber-200 text-amber-700 font-medium"
                        : "bg-white border-slate-200 text-slate-500 hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    {opt}
                  </button>
                ))
              ) : (
                <span className="text-[11px] text-slate-400">加载中...</span>
              )}
            </div>
          </div>
        </div>

        {showMoreFilters && (
          <div className="bg-white border border-slate-200 p-4 mb-6">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">更多筛选条件</div>
            <FilterBuilder schema={schemaFields} value={extraFilter} onChange={setExtraFilter} />
          </div>
        )}

        <div className="bg-white rounded-none border border-slate-200 overflow-hidden">
          {isLoading ? (
            <div className="p-24 flex flex-col items-center justify-center space-y-4">
              <div className="w-8 h-8 border-2 border-slate-200 border-t-slate-800 rounded-full animate-spin"></div>
              <div className="text-sm text-slate-400">正在检索...</div>
              <div className="text-xs text-slate-400 max-w-[520px] text-center leading-relaxed">{loadingQuotes[loadingQuoteIndex]}</div>
            </div>
          ) : error || !hasData ? (
            <div className="p-12">
              <div className="text-lg font-semibold text-slate-900">暂时无法获取搜索结果</div>
              <div className="text-sm text-slate-500 mt-2">
                {error ? "服务可能未启动或网络异常。请稍后重试，或调整筛选条件。" : "返回结果为空，可能是服务未响应。请稍后重试。"}
              </div>
              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowMoreFilters(true);
                    setPage(1);
                  }}
                  className="px-4 py-2 rounded-none border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  调整筛选条件
                </button>
                <Link
                  href="/newest"
                  className="px-4 py-2 rounded-none border border-slate-900 bg-slate-900 text-sm font-medium text-white hover:bg-slate-800 transition-colors"
                >
                  看看最新入库
                </Link>
              </div>
            </div>
          ) : items.length === 0 ? (
            <div className="p-12">
              <div className="text-lg font-semibold text-slate-900">未搜索到匹配结果</div>
              {(data as any)?.meta?.suggestion && (
                <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2 mt-3">
                  {(data as any).meta.suggestion}
                </div>
              )}
              <div className="text-sm text-slate-500 mt-2">建议你尝试以下方式提高命中率：</div>
              <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-slate-600">
                <div className="border border-slate-200 bg-slate-50 p-3">放宽条件：减少机构子类/认证类型的限制</div>
                <div className="border border-slate-200 bg-slate-50 p-3">尝试“最新任职变动/最近活跃”等排序查看相近人群</div>
                <div className="border border-slate-200 bg-slate-50 p-3">改用更短的机构关键词（例如只输入“东方”）</div>
                <div className="border border-slate-200 bg-slate-50 p-3">展开“更多筛选”组合更多条件（行业、地区等）</div>
              </div>
              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowMoreFilters(true);
                    setPage(1);
                  }}
                  className="px-4 py-2 rounded-none border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  打开更多筛选
                </button>
                <Link
                  href="/newest"
                  className="px-4 py-2 rounded-none border border-slate-900 bg-slate-900 text-sm font-medium text-white hover:bg-slate-800 transition-colors"
                >
                  看看最新入库
                </Link>
              </div>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {items.map((item: any) => (
                <button
                  key={`${item.source}-${item.id}`}
                  type="button"
                  onClick={() => openDetail(String(item.id), String(item.source))}
                  className="w-full text-left p-6 hover:bg-slate-50 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4 group"
                >
                <div className="flex items-center gap-4">
                  {item.avatar_url ? (
                    <img
                      src={item.avatar_url}
                      alt={item.name}
                      width={48}
                      height={48}
                      loading="lazy"
                      className="w-12 h-12 rounded-full object-cover border border-slate-200 shrink-0"
                      onError={(e) => {
                        e.currentTarget.style.display = "none";
                        e.currentTarget.nextElementSibling?.classList.remove("hidden");
                      }}
                    />
                  ) : null}
                  <div
                    className={`w-12 h-12 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-xl text-slate-400 font-medium shrink-0 ${
                      item.avatar_url ? "hidden" : ""
                    }`}
                  >
                    {item.name.charAt(0)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-lg text-slate-900 group-hover:text-slate-600 transition-colors">{item.name}</span>
                      <Badge
                        variant="outline"
                        className="text-[10px] uppercase px-1.5 py-0 rounded-none bg-slate-100 text-slate-600 border-slate-200"
                      >
                        {item.source}
                      </Badge>
                      {item.is_rsc && (
                        <div className="flex items-center">
                          <Badge
                            variant="outline"
                            className="bg-slate-900 text-white border-none px-1.5 py-0 text-[10px] flex items-center gap-1 shrink-0 rounded-none"
                          >
                            <Shield className="w-2.5 h-2.5" /> RSC 已认证
                          </Badge>
                          {item.is_outdated && (
                            <div className="ml-1.5 flex items-center gap-1 text-[10px] font-medium text-amber-700 bg-amber-50 px-1.5 py-0 border border-amber-200/50 shrink-0 rounded-none">
                              <AlertCircle className="w-2.5 h-2.5" /> 待更新
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="text-sm text-slate-500 flex items-center gap-3 mt-1">
                      <span className="flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5" /> {item.institution}
                      </span>
                      {item.title && (
                        <span className="flex items-center gap-1.5">
                          <Briefcase className="w-3.5 h-3.5" /> {item.title}
                        </span>
                      )}
                    </div>
                    {((item.top_tags && item.top_tags.length > 0) || (item.pref_industries_top3 && item.pref_industries_top3.length > 0)) && (
                      <div className="flex gap-1.5 mt-1.5">
                        {(item.top_tags || []).map((tag: string, idx: number) => (
                          <span key={`t-${idx}`} className="text-[10px] bg-amber-50 text-amber-700 px-1.5 py-0.5 border border-amber-100/50">
                            {tag}
                          </span>
                        ))}
                        {(item.pref_industries_top3 || []).map((tag: string, idx: number) => (
                          <span key={`p-${idx}`} className="text-[10px] bg-amber-50 text-amber-700 px-1.5 py-0.5 border border-amber-100/50">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex flex-col sm:items-end gap-1 shrink-0">
                  <div className="text-xs text-slate-400 flex items-center gap-1 mt-2 sm:mt-0">
                    <Clock className="w-3 h-3" /> 任职登记日期 {item.reg_date || item.updated_at?.split(" ")[0] || "未知"}
                  </div>
                  <span className="text-xs font-medium text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 justify-end">
                    查看详情 <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {hasData && Number((data as any)?.total || 0) > 0 && (
          <div className="flex items-center justify-center gap-4 mt-8">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 rounded-none border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              上一页
            </button>
            <span className="text-sm text-slate-500">
              第 {page} 页 / 共 {Math.ceil(Number((data as any)?.total || 0) / 20)} 页
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= Math.ceil(Number((data as any)?.total || 0) / 20)}
              className="px-4 py-2 rounded-none border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              下一页
            </button>
          </div>
        )}
      </div>

      {selectedTalent && (
        <div className="fixed inset-0 z-[100]">
          <div className="absolute inset-0 bg-black/20" onClick={closeDetail} />
          <div
            ref={overlayScrollRef}
            className="absolute inset-0 overflow-y-auto overscroll-contain"
            onTouchStart={onOverlayTouchStart}
            onTouchEnd={onOverlayTouchEnd}
          >
            <div className="min-h-full px-6 sm:px-12 md:px-24 pt-20 pb-24 w-full max-w-7xl mx-auto">
              <TalentDetailView
                talent={selectedTalent}
                backLabel="返回搜索结果"
                onClose={closeDetail}
                mode="overlay"
                shareUrl={shareUrl}
                positionText={positionText}
                canPrev={canPrev}
                canNext={canNext}
                onPrev={onPrev}
                onNext={onNext}
                prevTalent={prevTalent}
                nextTalent={nextTalent}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
