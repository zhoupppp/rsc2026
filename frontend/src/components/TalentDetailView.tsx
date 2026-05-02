"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, AlertCircle, ChevronLeft, ChevronRight, ExternalLink, Search, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import RecentFollowCompanies from "@/components/RecentFollowCompanies";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer } from "recharts";
import { API_BASE_URL } from "@/lib/api";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export type TalentRef = { id: string; source: string };

export default function TalentDetailView({
  talent,
  backLabel,
  onClose,
  canPrev,
  canNext,
  onPrev,
  onNext,
  shareUrl,
  positionText,
  prevTalent,
  nextTalent,
  mode = "page",
}: {
  talent: TalentRef;
  backLabel: string;
  onClose: () => void;
  canPrev?: boolean;
  canNext?: boolean;
  onPrev?: () => void;
  onNext?: () => void;
  shareUrl?: string;
  positionText?: string;
  prevTalent?: TalentRef;
  nextTalent?: TalentRef;
  mode?: "overlay" | "page";
}) {
  const { mutate } = useSWRConfig();
  const [copied, setCopied] = useState(false);
  const [showAllBehavior, setShowAllBehavior] = useState(false);
  const [showAllTimeline, setShowAllTimeline] = useState(false);

  const resolvedShareUrl = useMemo(() => {
    if (shareUrl) return shareUrl;
    if (typeof window === "undefined") return "";
    return window.location.href;
  }, [shareUrl]);

  useEffect(() => {
    setCopied(false);
    setShowAllBehavior(false);
    setShowAllTimeline(false);
  }, [talent.id, talent.source]);

  useEffect(() => {
    const preload = async (t?: TalentRef) => {
      if (!t) return;
      const key = `${API_BASE_URL}/api/talents/${t.source}/${t.id}`;
      try {
        await mutate(key, fetcher(key), { revalidate: false });
      } catch {}
    };
    preload(prevTalent);
    preload(nextTalent);
  }, [mutate, prevTalent?.id, prevTalent?.source, nextTalent?.id, nextTalent?.source]);

  const handleCopy = async () => {
    if (!resolvedShareUrl) return;
    try {
      await navigator.clipboard.writeText(resolvedShareUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
      return;
    } catch {}

    try {
      const ta = document.createElement("textarea");
      ta.value = resolvedShareUrl;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      ta.style.top = "0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {}
  };

  const { data: detailData, isLoading: isLoadingDetail } = useSWR(
    talent ? `${API_BASE_URL}/api/talents/${talent.source}/${talent.id}` : null,
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

  const tabInitKeyRef = useRef<string>("");
  const prevHasTimelineRef = useRef(false);
  const [activeTab, setActiveTab] = useState<"timeline" | "org">("timeline");
  const resolvedTab: "timeline" | "org" = hasOrg && !hasTimeline ? "org" : !hasOrg && hasTimeline ? "timeline" : activeTab;
  const showSidebar = hasTimeline || hasOrg;
  const showSidebarTabs = hasOrg;

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
    return {
      items: [...current, ...visibleHistory],
      hasHidden: history.length > historyMax,
    };
  }, [detailData?.timeline, showAllTimeline]);

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

  const shenwanPrefs = useMemo(() => {
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
  }, [detailData]);

  const shenwanPillSegments = useMemo(() => {
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
  }, [shenwanPrefs]);

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

  useEffect(() => {
    if (prevHasTimelineRef.current) return;
    if (!hasTimeline) return;
    prevHasTimelineRef.current = true;
    if (activeTab === "org" && hasOrg) {
      setActiveTab("timeline");
    }
  }, [activeTab, hasOrg, hasTimeline]);

  useEffect(() => {
    if (!detailData || !talent) return;
    const key = `${talent.source}:${talent.id}`;
    if (tabInitKeyRef.current !== key) {
      tabInitKeyRef.current = key;
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
  }, [detailData, talent, hasOrg, hasTimeline, activeTab]);

  let activeDaysStr = "";
  let isActiveWithin30Days = false;
  if (detailData?.rsc_info?.last_active_time) {
    const activeDate = new Date(detailData.rsc_info.last_active_time);
    if (!Number.isNaN(activeDate.getTime())) {
      const days = Math.floor((new Date().getTime() - activeDate.getTime()) / (1000 * 3600 * 24));
      if (days === 0) {
        activeDaysStr = "今日活跃";
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
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 10 }}
        transition={{ duration: 0.2 }}
        className="w-full bg-white rounded-none border border-slate-200 overflow-hidden"
      >
        <div className="sticky top-0 z-10 px-8 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          {mode === "overlay" ? (
            <div className="min-w-0 flex items-center gap-3">
              <div className="font-semibold text-slate-900 truncate">{detailData?.name || "用户详情"}</div>
              <Badge variant="outline" className="text-[10px] uppercase px-1.5 py-0 rounded-none bg-slate-100 text-slate-600 border-slate-200 shrink-0">
                {talent.source}
              </Badge>
            </div>
          ) : (
            <button
              onClick={onClose}
              className="text-sm font-medium text-slate-600 hover:text-slate-900 flex items-center gap-2 transition-colors border border-slate-200 bg-white/70 hover:bg-white px-3 py-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
            >
              <ArrowLeft className="w-4 h-4" />
              {backLabel}
            </button>
          )}

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 flex-wrap justify-end">
              <button
                type="button"
                onClick={handleCopy}
                disabled={!resolvedShareUrl}
                className="h-9 px-3 border border-slate-200 bg-white text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {copied ? "已复制" : "复制链接"}
              </button>
              {resolvedShareUrl && (
                <a
                  href={resolvedShareUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="h-9 px-3 border border-slate-200 bg-white text-xs font-medium text-slate-600 hover:bg-slate-50 flex items-center gap-1"
                >
                  新窗口 <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
            {(onPrev || onNext) && (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={onPrev}
                  disabled={!onPrev || !canPrev}
                  className="w-9 h-9 border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center"
                  aria-label="上一位"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                {positionText && <div className="text-xs text-slate-400 font-mono min-w-[44px] text-center">{positionText}</div>}
                <button
                  type="button"
                  onClick={onNext}
                  disabled={!onNext || !canNext}
                  className="w-9 h-9 border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center"
                  aria-label="下一位"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
            {mode === "overlay" && (
              <button
                type="button"
                onClick={onClose}
                className="w-9 h-9 border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
                aria-label="关闭弹窗"
              >
                <X className="w-4 h-4" />
              </button>
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
                  <p className="text-xs text-amber-700/80 mt-0.5">系统检测到该人员近期可能发生职业变动，建议在路演沟通前重新核实。</p>
                </div>
              </motion.div>
            )}

            <div className="flex flex-col md:flex-row">
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
                        e.currentTarget.style.display = "none";
                        e.currentTarget.nextElementSibling?.classList.remove("hidden");
                      }}
                    />
                  ) : null}
                  <div className={`w-20 h-20 rounded-full bg-slate-100 flex items-center justify-center text-3xl font-light text-slate-400 shrink-0 ${detailData?.avatar_url ? "hidden" : ""}`}>
                    {detailData?.name && detailData.name.length > 0 ? detailData.name.charAt(0) : ""}
                  </div>
                  <div className="w-full">
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                      <h2 className="text-4xl font-semibold text-slate-900 tracking-tight">{detailData?.name || ""}</h2>
                      {detailData?.rsc_info && (
                        <Badge variant="outline" className="bg-slate-900 text-white hover:bg-slate-800 border-none px-2 py-0.5 font-medium rounded-none">
                          RSC 认证
                        </Badge>
                      )}
                      {detailData?.rsc_info?.value_tags && detailData.rsc_info.value_tags.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {detailData.rsc_info.value_tags.map((tag: string, i: number) => (
                            <Badge key={i} variant="outline" className="text-[10px] bg-amber-50 text-amber-700 rounded-none border-amber-200 font-normal px-1.5">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}
                      {activeDaysStr && (
                        <Badge
                          variant="outline"
                          className={`border-none px-2 py-0.5 font-medium rounded-none ${isActiveWithin30Days ? "bg-emerald-500 text-white" : "bg-slate-200 text-slate-600"}`}
                        >
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
                              {detailData.rsc_info.department ? `（${detailData.rsc_info.department}）` : ""}
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

                {detailData?.rsc_info && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.2 }} className="mt-10 w-full">
                    <div className="flex justify-between items-center mb-4 border-b border-slate-900 pb-2">
                      <h3 className="text-[11px] font-semibold text-slate-900 uppercase tracking-widest">RSC 深度画像</h3>
                    </div>

                    <div className="space-y-6">
                      {(hasValueScore || hasInfluenceScore || detailData.rsc_info.org_aum) && (
                        <div className="flex flex-col md:flex-row gap-6 items-center">
                          {(hasValueScore || hasInfluenceScore) && (
                            <div className="w-full md:w-1/2 h-40 -ml-6 -mt-4">
                              <ResponsiveContainer width="100%" height="100%">
                                <RadarChart
                                  cx="50%"
                                  cy="50%"
                                  outerRadius="70%"
                                  data={[
                                    { subject: "价值分", A: valueScoreForRadar, fullMark: 100 },
                                    { subject: "影响力", A: influenceScoreForRadar, fullMark: 100 },
                                    { subject: "活跃度", A: 85, fullMark: 100 },
                                    { subject: "专业度", A: 90, fullMark: 100 },
                                    { subject: "资金量", A: detailData.rsc_info.org_aum ? 95 : 60, fullMark: 100 },
                                  ]}
                                >
                                  <PolarGrid stroke="#f1f5f9" />
                                  <PolarAngleAxis dataKey="subject" tick={{ fill: "#64748b", fontSize: 10 }} />
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

                      {((detailData.rsc_info.behavior_tags && Object.keys(detailData.rsc_info.behavior_tags).length > 0) ||
                        (detailData.rsc_info.research_industries && detailData.rsc_info.research_industries.length > 0)) && (
                        <div>
                          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">投资偏好 & 研究行业</div>
                          <div className="flex flex-wrap gap-1.5">
                            {detailData.rsc_info.behavior_tags?.["偏好主题"] &&
                              String(detailData.rsc_info.behavior_tags["偏好主题"])
                                .split(",")
                                .map((t: string) => t.trim())
                                .filter(Boolean)
                                .map((t: string) => (
                                  <Badge key={`topic-${t}`} variant="outline" className="rounded-none bg-[#F5F2EB] text-[#8C6A4B] border-[#E8DFD1] text-xs font-normal px-2">
                                    {t}
                                  </Badge>
                                ))}
                            {detailData.rsc_info.behavior_tags?.["偏好赛道"] &&
                              String(detailData.rsc_info.behavior_tags["偏好赛道"])
                                .split(",")
                                .map((t: string) => t.trim())
                                .filter(Boolean)
                                .map((t: string) => (
                                  <Badge key={`track-${t}`} variant="outline" className="rounded-none bg-[#F5F2EB] text-[#8C6A4B] border-[#E8DFD1] text-xs font-normal px-2">
                                    {t}
                                  </Badge>
                                ))}
                            {detailData.rsc_info.behavior_tags?.["偏好策略"] &&
                              String(detailData.rsc_info.behavior_tags["偏好策略"])
                                .split(",")
                                .map((t: string) => t.trim())
                                .filter(Boolean)
                                .map((t: string) => (
                                  <Badge key={`str-${t}`} variant="outline" className="rounded-none bg-slate-100 text-slate-600 border-slate-200 text-xs font-normal px-2">
                                    {t}
                                  </Badge>
                                ))}
                            {Array.isArray(detailData.rsc_info.research_industries) &&
                              detailData.rsc_info.research_industries.map((t: string) => (
                                <Badge key={`ind-${t}`} variant="outline" className="rounded-none bg-slate-800 text-white border-transparent text-xs font-normal px-2">
                                  {t}
                                </Badge>
                              ))}
                          </div>
                        </div>
                      )}

                      {detailData.rsc_info.intro && (
                        <div>
                          <div className="text-[10px] text-slate-500 mb-2">个人简介</div>
                          <p className="text-sm text-slate-600 leading-relaxed">{detailData.rsc_info.intro}</p>
                        </div>
                      )}

                      {behaviorBullets.length > 0 && (
                        <div className="bg-slate-50 border border-slate-200 p-4">
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

                      <div className="pt-8 mt-8 border-t border-slate-100">
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4 border-b border-slate-100 pb-2">用户全景信息</h4>
                        <div className="grid grid-cols-1 gap-x-8 gap-y-3 text-sm">
                          {detailData.rsc_info?.uid && (
                            <div className="flex items-start gap-4">
                              <span className="text-slate-400 w-20">RSC UID</span>
                              <span className="text-slate-900 font-mono break-words">{detailData.rsc_info.uid}</span>
                            </div>
                          )}
                          {detailData.rsc_info?.register_time && (
                            <div className="flex items-start gap-4">
                              <span className="text-slate-400 w-20">注册时间</span>
                              <span className="text-slate-900 break-words">{detailData.rsc_info.register_time}</span>
                            </div>
                          )}
                          {detailData.rsc_info?.org_type && (
                            <div className="flex items-start gap-4">
                              <span className="text-slate-400 w-20">机构类型</span>
                              <span className="text-slate-900 break-words">{detailData.rsc_info.org_type}</span>
                            </div>
                          )}
                          {detailData.rsc_info?.highest_edu && (
                            <div className="flex items-start gap-4">
                              <span className="text-slate-400 w-20">最高学历</span>
                              <span className="text-slate-900 break-words">{detailData.rsc_info.highest_edu}</span>
                            </div>
                          )}
                          {detailData.rsc_info?.university && (
                            <div className="flex items-start gap-4 min-w-0">
                              <span className="text-slate-400 w-20">毕业院校</span>
                              <span className="text-slate-900 min-w-0 truncate" title={detailData.rsc_info.university}>
                                {detailData.rsc_info.university}
                              </span>
                            </div>
                          )}
                          {detailData.rsc_info?.agg_research_industry && (
                            <div className="flex items-start gap-4 min-w-0">
                              <span className="text-slate-400 w-20">汇总投研行业</span>
                              <span className="text-slate-900 min-w-0 truncate" title={detailData.rsc_info.agg_research_industry}>
                                {detailData.rsc_info.agg_research_industry}
                              </span>
                            </div>
                          )}
                          {behaviorSummary && (
                            <div className="flex items-start gap-4">
                              <span className="text-slate-400 w-20">行为汇总</span>
                              <span className="text-slate-900 text-sm whitespace-normal break-words">{behaviorSummary}</span>
                            </div>
                          )}
                          {detailData.rsc_info?.office_address && (
                            <div className="flex items-start gap-4">
                              <span className="text-slate-400 w-20">办公地址</span>
                              <span className="text-slate-900 text-sm whitespace-normal break-words">{detailData.rsc_info.office_address}</span>
                            </div>
                          )}
                          {(detailData.rsc_info?.mobile_country || detailData.rsc_info?.mobile_province) && (
                            <div className="flex items-start gap-4">
                              <span className="text-slate-400 w-20">手机归属地</span>
                              <span className="text-slate-900 break-words">
                                {[detailData.rsc_info.mobile_country, detailData.rsc_info.mobile_province].filter(Boolean).join(" · ")}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

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

              {showSidebar && (
                <div className="w-full md:w-[35%] p-10 bg-slate-50 relative flex flex-col h-full border-l border-slate-200">
                  {showSidebarTabs ? (
                    <div className="mb-6 flex gap-4 border-b border-slate-200">
                      <button
                        className={`pb-2 text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed ${resolvedTab === "timeline" ? "border-b-2 border-slate-900 text-slate-900" : "text-slate-400 hover:text-slate-600"}`}
                        onClick={() => {
                          if (!hasTimeline) return;
                          setActiveTab("timeline");
                        }}
                        disabled={!hasTimeline}
                      >
                        官方职业履历
                      </button>
                      <button
                        className={`pb-2 text-sm font-medium ${resolvedTab === "org" ? "border-b-2 border-slate-900 text-slate-900" : "text-slate-400 hover:text-slate-600"}`}
                        onClick={() => setActiveTab("org")}
                      >
                        机构全景档案
                      </button>
                    </div>
                  ) : (
                    <div className="mb-6">
                      <div className="text-sm font-medium text-slate-900">
                        {hasTimeline ? "官方职业履历" : "机构全景档案"}
                      </div>
                      <div className="mt-2 border-b border-slate-200" />
                    </div>
                  )}

                  <div className="flex-1 overflow-y-auto pr-2">
                    {resolvedTab === "timeline" ? (
                      hasTimeline ? (
                        <div>
                          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.2 }} className="relative border-l border-slate-200 ml-2 space-y-8 flex-grow">
                            {timelineDisplay.items.map((event: any, idx: number) => {
                              const isCurrent = event.end_date === "至今" || event.status === "正常";
                              return (
                                <div
                                  key={`${idx}-${event.institution}-${event.start_date}`}
                                  className={`relative pl-8 transition-opacity ${isCurrent ? "opacity-100" : "opacity-60 grayscale-[50%]"}`}
                                >
                                  <div className={`absolute -left-[4px] top-1.5 w-[7px] h-[7px] rounded-full ${isCurrent ? "bg-slate-900" : "bg-slate-300"}`} />
                                  <div className={`-ml-3 pl-3 pr-2 py-2 ${isCurrent ? "bg-white border border-slate-200" : ""}`}>
                                    <div className="flex flex-col gap-1">
                                      <span className="text-[11px] font-mono text-slate-400">
                                        {event.start_date || "?"} — {event.end_date}
                                      </span>
                                      <h4 className={`text-base font-medium ${isCurrent ? "text-slate-900" : "text-slate-600"}`}>{event.institution}</h4>
                                    </div>
                                    <div className="flex items-center gap-2 mt-1">
                                      <span className="text-sm text-slate-500">{event.role || "专业人员"}</span>
                                      {event.status && event.status !== "正常" && (
                                        <span className="text-[10px] text-slate-400 border border-slate-200 px-1.5 py-0.5 rounded-none">{event.status}</span>
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
                      hasOrg && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }} className="space-y-6">
                          {(detailData.rsc_info.org_one_sentence_pos ||
                            detailData.rsc_info.org_invest_pos ||
                            detailData.rsc_info.org_invest_style ||
                            detailData.rsc_info.org_core_figures) && (
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
                                    <Badge key={i} variant="outline" className="text-[10px] bg-slate-50 text-slate-600 rounded-none border-slate-200 font-normal px-1.5">
                                      {tag}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </motion.div>
                      )
                    )}
                  </div>

                  <div className="pt-4 mt-6 border-t border-slate-200 space-y-2">
                    <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest">档案来源</div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">ID</span>
                      {detailData?.origin_url ? (
                        <a
                          href={detailData.origin_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-slate-900 font-mono hover:text-slate-900 flex items-center gap-1"
                          aria-label="档案 ID"
                        >
                          {talent.id} <ExternalLink className="w-3 h-3 text-slate-400" />
                        </a>
                      ) : (
                        <span className="text-slate-900 font-mono" aria-label="档案 ID">
                          {talent.id}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="p-12 text-center text-slate-500">暂无详情数据</div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
