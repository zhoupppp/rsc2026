"use client";

import { useMemo } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

type FieldSchema = {
  key: string;
  label: string;
  type: "text" | "enum" | "date" | "boolean";
  ops: string[];
  options?: string[];
};

type RuleNode = {
  type: "rule";
  id: string;
  field: string;
  op: string;
  value: string;
};

type GroupNode = {
  type: "group";
  id: string;
  op: "and" | "or";
  children: Node[];
};

type Node = RuleNode | GroupNode;

export type FilterBuilderValue = GroupNode;

const genId = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`;

function splitVals(s: string): string[] {
  return s
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}

function serializeNode(node: Node): any | null {
  if (node.type === "group") {
    const children = node.children.map(serializeNode).filter(Boolean);
    if (children.length === 0) return null;
    return { op: node.op, children };
  }

  const field = (node.field || "").trim();
  const op = (node.op || "").trim();
  if (!field || !op) return null;

  if (op === "exists" || op === "not_exists") {
    return { field, op };
  }

  if (op === "in" || op === "not_in") {
    const values = splitVals(node.value);
    if (values.length === 0) return null;
    return { field, op, values };
  }

  const value = (node.value || "").trim();
  if (!value) return null;
  return { field, op, value };
}

export function toAdvQuery(value: FilterBuilderValue): string | null {
  const q = serializeNode(value);
  if (!q) return null;
  return JSON.stringify(q);
}

export default function FilterBuilder({
  schema,
  value,
  onChange,
}: {
  schema: FieldSchema[] | undefined;
  value: FilterBuilderValue;
  onChange: (v: FilterBuilderValue) => void;
}) {
  const opLabel = (op: string) => {
    const m: Record<string, string> = {
      contains: "包含",
      not_contains: "不包含",
      eq: "等于",
      neq: "不等于",
      in: "属于（多选）",
      not_in: "不属于（排除）",
      exists: "存在",
      not_exists: "不存在",
      gte: "大于等于",
      lte: "小于等于",
      gt: "大于",
      lt: "小于",
    };
    return m[op] || op;
  };

  const fieldsByKey = useMemo(() => {
    const m = new Map<string, FieldSchema>();
    (schema || []).forEach((f) => m.set(f.key, f));
    return m;
  }, [schema]);

  const fieldOptions = useMemo(() => (schema || []).map((f) => ({ key: f.key, label: f.label })), [schema]);

  const updateNode = (nodeId: string, updater: (n: Node) => Node | null, group: GroupNode = value): GroupNode => {
    const children = group.children
      .map((c) => {
        if (c.id === nodeId) return updater(c);
        if (c.type === "group") return updateNode(nodeId, updater, c);
        return c;
      })
      .filter(Boolean) as Node[];
    return { ...group, children };
  };

  const addRule = (groupId: string) => {
    const insert = (g: GroupNode): GroupNode => {
      if (g.id !== groupId) {
        return { ...g, children: g.children.map((c) => (c.type === "group" ? insert(c) : c)) };
      }
      const next: RuleNode = { type: "rule", id: genId(), field: "", op: "contains", value: "" };
      return { ...g, children: [...g.children, next] };
    };
    onChange(insert(value));
  };

  const addGroup = (groupId: string) => {
    const insert = (g: GroupNode): GroupNode => {
      if (g.id !== groupId) {
        return { ...g, children: g.children.map((c) => (c.type === "group" ? insert(c) : c)) };
      }
      const next: GroupNode = { type: "group", id: genId(), op: "and", children: [] };
      return { ...g, children: [...g.children, next] };
    };
    onChange(insert(value));
  };

  const removeNode = (nodeId: string) => {
    onChange(updateNode(nodeId, () => null));
  };

  const renderGroup = (g: GroupNode, depth: number) => {
    return (
      <div className={`${depth > 0 ? "pl-4 border-l-2 border-slate-100" : ""}`}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <select
              value={g.op}
              onChange={(e) => onChange(updateNode(g.id, (n) => ({ ...(n as GroupNode), op: e.target.value as "and" | "or" })))}
              className="text-xs border border-slate-200 rounded-none px-2 py-1 bg-white"
            >
              <option value="and">全部满足 (AND)</option>
              <option value="or">满足任一 (OR)</option>
            </select>
            <button
              type="button"
              onClick={() => addRule(g.id)}
              className="text-xs px-2 py-1 border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 flex items-center gap-1 rounded-none"
            >
              <Plus className="w-3 h-3" /> 条件
            </button>
            <button
              type="button"
              onClick={() => addGroup(g.id)}
              className="text-xs px-2 py-1 border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 flex items-center gap-1 rounded-none"
            >
              <Plus className="w-3 h-3" /> 条件组
            </button>
          </div>
          {depth > 0 && (
            <button type="button" onClick={() => removeNode(g.id)} className="text-slate-400 hover:text-slate-700">
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="mt-3 space-y-2">
          {g.children.length === 0 ? (
            <div className="text-xs text-slate-400 py-2">暂无条件</div>
          ) : (
            g.children.map((c) => (c.type === "group" ? renderGroup(c, depth + 1) : renderRule(c)))
          )}
        </div>
      </div>
    );
  };

  const renderRule = (r: RuleNode) => {
    const f = fieldsByKey.get(r.field);
    const ops = f?.ops || ["contains", "eq", "in", "exists"];
    const type = f?.type || "text";
    const suggestions = (f?.options || []).slice(0, 12);
    const datalistId = (f?.options || []).length > 0 ? `fb-${r.id}-${r.field}` : undefined;
    const opOptions = ops.map((o) => ({ value: o, label: opLabel(o) }));

    const onPickSuggestion = (s: string) => {
      if (r.op === "in" || r.op === "not_in") {
        const vals = splitVals(r.value);
        if (!vals.includes(s)) vals.push(s);
        onChange(updateNode(r.id, (n) => ({ ...(n as RuleNode), value: vals.join(",") })));
        return;
      }
      onChange(updateNode(r.id, (n) => ({ ...(n as RuleNode), value: s })));
    };

    const valueInput =
      r.op === "exists" || r.op === "not_exists" ? null : type === "boolean" ? (
        <select
          value={r.value}
          onChange={(e) => onChange(updateNode(r.id, (n) => ({ ...(n as RuleNode), value: e.target.value })))}
          className="w-full text-sm border-slate-200 rounded-none focus:ring-slate-900 focus:border-slate-900 p-2 border bg-white"
        >
          <option value="">请选择</option>
          <option value="true">是</option>
          <option value="false">否</option>
        </select>
      ) : (
        <>
          <Input
            value={r.value}
            onChange={(e) => onChange(updateNode(r.id, (n) => ({ ...(n as RuleNode), value: e.target.value })))}
            type={type === "date" ? "date" : "text"}
            list={datalistId}
            placeholder={r.op === "in" || r.op === "not_in" ? "用逗号分隔多个值" : "请输入"}
            className="rounded-none border-slate-200 focus-visible:ring-slate-900"
          />
          {datalistId && (
            <datalist id={datalistId}>
              {(f?.options || []).slice(0, 200).map((o) => (
                <option key={o} value={o} />
              ))}
            </datalist>
          )}
        </>
      );

    return (
      <div className="border border-slate-200 bg-white p-3 rounded-none">
        <div className="flex items-start gap-2">
          <div className="w-[160px]">
            <select
              value={r.field}
              onChange={(e) => {
                const nextField = e.target.value;
                const nextOp = fieldsByKey.get(nextField)?.ops?.[0] || "contains";
                onChange(updateNode(r.id, (n) => ({ ...(n as RuleNode), field: nextField, op: nextOp, value: "" })));
              }}
              className="w-full text-sm border-slate-200 rounded-none focus:ring-slate-900 focus:border-slate-900 p-2 border bg-white"
            >
              <option value="">选择字段</option>
              {fieldOptions.map((fo) => (
                <option key={fo.key} value={fo.key}>
                  {fo.label}
                </option>
              ))}
            </select>
          </div>

          <div className="w-[140px]">
            <select
              value={r.op}
              onChange={(e) => onChange(updateNode(r.id, (n) => ({ ...(n as RuleNode), op: e.target.value, value: "" })))}
              className="w-full text-sm border-slate-200 rounded-none focus:ring-slate-900 focus:border-slate-900 p-2 border bg-white"
            >
              {opOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex-1 min-w-0">{valueInput}</div>

          <button type="button" onClick={() => removeNode(r.id)} className="text-slate-400 hover:text-slate-700 pt-2">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        {suggestions.length > 0 && r.op !== "exists" && r.op !== "not_exists" && type !== "date" && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {suggestions.map((s) => (
              <button key={s} type="button" onClick={() => onPickSuggestion(s)} className="text-left">
                <Badge variant="outline" className="rounded-none text-[10px] bg-slate-50 text-slate-600 border-slate-200">
                  {s}
                </Badge>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  };

  return renderGroup(value, 0);
}
