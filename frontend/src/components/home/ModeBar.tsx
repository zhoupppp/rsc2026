"use client";

import type { ComponentType } from "react";
import { Sparkles, Search, SlidersHorizontal, X } from "lucide-react";
import type { HomeMode, HomeView } from "./types";

export function ModeBar({
  homeView,
  mode,
  onModeChange,
  onExit,
}: {
  homeView: HomeView;
  mode: HomeMode;
  onModeChange: (m: HomeMode) => void;
  onExit: () => void;
}) {
  const items: Array<{ key: HomeMode; label: string; Icon: ComponentType<{ className?: string }> }> = [
    { key: "search", label: "搜索", Icon: Search },
    { key: "filter", label: "精准筛选", Icon: SlidersHorizontal },
    { key: "ai", label: "AI 智能检索", Icon: Sparkles },
  ];

  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
      <div />
      <div className="bg-slate-50 p-1 flex items-center gap-1 border border-slate-200">
        {items.map(({ key, label, Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => onModeChange(key)}
            className={`px-4 py-2 text-sm font-medium transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 ${
              mode === key ? "bg-white text-slate-900 shadow-sm border border-slate-200" : "text-slate-500 hover:text-slate-900"
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {homeView === "workbench" && (
        <button
          type="button"
          onClick={onExit}
          className="justify-self-end px-3 py-2 text-sm font-medium border border-slate-200 text-slate-700 bg-white/70 hover:bg-white transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
        >
          <X className="w-4 h-4" />
          关闭
        </button>
      )}
    </div>
  );
}
