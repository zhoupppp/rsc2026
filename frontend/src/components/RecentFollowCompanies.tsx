"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";

export default function RecentFollowCompanies({ companies }: { companies: string[] }) {
  const [expanded, setExpanded] = useState(false);

  const items = useMemo(() => {
    return (companies || [])
      .map((c) => String(c || "").trim())
      .filter(Boolean)
      .slice(0, 20);
  }, [companies]);

  const visible = expanded ? items : items.slice(0, 8);

  if (items.length === 0) return null;

  return (
    <div className="border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[10px] text-slate-500 uppercase tracking-widest">关注公司</div>
        {items.length > 8 && (
          <button type="button" className="text-[10px] text-slate-500 hover:text-slate-900" onClick={() => setExpanded((v) => !v)}>
            {expanded ? "收起" : `展开全部（${items.length}）`}
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {visible.map((name) => (
          <Badge key={name} variant="outline" className="rounded-none bg-slate-50 text-slate-700 border-slate-200 text-xs font-normal px-2 max-w-[220px]">
            <span className="truncate" title={name}>
              {name}
            </span>
          </Badge>
        ))}
      </div>
    </div>
  );
}

