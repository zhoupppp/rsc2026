"use client";

import { ExternalLink } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-slate-200/70 bg-white/70 backdrop-blur">
      <div className="max-w-7xl mx-auto px-6 py-8 flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
          <a
            href="https://www.roadshowchina.cn/Product/index.html"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-slate-600 hover:text-slate-900 transition-colors"
          >
            SuperIR（站外） <ExternalLink aria-hidden="true" className="w-3.5 h-3.5" />
          </a>
          <a
            href="https://www.roadshowchina.cn/About/us.html"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-slate-600 hover:text-slate-900 transition-colors"
          >
            关于路演中（站外） <ExternalLink aria-hidden="true" className="w-3.5 h-3.5" />
          </a>
        </div>

        <div className="text-xs text-slate-400">
          RSCdata · 金融人才档案库
        </div>
      </div>
    </footer>
  );
}
