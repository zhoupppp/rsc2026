"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, Clock, Building2, Briefcase, ArrowRight, Shield, AlertCircle, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import TalentDetailView, { type TalentRef } from "@/components/TalentDetailView";
import { API_BASE_URL } from "@/lib/api";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function NewestClient() {
  const searchParams = useSearchParams();

  const getInitialState = () => {
    if (searchParams) {
      const pageParam = searchParams.get("page");
      const onlyRscParam = searchParams.get("only_rsc");
      const tagsParam = searchParams.get("tags");
      const aumParam = searchParams.get("aum");
      const sortByParam = searchParams.get("sort_by");
      const orgSubtypeParam = searchParams.get("org_subtype");
      const certTypeParam = searchParams.get("cert_type");
      const outdatedParam = searchParams.get("outdated");
      return {
        page: pageParam ? parseInt(pageParam) : 1,
        onlyRsc: onlyRscParam === "true",
        tags: tagsParam ? tagsParam.split(",") : [],
        aum: aumParam ? aumParam.split(",") : [],
        sortBy: sortByParam || "",
        orgSubtypes: orgSubtypeParam ? orgSubtypeParam.split(",").filter(Boolean) : [],
        certTypes: certTypeParam ? certTypeParam.split(",").filter(Boolean) : [],
        onlyOutdated: outdatedParam === "true",
      };
    }
    return { page: 1, onlyRsc: false, tags: [], aum: [], sortBy: "", orgSubtypes: [], certTypes: [], onlyOutdated: false };
  };

  const initialState = getInitialState();
  const [page, setPage] = useState(initialState.page);
  const [onlyRsc, setOnlyRsc] = useState(initialState.onlyRsc);
  const [selectedTags, setSelectedTags] = useState<string[]>(initialState.tags);
  const [selectedAums, setSelectedAums] = useState<string[]>(initialState.aum);
  const [sortBy, setSortBy] = useState<string>(initialState.sortBy || "latest_added");
  const [selectedOrgSubtypes, setSelectedOrgSubtypes] = useState<string[]>(initialState.orgSubtypes);
  const [selectedCertTypes, setSelectedCertTypes] = useState<string[]>(initialState.certTypes);
  const [onlyOutdated, setOnlyOutdated] = useState<boolean>(initialState.onlyOutdated);
  const [selectedTalent, setSelectedTalent] = useState<TalentRef | null>(null);
  const openedByPushRef = useRef(false);
  const overlayScrollRef = useRef<HTMLDivElement | null>(null);
  const touchRef = useRef<{ x: number; y: number; active: boolean }>({ x: 0, y: 0, active: false });

  useEffect(() => {
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("page", page.toString());
      url.searchParams.set("only_rsc", onlyRsc.toString());
      if (sortBy) url.searchParams.set("sort_by", sortBy);
      else url.searchParams.delete("sort_by");

      if (selectedTags.length > 0) {
        url.searchParams.set("tags", selectedTags.join(","));
      } else {
        url.searchParams.delete("tags");
      }

      if (selectedAums.length > 0) {
        url.searchParams.set("aum", selectedAums.join(","));
      } else {
        url.searchParams.delete("aum");
      }

      if (selectedOrgSubtypes.length > 0) url.searchParams.set("org_subtype", selectedOrgSubtypes.join(","));
      else url.searchParams.delete("org_subtype");

      if (selectedCertTypes.length > 0) url.searchParams.set("cert_type", selectedCertTypes.join(","));
      else url.searchParams.delete("cert_type");

      if (onlyOutdated) url.searchParams.set("outdated", "true");
      else url.searchParams.delete("outdated");

      window.history.replaceState({}, "", url.toString());
    }
  }, [page, onlyRsc, selectedTags, selectedAums, sortBy, selectedOrgSubtypes, selectedCertTypes, onlyOutdated]);

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

  const buildUrl = () => {
    const resolvedSortBy = sortBy || "latest_added";
    let url = `${API_BASE_URL}/api/talents/search?page=${page}&size=20&sort_by=${encodeURIComponent(resolvedSortBy)}`;
    if (onlyRsc) url += `&only_rsc=true`;
    if (selectedTags.length > 0) url += `&tags=${encodeURIComponent(selectedTags.join(","))}`;
    if (selectedAums.length > 0) url += `&aum=${encodeURIComponent(selectedAums.join(","))}`;

    const quickChildren: any[] = [];
    if (selectedOrgSubtypes.length > 0) quickChildren.push({ field: "org_subtype", op: "in", values: selectedOrgSubtypes });
    if (selectedCertTypes.length > 0) quickChildren.push({ field: "cert_type", op: "in", values: selectedCertTypes });
    if (onlyOutdated) quickChildren.push({ field: "is_outdated", op: "eq", value: "true" });
    if (quickChildren.length > 0) {
      const quickObj = quickChildren.length === 1 ? quickChildren[0] : { op: "and", children: quickChildren };
      url += `&adv_query=${encodeURIComponent(JSON.stringify(quickObj))}`;
    }
    return url;
  };

  const { data, isLoading } = useSWR(buildUrl(), fetcher);

  const items = useMemo(() => {
    const arr = (data as any)?.items;
    return Array.isArray(arr) ? arr : [];
  }, [data]);

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
    detailUrl.searchParams.set("from", "newest");
    if (back) detailUrl.searchParams.set("back", back);
    return detailUrl.toString();
  }, [selectedTalent?.id, selectedTalent?.source]);

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
    <div className="min-h-screen p-6 sm:px-12 md:px-24 pb-24 w-full max-w-5xl mx-auto font-sans">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
        <div className="min-w-0 flex-1">
          <Link
            href="/"
            className="text-sm font-medium text-slate-500 hover:text-slate-900 flex items-center gap-2 mb-4 transition-colors w-fit"
          >
            <ArrowLeft className="w-4 h-4" /> 返回首页
          </Link>
          <h1 className="text-3xl font-semibold text-slate-900 flex items-center gap-3">最新入库人员</h1>
          <p className="text-slate-500 mt-2">按最新入库时间查看平台最近抓取更新的专业人员名单</p>
        </div>

        <div className="shrink-0 w-full sm:w-auto overflow-x-auto sm:overflow-visible">
          <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 sm:gap-3 justify-start sm:justify-end whitespace-nowrap">
            <label className="inline-flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700 bg-slate-50 px-3 h-9 rounded-none border border-slate-200 hover:bg-slate-100 transition-colors">
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

            <label className="inline-flex items-center gap-2 cursor-pointer text-xs font-medium text-amber-700 bg-amber-50 px-3 h-9 rounded-none border border-amber-200 hover:bg-amber-100/60 transition-colors">
            <input
              type="checkbox"
              checked={onlyOutdated}
              onChange={(e) => {
                setOnlyOutdated(e.target.checked);
                setPage(1);
              }}
              className="w-4 h-4 rounded-none border-amber-300 text-amber-700 focus:ring-amber-700"
            />
            仅看待更新
          </label>

            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(1);
              }}
              aria-label="排序方式"
              className="h-9 text-xs border border-slate-200 rounded-none px-3 bg-white text-slate-700"
            >
              <option value="latest_added">默认：最新入库</option>
              <option value="latest_job_change">最新任职变动</option>
              <option value="recent_active">最近活跃</option>
              <option value="latest_cert">最新认证</option>
              <option value="latest_register">最新注册</option>
            </select>
          </div>
        </div>
      </div>

      <div className="bg-white border border-slate-200 p-4 mb-6 relative z-20 space-y-3">
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-xs text-slate-400 font-semibold uppercase tracking-widest mr-2 flex items-center gap-1">
            <Search className="w-3.5 h-3.5" /> 快捷筛选
          </span>
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
                className={`text-[11px] px-3 py-1.5 rounded-none border transition-colors ${
                  selectedOrgSubtypes.includes(opt)
                    ? "bg-slate-800 border-slate-900 text-white font-medium"
                    : "bg-white border-slate-200 text-slate-500 hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                {opt}
              </button>
            ))
          ) : (
            <span className="text-[11px] text-slate-400">加载中…</span>
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
                className={`text-[11px] px-3 py-1.5 rounded-none border transition-colors ${
                  selectedCertTypes.includes(opt)
                    ? "bg-amber-50 border-amber-200 text-amber-700 font-medium"
                    : "bg-white border-slate-200 text-slate-500 hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                {opt}
              </button>
            ))
          ) : (
            <span className="text-[11px] text-slate-400">加载中…</span>
          )}
        </div>

        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-[11px] text-slate-400 font-semibold uppercase tracking-widest mr-2">热门标签</span>
          {filterOptions?.tags?.slice(0, 10).map((tag: string) => (
            <button
              key={tag}
              type="button"
              onClick={() => {
                setSelectedTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag].slice(0, 2)));
                setPage(1);
              }}
              className={`text-[11px] px-3 py-1.5 rounded-none border transition-colors ${
                selectedTags.includes(tag)
                  ? "bg-amber-50 border-amber-200 text-amber-700 font-medium"
                  : "bg-white border-slate-200 text-slate-500 hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              {tag}
            </button>
          ))}

          <div className="w-px h-4 bg-slate-200 mx-2"></div>

          <span className="text-[11px] text-slate-400 font-semibold uppercase tracking-widest mr-2">管理规模</span>
          {filterOptions?.aums?.map((aum: string) => (
            <button
              key={aum}
              type="button"
              onClick={() => {
                setSelectedAums((prev) => (prev.includes(aum) ? prev.filter((a) => a !== aum) : [aum]));
                setPage(1);
              }}
              className={`text-[11px] px-3 py-1.5 rounded-none border transition-colors ${
                selectedAums.includes(aum)
                  ? "bg-slate-800 border-slate-900 text-white font-medium"
                  : "bg-white border-slate-200 text-slate-500 hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              {aum}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-none border border-slate-200 overflow-hidden">
        {isLoading ? (
          <div className="p-24 flex flex-col items-center justify-center space-y-4">
            <div className="w-8 h-8 border-2 border-slate-200 border-t-slate-800 rounded-full animate-spin"></div>
            <div className="text-sm text-slate-400">正在检索...</div>
          </div>
        ) : data?.items?.length === 0 ? (
          <div className="p-12 text-center text-slate-500">暂无数据</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {items.map((item: any) => (
              <button
                type="button"
                onClick={() => openDetail(String(item.id), String(item.source))}
                key={`${item.source}-${item.id}`}
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
                    <Clock className="w-3 h-3" /> 入库时间 {item.updated_at?.split(" ")[0] || "未知"}
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

      {data && data.total > 0 && (
        <div className="flex items-center justify-center gap-4 mt-8">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 rounded-none border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            上一页
          </button>
          <span className="text-sm text-slate-500">
            第 {page} 页 / 共 {Math.ceil(data.total / 20)} 页
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(data.total / 20)}
            className="px-4 py-2 rounded-none border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            下一页
          </button>
        </div>
      )}

      {selectedTalent && (
        <div className="fixed inset-0 z-[100]">
          <button type="button" aria-label="关闭详情" className="absolute inset-0 bg-black/20" onClick={closeDetail} />
          <div
            ref={overlayScrollRef}
            className="absolute inset-0 overflow-y-auto overscroll-contain"
            onTouchStart={onOverlayTouchStart}
            onTouchEnd={onOverlayTouchEnd}
          >
            <div className="min-h-full px-6 sm:px-12 md:px-24 pt-20 pb-24 w-full max-w-7xl mx-auto">
              <TalentDetailView
                talent={selectedTalent}
                backLabel="返回最新入库"
                onClose={closeDetail}
                mode="overlay"
                shareUrl={shareUrl}
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
