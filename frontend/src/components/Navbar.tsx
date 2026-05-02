"use client";

import Link from "next/link";
import { Search, LayoutDashboard, Clock } from "lucide-react";

export function Navbar() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200/60">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo & Brand */}
        <Link
          href="/"
          onClick={(e) => {
            if (typeof window !== "undefined" && window.location.pathname === "/") {
              e.preventDefault();
              window.dispatchEvent(new CustomEvent("rsc:go-home"));
            }
          }}
          className="flex items-center gap-3"
        >
          <img src="https://www.roadshowchina.cn/w/images/logo-icon.png" alt="RSC Logo" width={32} height={32} className="w-8 h-8" />
          <span className="text-xl font-bold text-brand-800 tracking-tight">RSCdata</span>
          <span className="hidden sm:inline-block text-xs font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full ml-2">
            金融档案库
          </span>
        </Link>

        {/* Navigation Links */}
        <nav className="hidden md:flex items-center gap-8">
          <Link href="/" className="text-sm font-medium text-brand-600 flex items-center gap-1.5">
            <Search className="w-4 h-4" />
            档案检索
          </Link>
          <Link href="/newest" className="text-sm font-medium text-slate-600 hover:text-brand-600 transition-colors flex items-center gap-1.5">
            <Clock className="w-4 h-4" />
            最新入库
          </Link>
          <Link href="/admin" className="text-sm font-medium text-slate-600 hover:text-brand-600 transition-colors flex items-center gap-1.5">
            <LayoutDashboard className="w-4 h-4" />
            后台数据大屏
          </Link>
        </nav>

        {/* Mobile menu button (simplified) */}
        <div className="md:hidden flex items-center">
          <Link href="/newest" className="text-xs font-medium text-slate-500 hover:text-brand-600 transition-colors">
            最新入库
          </Link>
        </div>
      </div>
    </header>
  );
}
