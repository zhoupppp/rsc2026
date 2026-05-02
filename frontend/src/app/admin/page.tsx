"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import Link from "next/link";
import { ArrowLeft, Activity, Database, CheckCircle, Clock, Server, FileText, AlertCircle, ShieldCheck, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { API_BASE_URL } from "@/lib/api";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function AdminDashboard() {
  const [logType, setLogType] = useState("monitor");

  const { data: qualityData, error: qualityError } = useSWR(`${API_BASE_URL}/api/admin/data/quality`, fetcher, { refreshInterval: 10000 });
  const { data: statusData, error: statusError } = useSWR(`${API_BASE_URL}/api/admin/scraper/status`, fetcher, { refreshInterval: 5000 });
  const { data: logsData, error: logsError } = useSWR(`${API_BASE_URL}/api/admin/scraper/logs?type=${logType}`, fetcher, { refreshInterval: 3000 });

  return (
    <div className="min-h-screen p-6 sm:px-12 md:px-24 pt-12 pb-24 w-full max-w-7xl mx-auto font-sans bg-slate-50/50">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
        <div>
          <Link href="/" className="text-sm font-medium text-slate-500 hover:text-slate-900 flex items-center gap-2 mb-4 transition-colors w-fit">
            <ArrowLeft className="w-4 h-4" /> 返回主站
          </Link>
          <h1 className="text-3xl font-semibold text-slate-900 flex items-center gap-3">
            <Activity className="w-8 h-8 text-slate-700" /> 数据质量与爬虫监控大屏
          </h1>
          <p className="text-slate-500 mt-2">实时监控底层金融数据的全面性、正确性以及后台爬虫的运行进度。</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="bg-slate-900 text-white border-none rounded-none">
            {statusData && statusData.in_progress > 0 ? "爬虫活跃中" : "爬虫休眠/等待"}
          </Badge>
          <span className="text-xs text-slate-400">自动刷新中...</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
        {/* 数据质量卡片 - SAC */}
        <div className="bg-white rounded-none shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-brand-500" /> 中证协 (SAC) 数据
            </h2>
          </div>
          {qualityData ? (
            <div className="space-y-4">
              <div className="flex justify-between items-end">
                <span className="text-sm text-slate-500">总入库人数</span>
                <span className="text-2xl font-bold text-slate-900">{qualityData.sac.total.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-end">
                <span className="text-sm text-slate-500">今日新增</span>
                <span className="text-lg font-semibold text-emerald-600">+{qualityData.sac.today_new}</span>
              </div>
              <div className="pt-4 border-t border-slate-100">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-600">任职登记日期 完整度</span>
                  <span className="font-medium text-slate-700">{qualityData.sac.completeness_pct}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-none h-2">
                  <div className="bg-slate-700 h-2 rounded-none" style={{ width: `${qualityData.sac.completeness_pct}%` }}></div>
                </div>
                {qualityData.sac.missing_date > 0 && (
                  <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" /> 有 {qualityData.sac.missing_date} 条数据缺失登记日期
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="animate-pulse flex flex-col gap-4">
              <div className="h-8 bg-slate-100 rounded w-1/3"></div>
              <div className="h-4 bg-slate-100 rounded w-full"></div>
            </div>
          )}
        </div>

        {/* 数据质量卡片 - AMAC */}
        <div className="bg-white rounded-none shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <Database className="w-5 h-5 text-indigo-500" /> 中基协 (AMAC) 数据
            </h2>
          </div>
          {qualityData ? (
            <div className="space-y-4">
              <div className="flex justify-between items-end">
                <span className="text-sm text-slate-500">总入库人数</span>
                <span className="text-2xl font-bold text-slate-900">{qualityData.amac.total.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-end">
                <span className="text-sm text-slate-500">今日新增</span>
                <span className="text-lg font-semibold text-emerald-600">+{qualityData.amac.today_new}</span>
              </div>
              <div className="pt-4 border-t border-slate-100">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-600">证书取得日期 完整度</span>
                  <span className="font-medium text-slate-700">{qualityData.amac.completeness_pct}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-none h-2">
                  <div className="bg-slate-700 h-2 rounded-none" style={{ width: `${qualityData.amac.completeness_pct}%` }}></div>
                </div>
                {qualityData.amac.missing_date > 0 && (
                  <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" /> 有 {qualityData.amac.missing_date} 条数据缺失证书日期
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="animate-pulse flex flex-col gap-4">
              <div className="h-8 bg-slate-100 rounded w-1/3"></div>
              <div className="h-4 bg-slate-100 rounded w-full"></div>
            </div>
          )}
        </div>

        {/* RSC 数据质量卡片 */}
        <div className="bg-white rounded-none shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <Users className="w-5 h-5 text-amber-500" /> RSC 用户比对库
            </h2>
          </div>
          {qualityData && qualityData.rsc ? (
            <div className="space-y-4">
              <div className="flex justify-between items-end">
                <span className="text-sm text-slate-500">RSC 用户总数</span>
                <span className="text-2xl font-bold text-slate-900">{qualityData.rsc.total.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-end">
                <span className="text-sm text-slate-500">已匹配人才库</span>
                <span className="text-lg font-semibold text-brand-600">{qualityData.rsc.matched.toLocaleString()}</span>
              </div>
              <div className="pt-4 border-t border-slate-100">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-600">用户匹配成功率</span>
                  <span className="font-medium text-slate-700">{qualityData.rsc.match_rate_pct}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-none h-2">
                  <div className="bg-slate-700 h-2 rounded-none" style={{ width: `${qualityData.rsc.match_rate_pct}%` }}></div>
                </div>
                {qualityData.rsc.outdated > 0 && (
                  <p className="text-xs text-amber-600 mt-2 flex items-center justify-between">
                    <span className="flex items-center gap-1"><AlertCircle className="w-3 h-3" /> 有 {qualityData.rsc.outdated} 名用户待更新机构</span>
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="animate-pulse flex flex-col gap-4">
              <div className="h-8 bg-slate-100 rounded w-1/3"></div>
              <div className="h-4 bg-slate-100 rounded w-full"></div>
            </div>
          )}
        </div>

        {/* 爬虫任务状态 */}
        <div className="bg-white rounded-none shadow-sm border border-slate-200 p-6 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <Server className="w-5 h-5 text-slate-600" /> 爬虫调度进度
            </h2>
          </div>
          {statusData ? (
            <div className="flex-1 flex flex-col">
              <div className="flex gap-4 mb-4">
                <div className="flex-1 bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <div className="text-xs text-slate-500 mb-1">正在执行任务</div>
                  <div className="text-xl font-bold text-brand-600">{statusData.in_progress}</div>
                </div>
                <div className="flex-1 bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <div className="text-xs text-slate-500 mb-1">已完成任务</div>
                  <div className="text-xl font-bold text-slate-700">{statusData.completed}</div>
                </div>
              </div>
              <div className="text-sm font-medium text-slate-700 mb-2">近期活跃任务：</div>
              <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-2 max-h-[120px]">
                {statusData.active_tasks.map((task: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between text-xs p-2 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="font-mono text-slate-600 truncate mr-2" title={task.task_name}>{task.task_name}</span>
                    <span className="text-slate-400 whitespace-nowrap">{task.updated_at.split(' ')[1]}</span>
                  </div>
                ))}
                {statusData.active_tasks.length === 0 && (
                  <div className="text-xs text-slate-400 text-center py-4">当前无进行中的任务</div>
                )}
              </div>
            </div>
          ) : (
            <div className="animate-pulse h-full bg-slate-50 rounded-xl"></div>
          )}
        </div>
      </div>

      {/* 日志大屏 */}
      <div className="bg-slate-900 rounded-none shadow-lg border border-slate-800 overflow-hidden flex flex-col h-[500px]">
        <div className="bg-slate-950 px-4 py-3 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-slate-400" />
            <span className="text-sm font-medium text-slate-300">实时日志控制台</span>
          </div>
          <div className="flex gap-2">
            <button 
              onClick={() => setLogType("monitor")}
              className={`text-xs px-3 py-1 rounded-none transition-colors ${logType === 'monitor' ? 'bg-slate-700 text-white' : 'bg-slate-900 text-slate-400 border border-slate-800 hover:bg-slate-800'}`}
            >
              Monitor
            </button>
            <button 
              onClick={() => setLogType("sac")}
              className={`text-xs px-3 py-1 rounded-none transition-colors ${logType === 'sac' ? 'bg-slate-700 text-white' : 'bg-slate-900 text-slate-400 border border-slate-800 hover:bg-slate-800'}`}
            >
              SAC Scraper
            </button>
            <button 
              onClick={() => setLogType("amac")}
              className={`text-xs px-3 py-1 rounded-none transition-colors ${logType === 'amac' ? 'bg-slate-700 text-white' : 'bg-slate-900 text-slate-400 border border-slate-800 hover:bg-slate-800'}`}
            >
              AMAC Scraper
            </button>
          </div>
        </div>
        <div className="p-4 overflow-y-auto flex-1 font-mono text-xs sm:text-sm text-slate-300 space-y-1 custom-scrollbar flex flex-col-reverse">
          {logsData ? (
            <div>
              {logsData.lines.map((line: string, i: number) => {
                // 简单的日志高亮
                let colorClass = "text-slate-300";
                if (line.includes("ERROR") || line.includes("Exception")) colorClass = "text-red-400 font-semibold";
                else if (line.includes("WARNING")) colorClass = "text-amber-400";
                else if (line.includes("INFO") || line.includes("completed")) colorClass = "text-emerald-400";
                
                return (
                  <div key={i} className={`whitespace-pre-wrap break-all ${colorClass}`}>
                    {line}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-slate-500 animate-pulse">Loading logs...</div>
          )}
        </div>
      </div>
    </div>
  );
}
