import sqlite3
import json
import os
import ssl
import urllib.request
import urllib.error
import time
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any, Set
from pydantic import BaseModel, Field
from datetime import datetime
from collections import defaultdict

app = FastAPI(title="Financial Talent Explorer API")

_cors_env = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
_allow_origins = ["*"] if not _cors_env else [o.strip() for o in _cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _download_to_file(url: str, dest_path: str, timeout_sec: int = 60) -> None:
    tmp_path = dest_path + ".tmp"
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp, open(tmp_path, "wb") as f:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        os.replace(tmp_path, dest_path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

def _resolve_db_path() -> str:
    env_path = (os.getenv("DB_PATH") or "").strip()
    if env_path:
        return env_path

    repo_root = os.path.dirname(os.path.dirname(__file__))
    candidate = os.path.join(repo_root, "financial_scraper", "financial_data_v1.db")
    if os.path.exists(candidate):
        return candidate

    candidate2 = os.path.join(os.path.dirname(__file__), "..", "financial_scraper", "financial_data_v1.db")
    if os.path.exists(candidate2):
        return candidate2

    db_url = (os.getenv("DB_URL") or "").strip()
    if db_url:
        cached_path = os.path.join(repo_root, "data", "financial_data_v1.db")
        if not os.path.exists(cached_path) or os.path.getsize(cached_path) < 1024:
            _download_to_file(db_url, cached_path)
        return cached_path

    return candidate

DB_PATH = _resolve_db_path()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# 内存索引
tag_index: Dict[str, Set[str]] = defaultdict(set) # tag -> set of rsc_uid
aum_index: Dict[str, Set[str]] = defaultdict(set) # aum_level -> set of rsc_uid
all_rsc_uids: Set[str] = set()
office_city_index: Dict[str, Set[str]] = defaultdict(set)
shenwan1_index: Dict[str, Set[str]] = defaultdict(set)
org_type_index: Dict[str, Set[str]] = defaultdict(set)
outdated_rsc_uids: Set[str] = set()

filter_stats_cache: Dict[str, Any] = {"built_at": None, "data": None}

def split_multi_values(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        out: List[str] = []
        for v in val:
            out.extend(split_multi_values(v))
        return out
    if isinstance(val, (int, float)):
        return [str(val)]
    s = str(val).strip()
    if not s:
        return []
    parts = []
    for sep in [",", "，", "、", ";", "；", "|", "\n", "\t"]:
        if sep in s:
            s = s.replace(sep, ",")
    for p in s.split(","):
        p = p.strip()
        if p:
            parts.append(p)
    return parts

def extract_user_tags(ext: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    bt = ext.get("behavior_tags")
    if isinstance(bt, dict):
        if bt.get("偏好主题"):
            tags.extend(split_multi_values(bt.get("偏好主题")))
        if bt.get("偏好赛道"):
            tags.extend(split_multi_values(bt.get("偏好赛道")))

    if ext.get("pref_theme"):
        tags.extend(split_multi_values(ext.get("pref_theme")))
    if ext.get("pref_track"):
        tags.extend(split_multi_values(ext.get("pref_track")))

    ri = ext.get("research_industries")
    if ri:
        tags.extend(split_multi_values(ri))
    ari = ext.get("agg_research_industry")
    if ari:
        tags.extend(split_multi_values(ari))
    vt = ext.get("value_tags")
    if vt:
        tags.extend(split_multi_values(vt))

    seen = set()
    out = []
    for t in tags:
        tt = t.strip()
        if not tt or tt in seen:
            continue
        seen.add(tt)
        out.append(tt)
    return out

def normalize_org_type(val: Any) -> str:
    s = clean_str(val)
    if not s:
        return ""
    if "公募" in s:
        return "公募基金"
    if "券商资管" in s or ("券商" in s and "资管" in s):
        return "券商资管"
    if "证券" in s or "券商" in s or "研究所" in s:
        return "证券公司"
    if "私募" in s:
        return "私募基金"
    if "保险" in s and "资管" in s:
        return "保险资管"
    if "保险" in s:
        return "保险资管"
    if "银行" in s and ("理财" in s or "资管" in s):
        return "银行理财"
    if "银行" in s:
        return "银行理财"
    return s

def normalize_office_city(val: Any) -> str:
    s = clean_str(val)
    if not s:
        return ""
    if "香港" in s:
        return "香港"
    ss = s.lower().replace(" ", "")
    if "hongkong" in ss or ss == "hk":
        return "香港"
    return s

def compute_filter_stats(top_n: int = 50) -> Dict[str, Any]:
    top_n = max(1, min(int(top_n), 200))

    city_counts: Dict[str, int] = defaultdict(int)
    shenwan1_counts: Dict[str, int] = defaultdict(int)
    shenwan2_counts: Dict[str, int] = defaultdict(int)
    org_type_counts: Dict[str, int] = defaultdict(int)
    tag_counts: Dict[str, int] = defaultdict(int)
    cert_type_counts: Dict[str, int] = defaultdict(int)
    country_region_counts: Dict[str, int] = defaultdict(int)
    province_counts: Dict[str, int] = defaultdict(int)
    office_province_counts: Dict[str, int] = defaultdict(int)
    mobile_province_counts: Dict[str, int] = defaultdict(int)
    org_region_counts: Dict[str, int] = defaultdict(int)
    org_is_foreign_counts: Dict[str, int] = defaultdict(int)
    org_group_counts: Dict[str, int] = defaultdict(int)
    org_subtype_counts: Dict[str, int] = defaultdict(int)
    org_office_location_counts: Dict[str, int] = defaultdict(int)
    org_value_score_counts: Dict[str, int] = defaultdict(int)
    org_influence_score_counts: Dict[str, int] = defaultdict(int)
    org_invest_profile_counts: Dict[str, int] = defaultdict(int)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.uid, u.ext_data,
               o.region, o.is_foreign, o.value_score, o.influence_score, o.invest_position, o.ext_data as org_ext_data
        FROM rsc_users u
        LEFT JOIN rsc_orgs o ON u.oid = o.oid
        WHERE u.ext_data IS NOT NULL
    """)
    rows = cursor.fetchall()

    for uid, ext_data, org_region, org_is_foreign, org_value_score, org_influence_score, org_invest_position, org_ext_data in rows:
        try:
            ext = json.loads(ext_data) if ext_data else {}
        except json.JSONDecodeError:
            continue
        if not isinstance(ext, dict):
            continue

        city = normalize_office_city(ext.get("office_city"))
        if city:
            city_counts[city] += 1
        sw1 = clean_str(ext.get("shenwan_1"))
        if sw1:
            shenwan1_counts[sw1] += 1
        sw2 = clean_str(ext.get("shenwan_2")) or clean_str(ext.get("shenwan_3"))
        if sw2:
            shenwan2_counts[sw2] += 1
        org_type = normalize_org_type(ext.get("org_type"))
        if org_type:
            org_type_counts[org_type] += 1

        cert_type = clean_str(ext.get("cert_type"))
        if cert_type:
            cert_type_counts[cert_type] += 1
        office_country = clean_str(ext.get("office_country"))
        if office_country:
            for v in split_multi_values(office_country):
                country_region_counts[v] += 1
        mobile_country = clean_str(ext.get("mobile_country"))
        if mobile_country:
            for v in split_multi_values(mobile_country):
                country_region_counts[v] += 1
        office_province = clean_str(ext.get("office_province"))
        if office_province:
            office_province_counts[office_province] += 1
            for v in split_multi_values(office_province):
                province_counts[v] += 1
        mobile_province = clean_str(ext.get("mobile_province"))
        if mobile_province:
            mobile_province_counts[mobile_province] += 1
            for v in split_multi_values(mobile_province):
                province_counts[v] += 1

        tags = extract_user_tags(ext)
        for t in tags:
            tag_counts[t] += 1

        if org_region:
            org_region_counts[clean_str(org_region)] += 1
        if org_is_foreign is not None:
            s = str(org_is_foreign).strip()
            if s:
                org_is_foreign_counts["true"] += 1
            else:
                org_is_foreign_counts["false"] += 1
        if org_value_score is not None:
            org_value_score_counts[str(org_value_score)] += 1
        if org_influence_score is not None:
            org_influence_score_counts[str(org_influence_score)] += 1
        if org_invest_position:
            for v in split_multi_values(org_invest_position):
                org_invest_profile_counts[v] += 1
        if org_ext_data:
            try:
                org_ext = json.loads(org_ext_data) if org_ext_data else {}
            except json.JSONDecodeError:
                org_ext = {}
            if isinstance(org_ext, dict):
                if org_ext.get("org_group"):
                    for v in split_multi_values(org_ext.get("org_group")):
                        org_group_counts[v] += 1
                if org_ext.get("org_subtype"):
                    for v in split_multi_values(org_ext.get("org_subtype")):
                        org_subtype_counts[v] += 1
                if org_ext.get("office_location"):
                    for v in split_multi_values(org_ext.get("office_location")):
                        org_office_location_counts[v] += 1
                if org_ext.get("invest_pos"):
                    for v in split_multi_values(org_ext.get("invest_pos")):
                        org_invest_profile_counts[v] += 1
                if org_ext.get("invest_style"):
                    for v in split_multi_values(org_ext.get("invest_style")):
                        org_invest_profile_counts[v] += 1

    conn.close()

    def to_sorted_list(m: Dict[str, int]) -> List[Dict[str, Any]]:
        return [{"value": k, "count": v} for k, v in sorted(m.items(), key=lambda x: x[1], reverse=True)[:top_n]]

    return {
        "built_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "total_rsc_users": len(rows),
        "fields": {
            "adv_office_city": {"type": "single", "options": to_sorted_list(city_counts)},
            "adv_shenwan_1": {"type": "single", "options": to_sorted_list(shenwan1_counts)},
            "pref_industry_l2": {"type": "single", "options": to_sorted_list(shenwan2_counts)},
            "adv_org_type": {"type": "single", "options": to_sorted_list(org_type_counts)},
            "tags": {"type": "multi", "options": to_sorted_list(tag_counts)},
            "cert_type": {"type": "single", "options": to_sorted_list(cert_type_counts)},
            "country_region": {"type": "single", "options": to_sorted_list(country_region_counts)},
            "province": {"type": "single", "options": to_sorted_list(province_counts)},
            "office_province": {"type": "single", "options": to_sorted_list(office_province_counts)},
            "mobile_province": {"type": "single", "options": to_sorted_list(mobile_province_counts)},
            "aum": {"type": "single", "options": [{"value": k, "count": len(v)} for k, v in sorted(aum_index.items(), key=lambda x: len(x[1]), reverse=True)]},
            "region": {"type": "single", "options": to_sorted_list(org_region_counts)},
            "is_foreign": {"type": "single", "options": to_sorted_list(org_is_foreign_counts)},
            "org_group": {"type": "single", "options": to_sorted_list(org_group_counts)},
            "org_subtype": {"type": "single", "options": to_sorted_list(org_subtype_counts)},
            "office_location": {"type": "single", "options": to_sorted_list(org_office_location_counts)},
            "value_score": {"type": "single", "options": to_sorted_list(org_value_score_counts)},
            "influence_score": {"type": "single", "options": to_sorted_list(org_influence_score_counts)},
            "invest_profile": {"type": "single", "options": to_sorted_list(org_invest_profile_counts)},
        },
    }

def format_filter_stats_for_prompt(stats: Dict[str, Any], top_n: int = 20) -> str:
    fields = stats.get("fields", {}) if isinstance(stats, dict) else {}
    def fmt(field_key: str) -> str:
        f = fields.get(field_key, {})
        opts = f.get("options", []) if isinstance(f, dict) else []
        parts = []
        for o in opts[:top_n]:
            if not isinstance(o, dict):
                continue
            v = str(o.get("value") or "").strip()
            c = o.get("count")
            if v and isinstance(c, int):
                parts.append(f"{v}({c})")
        return "、".join(parts)

    return "\n".join([
        f"- 城市(adv_office_city): {fmt('adv_office_city')}",
        f"- 申万一级(adv_shenwan_1): {fmt('adv_shenwan_1')}",
        f"- 机构类型(adv_org_type): {fmt('adv_org_type')}",
        f"- 标签(tags): {fmt('tags')}",
    ])

def suggest_existing_tags(keywords: List[str], limit: int = 8) -> List[str]:
    kw = [k.strip() for k in keywords if k and k.strip()]
    if not kw:
        return []
    candidates = []
    for tag, ids in tag_index.items():
        if not tag:
            continue
        if any(k.lower() in tag.lower() for k in kw):
            candidates.append((tag, len(ids)))
    candidates.sort(key=lambda x: x[1], reverse=True)
    return [c[0] for c in candidates[: max(1, min(int(limit), 20))]]

def expand_tags_in_query(obj: Any, hints: List[str]) -> Any:
    if not isinstance(obj, dict):
        return obj
    if "op" in obj and "children" in obj:
        obj["children"] = [expand_tags_in_query(c, hints) for c in obj.get("children", [])]
        return obj
    if obj.get("field") == "tags" and obj.get("op") in {"in", "not_in", "eq", "neq", "contains", "not_contains"}:
        vals = []
        if "values" in obj:
            vals = split_multi_values(obj["values"])
        elif "value" in obj:
            vals = split_multi_values(obj["value"])
        
        valid = [t for t in vals if t in tag_index]
        invalid = [t for t in vals if t and t not in tag_index]
        
        if invalid:
            if "科技" in invalid:
                tech_suggestions = suggest_existing_tags(
                    ["AI", "人工智能", "机器人", "云计算", "智能驾驶", "半导体", "SaaS", "软件", "计算机", "通信"],
                    limit=8
                )
                if tech_suggestions:
                    valid.extend(tech_suggestions)
                    hints.append(f"库内没有“科技”这个标签，已自动按科技相关高频标签做语义扩展：{'、'.join(tech_suggestions)}。")
                else:
                    hints.append("库内没有“科技”这个标签。建议改用申万一级行业（计算机/通信/电子等）或更具体主题标签。")
            else:
                suggestions = suggest_existing_tags(invalid, limit=8)
                if suggestions:
                    valid.extend(suggestions)
                    hints.append(f"库内未找到标签：{'、'.join(invalid[:6])}，已按近似高频标签做扩展：{'、'.join(suggestions)}。")
                else:
                    hints.append(f"库内未找到标签：{'、'.join(invalid[:6])}，可能导致结果偏少。")
                
        # Deduplicate
        seen = set()
        final_vals = []
        for v in valid:
            if v not in seen:
                seen.add(v)
                final_vals.append(v)
                
        if obj.get("op") in {"in", "not_in"}:
            obj["values"] = final_vals
        else:
            obj["value"] = final_vals[0] if final_vals else ""
            
    return obj

def normalize_filter_query(obj: Any) -> Optional[Dict[str, Any]]:
    allowed_fields = {
        "adv_office_city",
        "adv_shenwan_1",
        "pref_industry_l2",
        "adv_org_type",
        "name",
        "institution",
        "tags",
        "industry_theme",
        "aum",
        "cert_type",
        "office_country",
        "office_province",
        "mobile_country",
        "mobile_province",
        "country_region",
        "province",
        "pref_theme",
        "pref_track",
        "agg_research_industry",
        "last_active_time",
        "cert_time",
        "is_outdated",
        "region",
        "is_foreign",
        "org_group",
        "org_subtype",
        "office_location",
        "value_score",
        "influence_score",
        "invest_profile",
    }
    allowed_ops = {"eq", "neq", "contains", "not_contains", "in", "not_in", "exists", "not_exists", "gt", "gte", "lt", "lte"}

    if not obj or not isinstance(obj, dict):
        return None

    if "op" in obj and "children" in obj:
        op = str(obj.get("op") or "").lower().strip()
        if op not in {"and", "or"}:
            return None
        children_in = obj.get("children")
        if not isinstance(children_in, list):
            return None
        children_out: List[Dict[str, Any]] = []
        for c in children_in:
            n = normalize_filter_query(c)
            if n:
                children_out.append(n)
            else:
                r = normalize_filter_rule(c, allowed_fields, allowed_ops)
                if r:
                    children_out.append(r)
        if not children_out:
            return None
        return {"op": op, "children": children_out}

    return normalize_filter_rule(obj, allowed_fields, allowed_ops)

def normalize_filter_rule(obj: Any, allowed_fields: Set[str], allowed_ops: Set[str]) -> Optional[Dict[str, Any]]:
    if not obj or not isinstance(obj, dict):
        return None
    field = str(obj.get("field") or "").strip()
    op = str(obj.get("op") or "").lower().strip()
    if not field or field not in allowed_fields or op not in allowed_ops:
        return None

    if op in {"exists", "not_exists"}:
        return {"field": field, "op": op}

    if op in {"in", "not_in"}:
        values = obj.get("values")
        if values is None:
            values = obj.get("value")
        vals = split_multi_values(values)
        if not vals:
            return None
        return {"field": field, "op": op, "values": vals}

    value = obj.get("value")
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return {"field": field, "op": op, "value": s}

def split_query_hard_soft(obj: Any) -> (Optional[Dict[str, Any]], List[str]):
    if not obj or not isinstance(obj, dict):
        return None, []

    if "children" in obj and "op" in obj:
        op = str(obj.get("op") or "").lower().strip()
        children = obj.get("children", [])
        if not isinstance(children, list):
            return obj, []

        soft: List[str] = []
        hard_children: List[Dict[str, Any]] = []
        for c in children:
            hard_c, soft_c = split_query_hard_soft(c)
            soft.extend(soft_c)
            if hard_c:
                hard_children.append(hard_c)

        if op == "and":
            if not hard_children:
                hard = None
            elif len(hard_children) == 1:
                hard = hard_children[0]
            else:
                hard = {"op": "and", "children": hard_children}
            return hard, soft

        return obj, soft

    if obj.get("field") == "tags":
        if "values" in obj:
            return None, split_multi_values(obj.get("values"))
        if "value" in obj:
            return None, split_multi_values(obj.get("value"))
        return None, []

    return obj, []

def compute_relevance_score(desired: List[str], candidate: List[str]) -> int:
    d = [str(x).strip() for x in (desired or []) if str(x).strip()]
    c = [str(x).strip() for x in (candidate or []) if str(x).strip()]
    if not d or not c:
        return 0
    cs = set(c)
    score = 0
    for t in d:
        if t in cs:
            score += 1
    return score

def evaluate_filter_query_to_ids(query: Dict[str, Any]) -> Set[str]:
    qn = normalize_filter_query(query)
    if not qn:
        return set()
    conn = get_db_connection()
    cursor = conn.cursor()
    ids = _eval_query_node(qn, cursor)
    conn.close()
    return ids

def _eval_query_node(node: Dict[str, Any], cursor: sqlite3.Cursor) -> Set[str]:
    if "children" in node and "op" in node:
        op = node.get("op")
        children = node.get("children", [])
        sets = [_eval_query_node(c, cursor) for c in children if isinstance(c, dict)]
        if not sets:
            return set()
        if op == "or":
            out: Set[str] = set()
            for s in sets:
                out |= s
            return out
        out = sets[0].copy()
        for s in sets[1:]:
            out &= s
        return out
    return _eval_query_rule(node, cursor)

def _eval_query_rule(rule: Dict[str, Any], cursor: sqlite3.Cursor) -> Set[str]:
    field = rule.get("field")
    op = rule.get("op")
    all_ids = set(all_rsc_uids)

    def idx_get(index: Dict[str, Set[str]], val: str) -> Set[str]:
        return set(index.get(val, set()))

    def idx_union(index: Dict[str, Set[str]], vals: List[str]) -> Set[str]:
        out: Set[str] = set()
        for v in vals:
            out |= set(index.get(v, set()))
        return out

    if field in {"adv_office_city", "adv_shenwan_1", "adv_org_type"}:
        if field == "adv_office_city":
            index = office_city_index
        elif field == "adv_shenwan_1":
            index = shenwan1_index
        else:
            index = org_type_index

        if op in {"exists", "not_exists"}:
            exists_set: Set[str] = set()
            for s in index.values():
                exists_set |= set(s)
            return exists_set if op == "exists" else (all_ids - exists_set)

        if op in {"eq", "neq", "contains", "not_contains"}:
            v = str(rule.get("value") or "").strip()
            if not v:
                return set()
            if op in {"eq", "neq"}:
                base = idx_get(index, v)
                return base if op == "eq" else (all_ids - base)
            base: Set[str] = set()
            for k, s in index.items():
                if v in k:
                    base |= set(s)
            return base if op == "contains" else (all_ids - base)

        if op in {"in", "not_in"}:
            vals = split_multi_values(rule.get("values"))
            base = idx_union(index, vals)
            return base if op == "in" else (all_ids - base)

    if field == "tags":
        if op in {"exists", "not_exists"}:
            exists_set: Set[str] = set()
            for s in tag_index.values():
                exists_set |= set(s)
            return exists_set if op == "exists" else (all_ids - exists_set)

        if op in {"eq", "neq"}:
            v = str(rule.get("value") or "").strip()
            base = set(tag_index.get(v, set())) if v else set()
            return base if op == "eq" else (all_ids - base)

        if op in {"contains", "not_contains"}:
            v = str(rule.get("value") or "").strip()
            base: Set[str] = set()
            if v:
                for k, s in tag_index.items():
                    if v in k:
                        base |= set(s)
            return base if op == "contains" else (all_ids - base)

        if op in {"in", "not_in"}:
            vals = split_multi_values(rule.get("values"))
            base = idx_union(tag_index, vals)
            return base if op == "in" else (all_ids - base)

    if field == "industry_theme":
        if op in {"exists", "not_exists"}:
            exists_set: Set[str] = set()
            for s in tag_index.values():
                exists_set |= set(s)
            return exists_set if op == "exists" else (all_ids - exists_set)

        if op in {"eq", "neq", "contains", "not_contains"}:
            v = str(rule.get("value") or "").strip()
            if not v:
                return set()
            if op in {"eq", "neq"}:
                base = idx_get(tag_index, v)
                return base if op == "eq" else (all_ids - base)
            base: Set[str] = set()
            for k, s in tag_index.items():
                if v in k:
                    base |= set(s)
            return base if op == "contains" else (all_ids - base)

        if op in {"in", "not_in"}:
            vals = split_multi_values(rule.get("values"))
            base = idx_union(tag_index, vals)
            return base if op == "in" else (all_ids - base)

    if field in {"country_region", "province", "pref_industry_l2"}:
        def sql_select(where: str, params: List[Any]) -> Set[str]:
            cursor.execute(
                f"SELECT uid FROM rsc_users u WHERE u.ext_data IS NOT NULL AND {where}",
                params,
            )
            return {str(r[0]) for r in cursor.fetchall()}

        if field == "country_region":
            cols = [
                "json_extract(u.ext_data, '$.office_country')",
                "json_extract(u.ext_data, '$.mobile_country')",
            ]
        elif field == "province":
            cols = [
                "json_extract(u.ext_data, '$.office_province')",
                "json_extract(u.ext_data, '$.mobile_province')",
            ]
        else:
            cols = [
                "json_extract(u.ext_data, '$.shenwan_2')",
                "json_extract(u.ext_data, '$.shenwan_3')",
            ]

        if op in {"exists", "not_exists"}:
            base = sql_select("(" + " OR ".join([f"({c} IS NOT NULL AND TRIM({c}) != '')" for c in cols]) + ")", [])
            return base if op == "exists" else (all_ids - base)

        if op in {"eq", "neq", "contains", "not_contains", "gt", "gte", "lt", "lte"}:
            v = str(rule.get("value") or "").strip()
            if not v:
                return set()
            if op in {"eq", "neq"}:
                where = "(" + " OR ".join([f"{c} = ?" for c in cols]) + ")"
                params = [v] * len(cols)
                base = sql_select(where, params)
                return base if op == "eq" else (all_ids - base)
            if op in {"contains", "not_contains"}:
                where = "(" + " OR ".join([f"{c} LIKE ?" for c in cols]) + ")"
                params = [f"%{v}%"] * len(cols)
                base = sql_select(where, params)
                return base if op == "contains" else (all_ids - base)
            op_map = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
            where = "(" + " OR ".join([f"{c} {op_map[op]} ?" for c in cols]) + ")"
            params = [v] * len(cols)
            base = sql_select(where, params)
            return base

        if op in {"in", "not_in"}:
            vals = split_multi_values(rule.get("values"))
            if not vals:
                return set()
            placeholders = ",".join(["?"] * len(vals))
            where = "(" + " OR ".join([f"{c} IN ({placeholders})" for c in cols]) + ")"
            params: List[Any] = []
            for _ in cols:
                params.extend(vals)
            base = sql_select(where, params)
            return base if op == "in" else (all_ids - base)

    if field == "aum":
        if op in {"exists", "not_exists"}:
            exists_set: Set[str] = set()
            for s in aum_index.values():
                exists_set |= set(s)
            return exists_set if op == "exists" else (all_ids - exists_set)

        if op in {"eq", "neq"}:
            v = str(rule.get("value") or "").strip()
            base = set(aum_index.get(v, set())) if v else set()
            return base if op == "eq" else (all_ids - base)

        if op in {"contains", "not_contains"}:
            v = str(rule.get("value") or "").strip()
            base: Set[str] = set()
            if v:
                for k, s in aum_index.items():
                    if v in k:
                        base |= set(s)
            return base if op == "contains" else (all_ids - base)

        if op in {"in", "not_in"}:
            vals = split_multi_values(rule.get("values"))
            base = idx_union(aum_index, vals)
            return base if op == "in" else (all_ids - base)

    if field == "is_outdated":
        truthy = {"1", "true", "yes", "y", "是", "待更新"}
        falsy = {"0", "false", "no", "n", "否", "正常"}

        def to_bool(s: str) -> Optional[bool]:
            ss = (s or "").strip().lower()
            if ss in truthy:
                return True
            if ss in falsy:
                return False
            return None

        if op in {"exists", "not_exists"}:
            base = set(outdated_rsc_uids)
            return base if op == "exists" else (all_ids - base)

        if op in {"eq", "neq"}:
            b = to_bool(str(rule.get("value") or ""))
            if b is None:
                return set()
            base = set(outdated_rsc_uids)
            out = base if b else (all_ids - base)
            return out if op == "eq" else (all_ids - out)

        if op in {"in", "not_in"}:
            vals = [to_bool(v) for v in split_multi_values(rule.get("values"))]
            vals = [v for v in vals if v is not None]
            if not vals:
                return set()
            base = set(outdated_rsc_uids)
            out: Set[str] = set()
            if True in vals:
                out |= base
            if False in vals:
                out |= (all_ids - base)
            return out if op == "in" else (all_ids - out)

    if field in {
        "cert_type",
        "office_country",
        "office_province",
        "mobile_country",
        "mobile_province",
        "pref_theme",
        "pref_track",
        "agg_research_industry",
        "last_active_time",
        "cert_time",
    }:
        def sql_select(where: str, params: List[Any]) -> Set[str]:
            cursor.execute(
                f"SELECT uid FROM rsc_users u WHERE u.ext_data IS NOT NULL AND {where}",
                params,
            )
            return {str(r[0]) for r in cursor.fetchall()}

        if field == "cert_time":
            col = "u.cert_time"
        else:
            col = f"json_extract(u.ext_data, '$.{field}')"

        if op in {"exists", "not_exists"}:
            base = sql_select(f"{col} IS NOT NULL AND TRIM({col}) != ''", [])
            return base if op == "exists" else (all_ids - base)

        if op in {"eq", "neq", "contains", "not_contains", "gt", "gte", "lt", "lte"}:
            v = str(rule.get("value") or "").strip()
            if not v:
                return set()
            if op in {"eq", "neq"}:
                base = sql_select(f"{col} = ?", [v])
                return base if op == "eq" else (all_ids - base)
            if op in {"contains", "not_contains"}:
                base = sql_select(f"{col} LIKE ?", [f"%{v}%"])
                return base if op == "contains" else (all_ids - base)
            op_map = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
            base = sql_select(f"{col} {op_map[op]} ?", [v])
            return base

        if op in {"in", "not_in"}:
            vals = split_multi_values(rule.get("values"))
            if not vals:
                return set()
            placeholders = ",".join(["?"] * len(vals))
            base = sql_select(f"{col} IN ({placeholders})", vals)
            return base if op == "in" else (all_ids - base)

    if field in {"region", "is_foreign", "org_group", "org_subtype", "office_location"}:
        def sql_select_org(where: str, params: List[Any]) -> Set[str]:
            cursor.execute(
                f"""
                SELECT u.uid
                FROM rsc_users u
                LEFT JOIN rsc_orgs o ON u.oid = o.oid
                WHERE u.ext_data IS NOT NULL AND {where}
                """,
                params,
            )
            return {str(r[0]) for r in cursor.fetchall()}

        if field == "is_foreign":
            truthy = {"1", "true", "yes", "y", "是", "外资", "纯外资机构"}
            falsy = {"0", "false", "no", "n", "否"}

            def is_true(s: str) -> Optional[bool]:
                ss = (s or "").strip().lower()
                if not ss:
                    return False
                if ss in falsy:
                    return False
                if ss in truthy:
                    return True
                return True if "外资" in ss else None

            if op in {"exists", "not_exists"}:
                base = sql_select_org("(o.is_foreign IS NOT NULL AND TRIM(o.is_foreign) != '')", [])
                return base if op == "exists" else (all_ids - base)

            if op in {"eq", "neq"}:
                b = is_true(str(rule.get("value") or ""))
                if b is None:
                    return set()
                base = sql_select_org("(o.is_foreign IS NOT NULL AND TRIM(o.is_foreign) != '')", [])
                out = base if b else (all_ids - base)
                return out if op == "eq" else (all_ids - out)

        if field in {"is_foreign", "region"}:
            col = f"o.{field}"
        else:
            col = f"json_extract(o.ext_data, '$.{field}')"

        if op in {"exists", "not_exists"}:
            base = sql_select_org(f"{col} IS NOT NULL AND TRIM({col}) != ''", [])
            return base if op == "exists" else (all_ids - base)

        if op in {"eq", "neq", "contains", "not_contains", "gt", "gte", "lt", "lte"}:
            v = str(rule.get("value") or "").strip()
            if not v:
                return set()
            if op in {"eq", "neq"}:
                base = sql_select_org(f"{col} = ?", [v])
                return base if op == "eq" else (all_ids - base)
            if op in {"contains", "not_contains"}:
                base = sql_select_org(f"{col} LIKE ?", [f"%{v}%"])
                return base if op == "contains" else (all_ids - base)
            op_map = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
            base = sql_select_org(f"{col} {op_map[op]} ?", [v])
            return base

        if op in {"in", "not_in"}:
            vals = split_multi_values(rule.get("values"))
            if not vals:
                return set()
            placeholders = ",".join(["?"] * len(vals))
            base = sql_select_org(f"{col} IN ({placeholders})", vals)
            return base if op == "in" else (all_ids - base)

    if field in {"value_score", "influence_score"}:
        def sql_select_org(where: str, params: List[Any]) -> Set[str]:
            cursor.execute(
                f"""
                SELECT u.uid
                FROM rsc_users u
                LEFT JOIN rsc_orgs o ON u.oid = o.oid
                WHERE u.ext_data IS NOT NULL AND {where}
                """,
                params,
            )
            return {str(r[0]) for r in cursor.fetchall()}

        col = f"o.{field}"

        if op in {"exists", "not_exists"}:
            base = sql_select_org(f"{col} IS NOT NULL", [])
            return base if op == "exists" else (all_ids - base)

        if op in {"eq", "neq", "gt", "gte", "lt", "lte"}:
            v = str(rule.get("value") or "").strip()
            if not v:
                return set()
            if op in {"eq", "neq"}:
                base = sql_select_org(f"{col} = ?", [v])
                return base if op == "eq" else (all_ids - base)
            op_map = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
            base = sql_select_org(f"{col} {op_map[op]} ?", [v])
            return base

        if op in {"in", "not_in"}:
            vals = split_multi_values(rule.get("values"))
            if not vals:
                return set()
            placeholders = ",".join(["?"] * len(vals))
            base = sql_select_org(f"{col} IN ({placeholders})", vals)
            return base if op == "in" else (all_ids - base)

    if field == "invest_profile":
        def sql_select_org(where: str, params: List[Any]) -> Set[str]:
            cursor.execute(
                f"""
                SELECT u.uid
                FROM rsc_users u
                LEFT JOIN rsc_orgs o ON u.oid = o.oid
                WHERE u.ext_data IS NOT NULL AND {where}
                """,
                params,
            )
            return {str(r[0]) for r in cursor.fetchall()}

        cols = [
            "o.invest_position",
            "json_extract(o.ext_data, '$.invest_pos')",
            "json_extract(o.ext_data, '$.invest_style')",
        ]

        if op in {"exists", "not_exists"}:
            base = sql_select_org("(" + " OR ".join([f"({c} IS NOT NULL AND TRIM({c}) != '')" for c in cols]) + ")", [])
            return base if op == "exists" else (all_ids - base)

        if op in {"eq", "neq", "contains", "not_contains"}:
            v = str(rule.get("value") or "").strip()
            if not v:
                return set()
            if op in {"eq", "neq"}:
                where = "(" + " OR ".join([f"{c} = ?" for c in cols]) + ")"
                params = [v] * len(cols)
                base = sql_select_org(where, params)
                return base if op == "eq" else (all_ids - base)
            where = "(" + " OR ".join([f"{c} LIKE ?" for c in cols]) + ")"
            params = [f"%{v}%"] * len(cols)
            base = sql_select_org(where, params)
            return base if op == "contains" else (all_ids - base)

        if op in {"in", "not_in"}:
            vals = split_multi_values(rule.get("values"))
            if not vals:
                return set()
            placeholders = ",".join(["?"] * len(vals))
            where = "(" + " OR ".join([f"{c} IN ({placeholders})" for c in cols]) + ")"
            params: List[Any] = []
            for _ in cols:
                params.extend(vals)
            base = sql_select_org(where, params)
            return base if op == "in" else (all_ids - base)

    if field in {"name", "institution"}:
        col = "name" if field == "name" else "org_name"

        if op in {"exists", "not_exists"}:
            cursor.execute(f"SELECT uid FROM rsc_users WHERE {col} IS NOT NULL AND {col} != ''")
            exists_set = {str(r[0]) for r in cursor.fetchall()}
            return exists_set if op == "exists" else (all_ids - exists_set)

        if op in {"eq", "neq", "contains", "not_contains"}:
            v = str(rule.get("value") or "").strip()
            if not v:
                return set()
            if op in {"eq", "neq"}:
                cursor.execute(f"SELECT uid FROM rsc_users WHERE {col} = ?", (v,))
                base = {str(r[0]) for r in cursor.fetchall()}
                return base if op == "eq" else (all_ids - base)
            cursor.execute(f"SELECT uid FROM rsc_users WHERE {col} LIKE ?", (f"%{v}%",))
            base = {str(r[0]) for r in cursor.fetchall()}
            return base if op == "contains" else (all_ids - base)

        if op in {"in", "not_in"}:
            vals = split_multi_values(rule.get("values"))
            if not vals:
                return set()
            placeholders = ",".join(["?"] * len(vals))
            cursor.execute(f"SELECT uid FROM rsc_users WHERE {col} IN ({placeholders})", vals)
            base = {str(r[0]) for r in cursor.fetchall()}
            return base if op == "in" else (all_ids - base)

    return set()

def build_memory_indices(cursor):
    global tag_index, aum_index, all_rsc_uids, office_city_index, shenwan1_index, org_type_index, outdated_rsc_uids
    tag_index.clear()
    aum_index.clear()
    all_rsc_uids.clear()
    office_city_index.clear()
    shenwan1_index.clear()
    org_type_index.clear()
    outdated_rsc_uids.clear()
    
    try:
        cursor.execute("""
            SELECT u.uid, u.ext_data, o.aum 
            FROM rsc_users u
            LEFT JOIN rsc_orgs o ON u.oid = o.oid
        """)
        rows = cursor.fetchall()
        
        for row in rows:
            uid = row[0]
            if uid is None:
                continue
            uid = str(uid)
            rsc_info_str = row[1]
            aum_val = row[2]

            all_rsc_uids.add(uid)
            
            if rsc_info_str:
                try:
                    info = json.loads(rsc_info_str)
                    for tag in extract_user_tags(info):
                        tag_index[tag].add(uid)

                    city = normalize_office_city(info.get("office_city"))
                    if city:
                        office_city_index[city].add(uid)
                    sw1 = str(info.get("shenwan_1") or "").strip()
                    if sw1:
                        shenwan1_index[sw1].add(uid)
                    ot = normalize_org_type(info.get("org_type"))
                    if ot:
                        org_type_index[ot].add(uid)
                except json.JSONDecodeError:
                    pass
            
            if aum_val:
                aum = str(aum_val)
                if '百亿' in aum or '100亿' in aum:
                    aum_index['>100亿'].add(uid)
                elif '50' in aum and '100' in aum:
                    aum_index['50-100亿'].add(uid)
                elif '20' in aum and '50' in aum:
                    aum_index['20-50亿'].add(uid)
                elif '0' in aum and '20' in aum:
                    aum_index['0-20亿'].add(uid)
        try:
            cursor.execute("SELECT DISTINCT rsc_uid FROM rsc_user_mapping WHERE rsc_uid IS NOT NULL AND is_outdated = 1")
            for r in cursor.fetchall():
                if r and r[0]:
                    outdated_rsc_uids.add(str(r[0]))
        except sqlite3.OperationalError:
            pass
    except sqlite3.OperationalError as e:
        print("Warning: Skipping memory indices.", e)
        
    print(f"Memory indices built: {len(tag_index)} tags, {len(aum_index)} AUM levels")

class SearchResultItem(BaseModel):
    id: str
    name: str
    institution: str
    source: str
    title: str = ""
    avatar_url: str = ""
    past_match: Optional[Dict[str, str]] = None
    is_rsc: bool = False
    updated_at: str = ""
    reg_date: str = ""
    is_outdated: bool = False
    top_tags: List[str] = []
    pref_industries_top3: List[str] = []
    org_aum: str = ""

class SearchResponse(BaseModel):
    total: int
    items: List[SearchResultItem]
    page: int
    size: int
    meta: Dict[str, Any] = Field(default_factory=dict)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatFilterRequest(BaseModel):
    messages: List[ChatMessage]

def _extract_city_from_text(text: str) -> str:
    cities = ["北京", "上海", "深圳", "广州", "杭州", "成都", "南京", "苏州", "武汉", "西安", "重庆", "天津", "香港"]
    for c in cities:
        if c in (text or ""):
            return c
    tt = str(text or "").lower().replace(" ", "")
    if "hongkong" in tt or tt == "hk":
        return "香港"
    return ""

def _extract_soft_tags_from_text(text: str, limit: int = 8) -> List[str]:
    t = str(text or "")
    seeds = []
    if any(k in t for k in ["科技", "AI", "人工智能", "云计算", "机器人", "智能驾驶", "半导体", "SaaS", "软件", "AIGC"]):
        seeds.extend(["AI", "人工智能", "机器人", "云计算", "智能驾驶", "半导体", "SaaS", "软件", "计算机", "通信", "AIGC"])
    if any(k in t for k in ["医药", "医疗", "医院", "药企", "创新药", "器械"]):
        seeds.extend(["医药", "医疗", "创新药", "器械"])
    if any(k in t for k in ["消费", "食品", "零售", "纺织", "美妆"]):
        seeds.extend(["食品饮料", "商贸零售", "美容护理", "纺织服饰"])
    if not seeds:
        return []
    return suggest_existing_tags(seeds, limit=max(1, min(int(limit), 20)))

def _estimate_total_via_search(filters: Dict[str, Any], query_obj: Optional[Dict[str, Any]], sort_by: str) -> int:
    try:
        adv_query = json.dumps(query_obj, ensure_ascii=False) if query_obj else None
        res = search_talents(
            name=None,
            institution=None,
            only_rsc=False,
            tags=str(filters.get("tags") or "") or None,
            aum=None,
            adv_shenwan_1=str(filters.get("adv_shenwan_1") or "") or None,
            adv_office_city=str(filters.get("adv_office_city") or "") or None,
            adv_org_type=str(filters.get("adv_org_type") or "") or None,
            adv_query=adv_query,
            sort_by=sort_by,
            page=1,
            size=1,
        )
        if isinstance(res, dict):
            return int(res.get("total") or 0)
    except Exception:
        return 0
    return 0

def _make_candidate(title: str, filters: Dict[str, Any], query_obj: Optional[Dict[str, Any]], sort_by: str, rationale: str, relax_level: int) -> Dict[str, Any]:
    total = _estimate_total_via_search(filters, query_obj, sort_by)
    cid = f"cand_{abs(hash((title, json.dumps(filters, ensure_ascii=False, sort_keys=True), json.dumps(query_obj, ensure_ascii=False, sort_keys=True) if query_obj else '', sort_by, relax_level))) % 10**10}"
    return {
        "id": cid,
        "title": title,
        "confidence": 0.0,
        "estimated_total": total,
        "sort_by": sort_by,
        "filters": filters,
        "query": query_obj,
        "rationale": rationale,
        "relax_level": int(relax_level),
    }

def build_chat_guidance(last_user_text: str, recognized_filters: Dict[str, Any]) -> Dict[str, Any]:
    text = str(last_user_text or "")
    city = str(recognized_filters.get("adv_office_city") or "") or _extract_city_from_text(text)
    soft_tags = _extract_soft_tags_from_text(text, limit=8)

    is_sell_side = any(k in text for k in ["卖方", "券商", "证券公司", "研究所", "投研", "分析师", "研究员"])
    is_buy_side = any(k in text for k in ["买方", "公募", "私募", "资管", "保险", "银行理财", "基金", "基金经理", "投资经理"])

    candidates: List[Dict[str, Any]] = []
    quick_replies: List[Dict[str, Any]] = []

    base_filters: Dict[str, Any] = {}
    if city:
        base_filters["adv_office_city"] = city
    if is_sell_side:
        base_filters["adv_org_type"] = "证券公司"
    elif is_buy_side:
        base_filters["adv_org_type"] = "公募基金,私募基金,券商资管,保险资管,银行理财"

    if soft_tags:
        base_filters["tags"] = ",".join(soft_tags)

    if base_filters:
        candidates.append(
            _make_candidate(
                title=("先按当前理解检索" + (f"（{city}）" if city else "")),
                filters=base_filters,
                query_obj={"field": "adv_office_city", "op": "eq", "value": city} if city else None,
                sort_by="relevance",
                rationale="先用你提到的关键信息做一次检索，并按相关性排序；标签会作为排序偏好，不会导致 0 结果。",
                relax_level=0,
            )
        )

    if city:
        relaxed = dict(base_filters)
        relaxed.pop("adv_office_city", None)
        candidates.append(
            _make_candidate(
                title="放宽城市（全国）",
                filters=relaxed,
                query_obj=None,
                sort_by="relevance",
                rationale="如果该城市样本偏少，可以先放宽到全国，再按相关性排序挑选更贴近的人。",
                relax_level=1,
            )
        )

    if city and soft_tags:
        tech_industry = ["计算机", "通信", "电子"]
        expanded = dict(base_filters)
        expanded["adv_shenwan_1"] = ",".join(tech_industry)
        candidates.append(
            _make_candidate(
                title="城市 + 科技相关行业（更宽）",
                filters=expanded,
                query_obj={
                    "op": "and",
                    "children": [
                        {"field": "adv_office_city", "op": "eq", "value": city},
                        {"field": "adv_shenwan_1", "op": "in", "values": tech_industry},
                    ],
                },
                sort_by="relevance",
                rationale="用申万一级行业作为更稳的范围（计算机/通信/电子），再用标签做相关性排序。",
                relax_level=0,
            )
        )

    if city:
        quick_replies.append(
            {"id": "qr_city_only", "label": f"先按{city}搜一下", "patch": {"filters": {"adv_office_city": city}, "sort_by": "relevance"}}
        )
        quick_replies.append({"id": "qr_city_relax", "label": "放宽到全国", "patch": {"filters": {"adv_office_city": ""}, "sort_by": "relevance"}})
    quick_replies.append({"id": "qr_buy_side", "label": "偏买方", "patch": {"filters": {"adv_org_type": "公募基金,私募基金,券商资管,保险资管,银行理财"}, "sort_by": "relevance"}})
    quick_replies.append({"id": "qr_sell_side", "label": "偏卖方", "patch": {"filters": {"adv_org_type": "证券公司"}, "sort_by": "relevance"}})
    if soft_tags:
        quick_replies.append({"id": "qr_keep_2_tags", "label": "只保留2个关键词", "patch": {"filters": {"tags": ",".join(soft_tags[:2])}, "sort_by": "relevance"}})

    candidates.sort(key=lambda x: (int(x.get("estimated_total") or 0), -int(x.get("relax_level") or 0)), reverse=True)
    candidates = candidates[:3]

    msg_parts = []
    if city:
        msg_parts.append(f"我先理解你想找：{city}相关的人。")
    else:
        msg_parts.append("我先理解你想找某个方向的金融人才。")
    if soft_tags:
        msg_parts.append(f"方向关键词我先按：{'、'.join(soft_tags[:6])}。")
    msg_parts.append("你更希望优先限定城市/行业/机构类型中的哪一个？可以点下面的选项。")

    return {
        "message": "".join(msg_parts),
        "candidates": candidates,
        "quick_replies": quick_replies[:6],
    }

BUY_SIDE_ORG_TYPES = "公募基金,私募基金,券商资管,保险资管,银行理财"
SELL_SIDE_ORG_TYPES = "证券公司"

def infer_intent(text: str) -> str:
    t = str(text or "")
    buy = any(k in t for k in ["买方", "公募", "私募", "资管", "保险", "银行理财", "基金", "基金经理", "投资经理"])
    sell = any(k in t for k in ["卖方", "券商", "证券公司", "研究所"])
    if buy and sell:
        return "conflict"
    if buy:
        return "buy_side"
    if sell:
        return "sell_side"
    return "unknown"

def _apply_org_type_to_filters_and_query(filters_out: Dict[str, Any], children: List[Dict[str, Any]], org_value: str) -> None:
    if not org_value:
        return
    filters_out["adv_org_type"] = org_value
    vals = split_multi_values(org_value)
    if len(vals) > 1:
        children.append({"field": "adv_org_type", "op": "in", "values": vals})
    else:
        children.append({"field": "adv_org_type", "op": "eq", "value": org_value})

def apply_intent_guardrails(last_user_text: str, resp: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(resp, dict):
        return resp

    intent = infer_intent(last_user_text)
    if intent == "unknown":
        return resp

    if intent == "conflict":
        city = ""
        try:
            city = str((resp.get("filters") or {}).get("adv_office_city") or "")
        except Exception:
            city = ""

        base_filters = dict(resp.get("filters") or {})
        base_query = resp.get("query") if isinstance(resp.get("query"), dict) else None
        if not city:
            city = _extract_city_from_text(last_user_text)
            if city:
                base_filters["adv_office_city"] = city
                base_query = {"field": "adv_office_city", "op": "eq", "value": city}

        buy_filters = dict(base_filters)
        sell_filters = dict(base_filters)
        buy_children: List[Dict[str, Any]] = []
        sell_children: List[Dict[str, Any]] = []
        if city:
            buy_children.append({"field": "adv_office_city", "op": "eq", "value": city})
            sell_children.append({"field": "adv_office_city", "op": "eq", "value": city})
        _apply_org_type_to_filters_and_query(buy_filters, buy_children, BUY_SIDE_ORG_TYPES)
        _apply_org_type_to_filters_and_query(sell_filters, sell_children, SELL_SIDE_ORG_TYPES)

        buy_query = buy_children[0] if len(buy_children) == 1 else {"op": "and", "children": buy_children} if buy_children else base_query
        sell_query = sell_children[0] if len(sell_children) == 1 else {"op": "and", "children": sell_children} if sell_children else base_query

        candidates = [
            _make_candidate(
                title="按买方机构投资者检索",
                filters=buy_filters,
                query_obj=buy_query,
                sort_by="relevance",
                rationale="你提到了“买方”，我会优先限定为机构投资者（公募/私募/资管/保险/理财），再按相关性排序。",
                relax_level=0,
            ),
            _make_candidate(
                title="按卖方（券商研究）检索",
                filters=sell_filters,
                query_obj=sell_query,
                sort_by="relevance",
                rationale="你同时提到了“卖方/券商”等，我也提供一份卖方研究人群的检索方案供你选择。",
                relax_level=0,
            ),
        ]
        candidates.sort(key=lambda x: int(x.get("estimated_total") or 0), reverse=True)
        candidates = candidates[:2]

        quick_replies = [
            {"id": "qr_pick_buy", "label": "就按买方", "patch": {"filters": {"adv_org_type": BUY_SIDE_ORG_TYPES}, "sort_by": "relevance"}},
            {"id": "qr_pick_sell", "label": "就按卖方", "patch": {"filters": {"adv_org_type": SELL_SIDE_ORG_TYPES}, "sort_by": "relevance"}},
        ]
        return {
            "type": "clarify",
            "message": "你同时提到了买方和卖方，我先给出两个方向的检索方案，你可以点选其一继续。",
            "candidates": candidates,
            "quick_replies": quick_replies,
        }

    desired_org = BUY_SIDE_ORG_TYPES if intent == "buy_side" else SELL_SIDE_ORG_TYPES
    if resp.get("type") == "search":
        filters = resp.get("filters") if isinstance(resp.get("filters"), dict) else {}
        if filters.get("adv_org_type") != desired_org:
            filters = dict(filters)
            filters["adv_org_type"] = desired_org
            resp["filters"] = filters

        q = resp.get("query")
        if isinstance(q, dict):
            try:
                if q.get("field") == "adv_org_type":
                    resp["query"] = {"field": "adv_org_type", "op": "eq", "value": desired_org} if "," not in desired_org else {"field": "adv_org_type", "op": "in", "values": split_multi_values(desired_org)}
                elif q.get("op") in ("and", "or") and isinstance(q.get("children"), list):
                    has_org = any(isinstance(c, dict) and c.get("field") == "adv_org_type" for c in q.get("children"))
                    if not has_org:
                        q = dict(q)
                        children = list(q.get("children") or [])
                        children.append({"field": "adv_org_type", "op": "in", "values": split_multi_values(desired_org)} if "," in desired_org else {"field": "adv_org_type", "op": "eq", "value": desired_org})
                        q["children"] = children
                        resp["query"] = q
            except Exception:
                pass

        resp["sort_by"] = "relevance"

        soft = split_multi_values(filters.get("tags")) if isinstance(filters, dict) else []
        city = str(filters.get("adv_office_city") or "") if isinstance(filters, dict) else ""
        intent_label = "买方（机构投资者）" if intent == "buy_side" else "卖方（券商研究）"
        hard = []
        if city:
            hard.append(city)
        hard.append(intent_label)
        msg = f"我理解你的意图是：{intent_label}。已按硬条件（{' + '.join(hard)}）检索"
        if soft:
            msg += f"，并按关键词偏好（{'、'.join(soft[:6])}）做相关性排序。"
        else:
            msg += "。"
        resp["message"] = msg

    return resp

@app.post("/api/chat/filter")
async def chat_filter(request: ChatFilterRequest):
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("DEEPSEEK_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://api.deepseek.com"
    ssl_verify = (os.environ.get("DEEPSEEK_SSL_VERIFY") or os.environ.get("OPENAI_SSL_VERIFY") or "true").lower() not in ("0", "false", "no")
    
    if not api_key:
        last_user_text = ""
        for m in reversed(request.messages):
            if m.role == "user":
                last_user_text = str(m.content or "")
                break

        cities = ["北京", "上海", "深圳", "广州", "杭州", "成都", "南京", "苏州", "武汉", "西安", "重庆", "天津"]
        recognized: Dict[str, str] = {}
        for c in cities:
            if c in last_user_text:
                recognized["adv_office_city"] = c
                break

        if any(k in last_user_text for k in ["卖方", "券商", "证券公司", "研究所", "投研"]):
            recognized["adv_org_type"] = "证券公司"

        if any(k in last_user_text for k in ["科技", "AI", "人工智能", "云计算", "机器人", "智能驾驶", "半导体", "SaaS", "软件"]):
            tech_suggestions = suggest_existing_tags(
                ["AI", "人工智能", "机器人", "云计算", "智能驾驶", "半导体", "SaaS", "软件", "计算机", "通信"],
                limit=8
            )
            filters_out: Dict[str, Any] = {}
            children = []
            if recognized.get("adv_office_city"):
                filters_out["adv_office_city"] = recognized["adv_office_city"]
                children.append({"field": "adv_office_city", "op": "eq", "value": recognized["adv_office_city"]})
            if tech_suggestions:
                filters_out["tags"] = ",".join(tech_suggestions)
                children.append({"field": "tags", "op": "in", "values": tech_suggestions})
            q = children[0] if len(children) == 1 else {"op": "and", "children": children}
            if children:
                return {
                    "type": "search",
                    "filters": filters_out,
                    "query": q,
                    "message": f"大模型暂时不可用，已先按“科技”相关高频标签做兜底检索：{'、'.join(tech_suggestions) if tech_suggestions else '（暂无可用科技标签）'}。你也可以指定更精确的申万一级行业（计算机/通信/电子等）。"
                }

        guidance = build_chat_guidance(last_user_text, recognized)
        return {"type": "clarify", **guidance}
        
    system_prompt = """You are a search assistant for a financial talent database.
Your task is to analyze the user's input and convert it into structured search filters.

Available filter fields:
- `adv_shenwan_1`: Shenwan Level 1 Industry (e.g., "计算机", "电子", "医药生物", "非银金融", "新能源", "食品饮料", etc.)
- `adv_office_city`: Office City (e.g., "北京", "上海", "深圳", "广州", "杭州", etc.)
- `name`: Talent Name
- `institution`: Institution/Company Name
- `tags`: Specific skill, behavior tags, or research industries
- `adv_org_type`: Organization Type (e.g., "证券公司/券商(卖方)", "公募基金", "券商资管", "私募基金", "保险资管", "银行理财", etc.)

Instructions:
1. Analyze the conversation history.
2. If the user's intent is unclear, ambiguous, or too broad (e.g., "find me someone", "who is good"), return a JSON object asking for clarification:
   {"type": "clarify", "message": "Your clarifying question here..."}
 3. If the user provides enough information to form a search (e.g., an industry, city, name, institution, or tag), extract the relevant filters and return a JSON search object:
    {"type": "search", "filters": { "adv_shenwan_1": "...", "adv_office_city": "...", "name": "...", "institution": "...", "tags": "...", "adv_org_type": "..." }, "query": {"op":"and","children":[{"field":"adv_office_city","op":"eq","value":"上海"}]}, "message": "optional explanation"}
   Only include the keys in `filters` that have a value extracted from the user's input.
4. Do NOT invent fields outside the allowed keys. If a concept has no supported field (e.g., "最近活跃"), explain it briefly and ask the user to rephrase with supported filters.
5. Prefer values that exist in the database. If the user uses a broad term like "科技" but it is not an exact tag, choose a close Shenwan-1 industry (e.g., 计算机/通信/电子) and/or ask a follow-up question to disambiguate.
6. `query` is an advanced filter expression. It is optional but preferred when you need OR logic or multi-selection. Use this schema:
   - Group: {"op": "and"|"or", "children": [Group|Rule, ...]}
   - Rule: {"field": <allowed>, "op": <allowed>, "value": <string>} OR {"field": <allowed>, "op": "in"|"not_in", "values": [<string>, ...]} OR {"field": <allowed>, "op": "exists"|"not_exists"}
   Allowed fields: adv_office_city, adv_shenwan_1, adv_org_type, name, institution, tags
   Allowed ops: eq, neq, contains, not_contains, in, not_in, exists, not_exists
   
Output ONLY valid JSON, with no markdown formatting (no ```json) or extra text.
"""

    try:
        stats_for_prompt = compute_filter_stats(top_n=30)
        system_prompt = system_prompt + "\n\nDatabase value hints (top by count):\n" + format_filter_stats_for_prompt(stats_for_prompt, top_n=18)
    except Exception:
        pass

    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        url = base
    else:
        url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    model_id = os.environ.get("DEEPSEEK_MODEL") or os.environ.get("OPENAI_MODEL") or "deepseek-v4-flash"

    debug = os.environ.get("LLM_DEBUG", "").lower() in ("1", "true", "yes", "y")
    max_history = max(1, min(int(os.environ.get("CHAT_FILTER_MAX_HISTORY", "16")), 40))
    incoming = [{"role": m.role, "content": str(m.content or "")} for m in request.messages]
    if len(incoming) > max_history:
        incoming = incoming[-max_history:]

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(incoming)
    
    payload = {
        "model": model_id,
        "messages": messages,
        "thinking": {"type": "disabled"},
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
        "stream": False
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        context = ssl.create_default_context() if ssl_verify else ssl._create_unverified_context()
        resp_body = ""
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60.0, context=context) as response:
                    resp_body = response.read().decode("utf-8")
                break
            except urllib.error.HTTPError as e:
                code = getattr(e, "code", None)
                if code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                raise
            except urllib.error.URLError as e:
                if attempt < 2:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                raise

            try:
                data = json.loads(resp_body)
            except json.JSONDecodeError:
                return {"type": "clarify", "message": "大模型返回了非 JSON 响应（可能是流式输出），请稍后重试。"}

            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"].get("content")
                if isinstance(content, list):
                    parts = []
                    for p in content:
                        if isinstance(p, dict) and p.get("type") == "text":
                            parts.append(str(p.get("text") or ""))
                        elif isinstance(p, str):
                            parts.append(p)
                    content = "".join(parts)
                content = str(content or "").strip()
                if debug:
                    print(f"RAW LLM RESPONSE: {content}")
            else:
                return {"type": "clarify", "message": "大模型返回结构异常，请稍后重试。"}
            
            import re
            
            content = ''.join(char for char in content if ord(char) >= 32 or char in '\n\r\t')
            content = content.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
            
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL | re.IGNORECASE)
            if json_match:
                content = json_match.group(1).strip()
            else:
                if "{" in content and "}" in content:
                    start_idx = content.find("{")
                    end_idx = content.rfind("}") + 1
                    content = content[start_idx:end_idx].strip()
                    
            try:
                last_user_text = ""
                for m in reversed(request.messages):
                    if m.role == "user":
                        last_user_text = m.content or ""
                        break

                parsed = json.loads(content)
                if isinstance(parsed, dict) and parsed.get("type") == "search" and isinstance(parsed.get("filters"), dict):
                    filters_in: Dict[str, Any] = parsed.get("filters") or {}

                    allowed_cities = {"北京", "上海", "深圳", "广州", "杭州", "成都", "南京", "苏州", "武汉", "西安", "重庆", "天津"}
                    allowed_shenwan_1 = {
                        "农林牧渔", "基础化工", "钢铁", "有色金属", "电子", "家用电器", "食品饮料", "纺织服饰", "轻工制造",
                        "医药生物", "公用事业", "交通运输", "房地产", "商贸零售", "社会服务", "综合", "建筑材料", "建筑装饰",
                        "电力设备", "机械设备", "国防军工", "汽车", "计算机", "传媒", "通信", "银行", "非银金融", "美容护理",
                        "石油石化", "环保", "煤炭"
                    }
                    allowed_org_type = {"证券公司", "公募基金", "券商资管", "私募基金", "保险资管", "银行理财"}

                    normalized: Dict[str, str] = {}
                    hints: List[str] = []

                    is_sell_side = any(k in last_user_text for k in ["卖方", "券商", "证券公司", "研究所", "投研"])
                    is_buy_side = any(k in last_user_text for k in ["买方", "公募", "私募", "资管", "保险", "银行理财", "基金", "基金经理", "投资经理", "投研"])

                    if "adv_office_city" in filters_in:
                        city = str(filters_in.get("adv_office_city") or "").strip()
                        if city in allowed_cities:
                            normalized["adv_office_city"] = city
                        else:
                            for c in allowed_cities:
                                if c and c in last_user_text:
                                    normalized["adv_office_city"] = c
                                    break

                    if "adv_org_type" in filters_in:
                        org = str(filters_in.get("adv_org_type") or "").strip()
                        if org in allowed_org_type:
                            normalized["adv_org_type"] = org
                        else:
                            if is_sell_side:
                                normalized["adv_org_type"] = "证券公司"
                            elif is_buy_side:
                                normalized["adv_org_type"] = "公募基金,私募基金,券商资管,保险资管,银行理财"
                                hints.append("已按“买方”语义扩展为：公募基金/私募基金/券商资管/保险资管/银行理财。")
                            else:
                                hints.append("机构类型请从：证券公司/公募基金/券商资管/私募基金/保险资管/银行理财 中选择")
                    else:
                        if is_sell_side:
                            normalized["adv_org_type"] = "证券公司"
                        elif is_buy_side:
                            normalized["adv_org_type"] = "公募基金,私募基金,券商资管,保险资管,银行理财"
                            hints.append("已按“买方”语义扩展为：公募基金/私募基金/券商资管/保险资管/银行理财。")

                    if "adv_shenwan_1" in filters_in:
                        sw = str(filters_in.get("adv_shenwan_1") or "").strip()
                        if sw in allowed_shenwan_1:
                            normalized["adv_shenwan_1"] = sw
                        else:
                            if "消费" in last_user_text:
                                normalized["adv_shenwan_1"] = "食品饮料,商贸零售,社会服务,纺织服饰,美容护理"
                                hints.append("已按“消费”语义扩展为：食品饮料/商贸零售/社会服务/纺织服饰/美容护理。")
                            elif sw:
                                hints.append(f"申万一级行业需要使用标准名称（例如：{sw} 可能不在可用列表中）")
                    else:
                        if "消费" in last_user_text:
                            normalized["adv_shenwan_1"] = "食品饮料,商贸零售,社会服务,纺织服饰,美容护理"
                            hints.append("已按“消费”语义扩展为：食品饮料/商贸零售/社会服务/纺织服饰/美容护理。")
                        elif any(k in last_user_text for k in ["医药", "医疗", "医院", "药企", "创新药", "器械"]):
                            normalized["adv_shenwan_1"] = "医药生物"

                    for k in ["name", "institution"]:
                        if k in filters_in:
                            v = str(filters_in.get(k) or "").strip()
                            if v:
                                normalized[k] = v

                    if "tags" in filters_in:
                        raw_tags = split_multi_values(filters_in.get("tags"))
                        valid = [t for t in raw_tags if t in tag_index]
                        invalid = [t for t in raw_tags if t and t not in tag_index]
                        if valid:
                            normalized["tags"] = ",".join(valid)
                        if invalid and not valid:
                            if "科技" in invalid:
                                tech_suggestions = suggest_existing_tags(
                                    ["AI", "人工智能", "机器人", "云计算", "智能驾驶", "半导体", "SaaS", "软件", "计算机", "通信"],
                                    limit=8
                                )
                                if tech_suggestions:
                                    normalized["tags"] = ",".join(tech_suggestions)
                                    hints.append(f"库内没有“科技”这个标签，已按科技相关高频标签做语义扩展：{'、'.join(tech_suggestions)}。如需更精准，可指定申万一级行业（计算机/通信/电子等）。")
                                else:
                                    hints.append("库内没有“科技”这个标签。建议改用申万一级行业（计算机/通信/电子等）或更具体主题标签（如：人工智能/云计算/机器人）。")
                            else:
                                kw = invalid[:]
                                if any(k in last_user_text for k in ["分析师", "研究员", "基金经理", "投资经理", "量化"]):
                                    kw.extend([k for k in ["分析师", "研究员", "基金经理", "投资经理", "量化"] if k in last_user_text])
                                suggestions = suggest_existing_tags(kw, limit=8)
                                if suggestions:
                                    normalized["tags"] = ",".join(suggestions)
                                    hints.append(f"库内未找到标签：{'、'.join(invalid[:6])}，已按近似高频标签做扩展：{'、'.join(suggestions)}。")
                                else:
                                    hints.append(f"未找到这些标签：{'、'.join(invalid[:6])}。可以换成更具体的行业（申万一级）或从高频标签中选择。")
                        elif invalid:
                            hints.append(f"已忽略不存在的标签：{'、'.join(invalid[:6])}")

                    parsed["filters"] = normalized

                    qn = normalize_filter_query(parsed.get("query"))
                    if qn:
                        qn = expand_tags_in_query(qn, hints)
                        parsed["query"] = qn
                    else:
                        if "query" in parsed:
                            parsed.pop("query", None)
                        if normalized:
                            children = []
                            if normalized.get("adv_office_city"):
                                vals = split_multi_values(normalized["adv_office_city"])
                                if len(vals) > 1:
                                    children.append({"field": "adv_office_city", "op": "in", "values": vals})
                                else:
                                    children.append({"field": "adv_office_city", "op": "eq", "value": normalized["adv_office_city"]})
                            if normalized.get("adv_shenwan_1"):
                                vals = split_multi_values(normalized["adv_shenwan_1"])
                                if len(vals) > 1:
                                    children.append({"field": "adv_shenwan_1", "op": "in", "values": vals})
                                else:
                                    children.append({"field": "adv_shenwan_1", "op": "eq", "value": normalized["adv_shenwan_1"]})
                            if normalized.get("adv_org_type"):
                                vals = split_multi_values(normalized["adv_org_type"])
                                if len(vals) > 1:
                                    children.append({"field": "adv_org_type", "op": "in", "values": vals})
                                else:
                                    children.append({"field": "adv_org_type", "op": "eq", "value": normalized["adv_org_type"]})
                            if normalized.get("name"):
                                children.append({"field": "name", "op": "contains", "value": normalized["name"]})
                            if normalized.get("institution"):
                                children.append({"field": "institution", "op": "contains", "value": normalized["institution"]})
                            if normalized.get("tags"):
                                children.append({"field": "tags", "op": "in", "values": split_multi_values(normalized["tags"])})
                            if len(children) == 1:
                                parsed["query"] = children[0]
                            elif len(children) > 1:
                                parsed["query"] = {"op": "and", "children": children}

                    msg = str(parsed.get("message") or "").strip()
                    if not msg:
                        msg = "我理解你要找符合这些条件的金融人才。"
                    if hints:
                        msg = (msg + "；" + "；".join(hints)).strip("；")
                    parsed["message"] = msg

                    if not normalized:
                        guidance = build_chat_guidance(last_user_text, parsed.get("filters") or {})
                        return {"type": "clarify", **guidance}

                if isinstance(parsed, dict) and parsed.get("type") == "clarify":
                    guidance = build_chat_guidance(last_user_text, parsed.get("filters") or {})
                    parsed.update(guidance)
                    if parsed.get("message"):
                        parsed["message"] = str(parsed.get("message") or "").strip() or str(guidance.get("message") or "")
                    else:
                        parsed["message"] = str(guidance.get("message") or "")
                return apply_intent_guardrails(last_user_text, parsed)
            except json.JSONDecodeError:
                last_user_text = ""
                for m in reversed(request.messages):
                    if m.role == "user":
                        last_user_text = m.content or ""
                        break

                cities = ["北京", "上海", "深圳", "广州", "杭州", "成都", "南京", "苏州", "武汉", "西安", "重庆", "天津"]
                recognized: Dict[str, str] = {}
                for c in cities:
                    if c in last_user_text:
                        recognized["adv_office_city"] = c
                        break

                if any(k in last_user_text for k in ["卖方", "券商", "证券公司", "研究所", "投研"]):
                    recognized["adv_org_type"] = "证券公司"
                elif any(k in last_user_text for k in ["买方", "公募", "私募", "资管", "保险", "银行理财", "基金", "基金经理", "投资经理"]):
                    recognized["adv_org_type"] = "公募基金,私募基金,券商资管,保险资管,银行理财"

                if "消费" in last_user_text:
                    recognized["adv_shenwan_1"] = "食品饮料,商贸零售,社会服务,纺织服饰,美容护理"
                elif any(k in last_user_text for k in ["医药", "医疗", "医院", "药企", "创新药", "器械"]):
                    recognized["adv_shenwan_1"] = "医药生物"

                if any(k in last_user_text for k in ["科技", "AI", "人工智能", "云计算", "机器人", "智能驾驶", "半导体", "SaaS", "软件"]):
                    tech_suggestions = suggest_existing_tags(
                        ["AI", "人工智能", "机器人", "云计算", "智能驾驶", "半导体", "SaaS", "软件", "计算机", "通信"],
                        limit=8
                    )
                    filters_out: Dict[str, Any] = {}
                    children = []
                    if recognized.get("adv_office_city"):
                        filters_out["adv_office_city"] = recognized["adv_office_city"]
                        children.append({"field": "adv_office_city", "op": "eq", "value": recognized["adv_office_city"]})
                    if recognized.get("adv_org_type"):
                        _apply_org_type_to_filters_and_query(filters_out, children, recognized["adv_org_type"])
                    if tech_suggestions:
                        filters_out["tags"] = ",".join(tech_suggestions)
                        children.append({"field": "tags", "op": "in", "values": tech_suggestions})
                    q = children[0] if len(children) == 1 else {"op": "and", "children": children}
                    if children:
                        resp = {
                            "type": "search",
                            "filters": filters_out,
                            "query": q,
                            "sort_by": "relevance",
                            "message": f"大模型返回格式不稳定，已按“科技”相关高频标签做兜底检索：{'、'.join(tech_suggestions) if tech_suggestions else '（暂无可用科技标签）'}。你也可以指定更精确的申万一级行业（计算机/通信/电子等）。"
                        }
                        return apply_intent_guardrails(last_user_text, resp)

                recognized_text = "；".join([f"{k}={v}" for k, v in recognized.items()])
                if recognized_text:
                    guidance = build_chat_guidance(last_user_text, recognized)
                    return {"type": "clarify", **guidance}

                guidance = build_chat_guidance(last_user_text, recognized)
                return {"type": "clarify", **guidance}
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        if os.environ.get("LLM_DEBUG", "").lower() in ("1", "true", "yes", "y"):
            print(f"LLM API HTTPError: {error_body}")
        last_user_text = ""
        for m in reversed(request.messages):
            if m.role == "user":
                last_user_text = str(m.content or "")
                break

        cities = ["北京", "上海", "深圳", "广州", "杭州", "成都", "南京", "苏州", "武汉", "西安", "重庆", "天津"]
        recognized: Dict[str, str] = {}
        for c in cities:
            if c in last_user_text:
                recognized["adv_office_city"] = c
                break

        if any(k in last_user_text for k in ["卖方", "券商", "证券公司", "研究所", "投研"]):
            recognized["adv_org_type"] = "证券公司"
        elif any(k in last_user_text for k in ["买方", "公募", "私募", "资管", "保险", "银行理财", "基金", "基金经理", "投资经理"]):
            recognized["adv_org_type"] = "公募基金,私募基金,券商资管,保险资管,银行理财"

        if any(k in last_user_text for k in ["科技", "AI", "人工智能", "云计算", "机器人", "智能驾驶", "半导体", "SaaS", "软件"]):
            tech_suggestions = suggest_existing_tags(
                ["AI", "人工智能", "机器人", "云计算", "智能驾驶", "半导体", "SaaS", "软件", "计算机", "通信"],
                limit=8
            )
            filters_out: Dict[str, Any] = {}
            children = []
            if recognized.get("adv_office_city"):
                filters_out["adv_office_city"] = recognized["adv_office_city"]
                children.append({"field": "adv_office_city", "op": "eq", "value": recognized["adv_office_city"]})
            if recognized.get("adv_org_type"):
                _apply_org_type_to_filters_and_query(filters_out, children, recognized["adv_org_type"])
            if tech_suggestions:
                filters_out["tags"] = ",".join(tech_suggestions)
                children.append({"field": "tags", "op": "in", "values": tech_suggestions})
            q = children[0] if len(children) == 1 else {"op": "and", "children": children}
            if children:
                resp = {
                    "type": "search",
                    "filters": filters_out,
                    "query": q,
                    "sort_by": "relevance",
                    "message": f"大模型暂时不可用，已先按“科技”相关高频标签做兜底检索：{'、'.join(tech_suggestions) if tech_suggestions else '（暂无可用科技标签）'}。你也可以指定更精确的申万一级行业（计算机/通信/电子等）。"
                }
                return apply_intent_guardrails(last_user_text, resp)

        recognized_text = "；".join([f"{k}={v}" for k, v in recognized.items()])
        if recognized_text:
            guidance = build_chat_guidance(last_user_text, recognized)
            return {"type": "clarify", **guidance}

        guidance = build_chat_guidance(last_user_text, recognized)
        return {"type": "clarify", **guidance}
    except urllib.error.URLError as e:
        return {"type": "clarify", "message": f"大模型接口连接失败: {getattr(e, 'reason', 'unknown')}"}
    except Exception as e:
        import traceback
        error_msg = f"LLM Unexpected Error: {str(e)}\n{traceback.format_exc()}"
        if os.environ.get("LLM_DEBUG", "").lower() in ("1", "true", "yes", "y"):
            print(error_msg)
        return {"type": "clarify", "message": f"内部服务器错误，请稍后再试。"}

@app.on_event("startup")
def startup_event():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sac_name ON sac_practitioners(name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_amac_name ON amac_practitioners(name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sac_updated ON sac_practitioners(updated_at DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_amac_updated ON amac_practitioners(updated_at DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rsc_mapping_practitioner ON rsc_user_mapping(practitioner_id, source_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rsc_mapping_uid ON rsc_user_mapping(rsc_uid);")
    
    # 构建内存索引
    build_memory_indices(cursor)
    
    conn.commit()
    conn.close()

@app.get("/api/stats")
def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM sac_practitioners")
    sac_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM amac_practitioners")
    amac_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM sac_institutions WHERE raw_data LIKE '%\"status\": \"completed\"%'")
    sac_inst = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM amac_institutions")
    amac_inst = cursor.fetchone()[0]
    
    cursor.execute("SELECT MAX(updated_at) FROM (SELECT updated_at FROM sac_practitioners UNION ALL SELECT updated_at FROM amac_practitioners)")
    last_updated_at = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_talents": sac_count + amac_count,
        "total_institutions": sac_inst + amac_inst,
        "sac_talents": sac_count,
        "amac_talents": amac_count,
        "last_updated_at": last_updated_at
    }

@app.get("/api/tags")
def get_tags():
    # 获取高频 tags 和 aum (用于前端展示)
    sorted_tags = sorted(tag_index.items(), key=lambda x: len(x[1]), reverse=True)
    sorted_aum = sorted(aum_index.items(), key=lambda x: len(x[1]), reverse=True)
    
    return {
        "tags": [t[0] for t in sorted_tags[:30]], # 返回前30个高频标签
        "aums": [a[0] for a in sorted_aum]
    }

@app.get("/api/filters/stats")
def get_filter_stats(
    top_n: int = Query(50, ge=1, le=200),
    refresh: bool = False
):
    now = datetime.utcnow()
    built_at = filter_stats_cache.get("built_at")
    cached = filter_stats_cache.get("data")
    ttl_seconds = 300

    if not refresh and built_at and cached and isinstance(built_at, datetime):
        if (now - built_at).total_seconds() < ttl_seconds:
            return cached

    data = compute_filter_stats(top_n=top_n)
    filter_stats_cache["built_at"] = now
    filter_stats_cache["data"] = data
    return data

@app.get("/api/filters/schema")
def get_filter_schema(
    top_n: int = Query(50, ge=1, le=200),
    refresh: bool = False
):
    stats = get_filter_stats(top_n=top_n, refresh=refresh)
    fields = stats.get("fields", {}) if isinstance(stats, dict) else {}

    def opts(k: str) -> List[str]:
        f = fields.get(k, {}) if isinstance(fields, dict) else {}
        options = f.get("options", []) if isinstance(f, dict) else []
        out = []
        for o in options:
            if isinstance(o, dict) and o.get("value"):
                out.append(str(o["value"]))
        return out

    return {
        "built_at": stats.get("built_at"),
        "fields": [
            {"key": "name", "label": "姓名", "type": "text", "ops": ["contains", "not_contains", "eq", "neq", "exists", "not_exists"]},
            {"key": "institution", "label": "机构", "type": "text", "ops": ["contains", "not_contains", "eq", "neq", "exists", "not_exists"]},
            {"key": "adv_org_type", "label": "机构类型", "type": "enum", "ops": ["eq", "neq", "in", "not_in"], "options": opts("adv_org_type")},
            {"key": "adv_office_city", "label": "办公城市", "type": "enum", "ops": ["eq", "neq", "in", "not_in"], "options": opts("adv_office_city")},
            {"key": "country_region", "label": "国家地区", "type": "enum", "ops": ["contains", "not_contains", "eq", "neq", "in", "not_in", "exists", "not_exists"], "options": opts("country_region")},
            {"key": "province", "label": "省份", "type": "enum", "ops": ["contains", "not_contains", "eq", "neq", "in", "not_in", "exists", "not_exists"], "options": opts("province")},
            {"key": "adv_shenwan_1", "label": "申万一级行业", "type": "enum", "ops": ["eq", "neq", "in", "not_in"], "options": opts("adv_shenwan_1")},
            {"key": "pref_industry_l2", "label": "偏好行业(申万二级/GICS)", "type": "enum", "ops": ["contains", "not_contains", "eq", "neq", "in", "not_in", "exists", "not_exists"], "options": opts("pref_industry_l2")},
            {"key": "aum", "label": "机构管理规模", "type": "enum", "ops": ["eq", "neq", "in", "not_in"], "options": opts("aum")},
            {"key": "cert_type", "label": "认证类型", "type": "enum", "ops": ["eq", "neq", "in", "not_in"], "options": opts("cert_type")},
            {"key": "industry_theme", "label": "行业主题", "type": "enum", "ops": ["contains", "not_contains", "eq", "neq", "in", "not_in", "exists", "not_exists"], "options": opts("tags")},
            {"key": "region", "label": "机构区域", "type": "enum", "ops": ["contains", "not_contains", "eq", "neq", "in", "not_in", "exists", "not_exists"], "options": opts("region")},
            {"key": "is_foreign", "label": "是否外资机构", "type": "enum", "ops": ["eq", "neq"], "options": ["是", "否"]},
            {"key": "org_group", "label": "机构分组", "type": "enum", "ops": ["contains", "not_contains", "eq", "neq", "in", "not_in", "exists", "not_exists"], "options": opts("org_group")},
            {"key": "org_subtype", "label": "机构子类", "type": "enum", "ops": ["contains", "not_contains", "eq", "neq", "in", "not_in", "exists", "not_exists"], "options": opts("org_subtype")},
            {"key": "office_location", "label": "机构办公地", "type": "enum", "ops": ["contains", "not_contains", "eq", "neq", "in", "not_in", "exists", "not_exists"], "options": opts("office_location")},
            {"key": "value_score", "label": "价值评分", "type": "enum", "ops": ["eq", "neq", "in", "not_in", "exists", "not_exists"], "options": opts("value_score")},
            {"key": "influence_score", "label": "影响力评分", "type": "enum", "ops": ["eq", "neq", "in", "not_in", "exists", "not_exists"], "options": opts("influence_score")},
            {"key": "invest_profile", "label": "投资定位/风格/策略", "type": "enum", "ops": ["contains", "not_contains", "eq", "neq", "in", "not_in", "exists", "not_exists"], "options": opts("invest_profile")},
            {"key": "last_active_time", "label": "最近活跃时间", "type": "date", "ops": ["gte", "lte", "gt", "lt", "exists", "not_exists"]},
            {"key": "cert_time", "label": "认证时间", "type": "date", "ops": ["gte", "lte", "gt", "lt", "exists", "not_exists"]},
            {"key": "is_outdated", "label": "是否待更新", "type": "boolean", "ops": ["eq", "neq"], "options": ["true", "false"]},
        ],
    }

@app.get("/api/talents/search", response_model=SearchResponse)
def search_talents(
    name: Optional[str] = None,
    institution: Optional[str] = None,
    only_rsc: bool = False,
    include_rsc: bool = False,
    tags: Optional[str] = None,
    aum: Optional[str] = None,
    adv_shenwan_1: Optional[str] = None,
    adv_office_city: Optional[str] = None,
    adv_org_type: Optional[str] = None,
    adv_query: Optional[str] = None,
    sort_by: str = "",
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    offset = (page - 1) * size

    meta: Dict[str, Any] = {"sort_by": sort_by}
    desired_tags_soft: List[str] = []
    
    # Base SQL parts
    sac_select = """
    SELECT p.practitioner_id as id, p.name, p.institution_id as inst_id, 'SAC' as source, p.raw_data, p.updated_at,
           CASE WHEN m.rsc_uid IS NOT NULL THEN 1 ELSE 0 END as is_rsc,
           json_extract(p.raw_data, '$.regDate') as reg_date,
           COALESCE(m.is_outdated, 0) as is_outdated,
           u.ext_data as rsc_info,
           m.rsc_uid as rsc_uid,
           u.org_name as rsc_institution,
           u.position as rsc_title,
           1 as priority
    FROM sac_practitioners p
    LEFT JOIN rsc_user_mapping m ON p.practitioner_id = m.practitioner_id AND m.source_type = 'SAC'
    LEFT JOIN rsc_users u ON m.rsc_uid = u.uid
    """
    amac_select = """
    SELECT p.practitioner_id as id, p.name, p.institution_id as inst_id, 'AMAC' as source, p.raw_data, p.updated_at,
           CASE WHEN m.rsc_uid IS NOT NULL THEN 1 ELSE 0 END as is_rsc,
           date(json_extract(p.raw_data, '$.certObtainDate') / 1000, 'unixepoch') as reg_date,
           COALESCE(m.is_outdated, 0) as is_outdated,
           u.ext_data as rsc_info,
           m.rsc_uid as rsc_uid,
           u.org_name as rsc_institution,
           u.position as rsc_title,
           1 as priority
    FROM amac_practitioners p
    LEFT JOIN rsc_user_mapping m ON p.practitioner_id = m.practitioner_id AND m.source_type = 'AMAC'
    LEFT JOIN rsc_users u ON m.rsc_uid = u.uid
    """
    rsc_select = """
    SELECT u.uid as id, u.name, u.oid as inst_id, 'RSC' as source, '{}' as raw_data, u.register_time as updated_at,
           1 as is_rsc,
           u.cert_time as reg_date,
           COALESCE(m.is_outdated, 0) as is_outdated,
           u.ext_data as rsc_info,
           u.uid as rsc_uid,
           u.org_name as rsc_institution,
           u.position as rsc_title,
           0 as priority
    FROM rsc_users u
    LEFT JOIN (
        SELECT rsc_uid, MAX(COALESCE(is_outdated, 0)) as is_outdated
        FROM rsc_user_mapping
        WHERE rsc_uid IS NOT NULL
        GROUP BY rsc_uid
    ) m ON u.uid = m.rsc_uid
    """
    
    sac_where = []
    amac_where = []
    rsc_where = []
    sac_params = []
    amac_params = []
    rsc_params = []
    
    if name:
        sac_where.append("p.name LIKE ?")
        amac_where.append("p.name LIKE ?")
        sac_params.append(f"%{name}%")
        amac_params.append(f"%{name}%")
        rsc_where.append("u.name LIKE ?")
        rsc_params.append(f"%{name}%")
        
    if institution:
        sac_where.append("p.raw_data LIKE ?")
        amac_where.append("p.raw_data LIKE ?")
        sac_params.append(f"%{institution}%")
        amac_params.append(f"%{institution}%")
        rsc_where.append("u.org_name LIKE ?")
        rsc_params.append(f"%{institution}%")
        
    # 处理内存索引过滤
    valid_ids = None
    
    if adv_shenwan_1:
        sw_ids = set()
        for v in split_multi_values(adv_shenwan_1):
            sw_ids.update(shenwan1_index.get(v, set()))
        valid_ids = sw_ids if valid_ids is None else valid_ids.intersection(sw_ids)
        
    if adv_office_city:
        city_ids = set()
        for v in split_multi_values(adv_office_city):
            city_ids.update(office_city_index.get(v, set()))
        valid_ids = city_ids if valid_ids is None else valid_ids.intersection(city_ids)
        
    if adv_org_type:
        org_ids = set()
        for v in split_multi_values(adv_org_type):
            nv = normalize_org_type(v)
            if nv:
                org_ids.update(org_type_index.get(nv, set()))
        valid_ids = org_ids if valid_ids is None else valid_ids.intersection(org_ids)
        
    if only_rsc:
        sac_where.append("m.rsc_uid IS NOT NULL")
        amac_where.append("m.rsc_uid IS NOT NULL")
        
    if adv_query:
        try:
            q_obj = json.loads(adv_query)
            qn = normalize_filter_query(q_obj)
            if qn:
                if sort_by == "relevance":
                    hard_q, soft_tags = split_query_hard_soft(qn)
                    desired_tags_soft.extend(soft_tags)
                    if hard_q:
                        q_ids = evaluate_filter_query_to_ids(hard_q)
                        meta["hard_query"] = hard_q
                    else:
                        q_ids = set(all_rsc_uids)
                        meta["hard_query"] = {}
                else:
                    q_ids = evaluate_filter_query_to_ids(qn)
                valid_ids = q_ids if valid_ids is None else valid_ids.intersection(q_ids)
        except Exception:
            pass
    if tags:
        if sort_by == "relevance":
            desired_tags_soft.extend(split_multi_values(tags))
        else:
            tag_list = [t.strip() for t in tags.split(',')]
            tag_ids = set()
            for t in tag_list:
                if t in tag_index:
                    tag_ids.update(tag_index[t])
            valid_ids = tag_ids if valid_ids is None else valid_ids.intersection(tag_ids)
        
    if aum:
        aum_list = [a.strip() for a in aum.split(',')]
        aum_ids = set()
        for a in aum_list:
            if a in aum_index:
                aum_ids.update(aum_index[a])
        valid_ids = aum_ids if valid_ids is None else valid_ids.intersection(aum_ids)

    if sort_by == "relevance":
        seen = set()
        dt = []
        for t in desired_tags_soft:
            tt = str(t or "").strip()
            if not tt or tt in seen:
                continue
            seen.add(tt)
            dt.append(tt)
        desired_tags_soft = dt
        meta["soft_tags"] = desired_tags_soft[:20]
        
    if valid_ids is not None:
        if not valid_ids:
            if adv_office_city or (isinstance(meta.get("hard_query"), dict) and "adv_office_city" in json.dumps(meta.get("hard_query"))):
                meta["suggestion"] = "当前筛选条件在该城市下样本不足。建议：放宽到广东/全国，或去掉部分标签，仅保留行业/机构类型。"
            else:
                meta["suggestion"] = "当前筛选条件过窄导致 0 结果。建议：减少标签数量，或改用申万一级行业/机构类型进行检索。"
            return {"total": 0, "items": [], "page": page, "size": size, "meta": meta}
            
        valid_ids_list = list(valid_ids)
        if len(valid_ids_list) <= 900:
            placeholders = ','.join(['?'] * len(valid_ids_list))
            sac_where.append(f"m.rsc_uid IN ({placeholders})")
            sac_params.extend(valid_ids_list)
            amac_where.append(f"m.rsc_uid IN ({placeholders})")
            amac_params.extend(valid_ids_list)
            rsc_where.append(f"u.uid IN ({placeholders})")
            rsc_params.extend(valid_ids_list)
        else:
            cursor.execute("CREATE TEMP TABLE IF NOT EXISTS tmp_rsc_uids (uid TEXT PRIMARY KEY)")
            cursor.execute("DELETE FROM tmp_rsc_uids")
            cursor.executemany("INSERT OR IGNORE INTO tmp_rsc_uids(uid) VALUES (?)", [(i,) for i in valid_ids_list])
            sac_where.append("m.rsc_uid IN (SELECT uid FROM tmp_rsc_uids)")
            amac_where.append("m.rsc_uid IN (SELECT uid FROM tmp_rsc_uids)")
            rsc_where.append("u.uid IN (SELECT uid FROM tmp_rsc_uids)")
            
    sac_query = sac_select
    if sac_where:
        sac_query += " WHERE " + " AND ".join(sac_where)
        
    amac_query = amac_select
    if amac_where:
        amac_query += " WHERE " + " AND ".join(amac_where)
        
    rsc_query = rsc_select
    if rsc_where:
        rsc_query += " WHERE " + " AND ".join(rsc_where)

    unions = [sac_query, amac_query]
    union_params = [sac_params, amac_params]
    if include_rsc or only_rsc or valid_ids is not None or adv_query:
        unions.append(rsc_query)
        union_params.append(rsc_params)

    base_sql = " UNION ALL ".join(unions)
    search_sql = """
    SELECT *
    FROM (
        SELECT t.*,
               ROW_NUMBER() OVER (
                   PARTITION BY (CASE WHEN t.rsc_uid IS NOT NULL THEN 'RSC::' || t.rsc_uid ELSE t.source || '::' || t.id END)
                   ORDER BY t.priority ASC
               ) as rn
        FROM (""" + base_sql + """) t
    )
    WHERE rn = 1
    """
    
    params: List[Any] = []
    for p in union_params:
        params.extend(p)
    
    # Count total
    count_sql = f"SELECT COUNT(*) FROM ({search_sql})"
    cursor.execute(count_sql, params)
    total = cursor.fetchone()[0] or 0

    if total == 0:
        if adv_office_city:
            meta["suggestion"] = "当前城市下样本较少或暂无匹配。建议放宽城市（如广东/全国）或减少标签条件。"
        return {"total": 0, "items": [], "page": page, "size": size, "meta": meta}
    
    # Paginated results
    rows = []
    if sort_by == "relevance":
        prefetch = min(500, max(size * max(page, 1) * 5, size * 5))
        cursor.execute("SELECT * FROM (" + search_sql + ") LIMIT ? OFFSET ?", params + [prefetch, 0])
        rows = cursor.fetchall()
    else:
        order_clause = ""
        order_params: List[Any] = []

        def order_by_json_time(json_key: str) -> str:
            expr = f"json_extract(rsc_info, '$.{json_key}')"
            return f" ORDER BY ({expr} IS NULL) ASC, {expr} DESC, reg_date DESC NULLS LAST"

        if sort_by in ("latest_reg", "latest_job_change"):
            order_clause = " ORDER BY reg_date DESC NULLS LAST"
        elif sort_by == "latest_added":
            order_clause = " ORDER BY updated_at DESC NULLS LAST, reg_date DESC NULLS LAST"
        elif sort_by == "recent_active":
            order_clause = order_by_json_time("last_active_time")
        elif sort_by == "latest_cert":
            order_clause = order_by_json_time("cert_time")
        elif sort_by == "latest_register":
            order_clause = order_by_json_time("register_time")
        elif (not sort_by and (name or institution)):
            score_expr = "0"
            if name:
                score_expr += " + (CASE WHEN name = ? THEN 30 ELSE 0 END)"
                score_expr += " + (CASE WHEN name LIKE ? THEN 10 ELSE 0 END)"
                order_params.extend([name, f"%{name}%"])
            if institution:
                score_expr += " + (CASE WHEN raw_data LIKE ? THEN 5 ELSE 0 END)"
                order_params.append(f"%{institution}%")
            order_clause = f" ORDER BY ({score_expr}) DESC, reg_date DESC NULLS LAST"
        elif not name and not institution and valid_ids is None:
            order_clause = " ORDER BY reg_date DESC NULLS LAST"

        paginated_sql = "SELECT * FROM (" + search_sql + ")" + order_clause + " LIMIT ? OFFSET ?"
        cursor.execute(paginated_sql, params + order_params + [size, offset])
        rows = cursor.fetchall()
    
    items = []
    relevance_tags_by_item: Dict[str, List[str]] = {}
    for row in rows:
        raw = {}
        title = ""
        current_institution = ""
        past_institution_match = None

        if row['source'] == 'RSC':
            current_institution = str(row['rsc_institution'] or "")
            title = str(row['rsc_title'] or "")
        elif row['source'] == 'SAC':
            raw = json.loads(row['raw_data'])
            title = raw.get("pracCtegName", "")
            reg_history = raw.get("regHistory", [])
            
            if reg_history:
                latest_reg = reg_history[-1]
                current_institution = latest_reg.get("org_name", row['inst_id'])
                title = latest_reg.get("reg_type", title)
                
                # Check for past institution match if searching by institution
                if institution:
                    for h in reversed(reg_history):
                        org_name = h.get("org_name", "")
                        if institution.lower() in org_name.lower() and org_name != current_institution:
                            start = h.get("get_date", "?")
                            end = h.get("leave_date", "至今") or "至今"
                            past_institution_match = {
                                "name": org_name,
                                "time": f"{start} — {end}"
                            }
                            break # Found the most recent matching past institution
            else:
                raw_list = raw.get("raw_list_data", {})
                current_institution = raw_list.get("orgName", row['inst_id'])
        else:
            raw = json.loads(row['raw_data'])
            title = "基金从业人员"
            cert_history = raw.get("personCertHistoryList", [])
            
            if cert_history:
                active_certs = [c for c in cert_history if c.get("statusName") == "正常"]
                if active_certs:
                    current_institution = active_certs[0].get("orgName", row['inst_id'])
                    title = active_certs[0].get("certName", title)
                else:
                    current_institution = cert_history[0].get("orgName", row['inst_id'])
                    
                # Check for past institution match
                if institution:
                    for h in cert_history:
                        org_name = h.get("orgName", "")
                        if institution.lower() in org_name.lower() and org_name != current_institution:
                            start = ""
                            end = "至今"
                            if h.get("certObtainDate"):
                                try:
                                    import datetime
                                    start = datetime.datetime.fromtimestamp(h["certObtainDate"]/1000).strftime('%Y-%m-%d')
                                except:
                                    start = "?"
                            if h.get("certEndDate") and h.get("statusName") != "正常":
                                try:
                                    import datetime
                                    end = datetime.datetime.fromtimestamp(h["certEndDate"]/1000).strftime('%Y-%m-%d')
                                except:
                                    pass
                            past_institution_match = {
                                "name": org_name,
                                "time": f"{start} — {end}"
                            }
                            break
            else:
                current_institution = raw.get("orgName", row['inst_id'])
                
        # 提取 top_tags
        top_tags = []
        pref_industries_top3: List[str] = []
        avatar_url = ""
        if row['is_rsc'] == 1 and row['rsc_info']:
            try:
                rsc_info = json.loads(row['rsc_info'])
                if isinstance(rsc_info, dict):
                    avatar_url = clean_str(rsc_info.get("avatar_url"))
                try:
                    key = f"{row['source']}::{row['id']}"
                    if isinstance(rsc_info, dict):
                        relevance_tags_by_item[key] = extract_user_tags(rsc_info)
                except Exception:
                    pass
                bt = rsc_info.get('behavior_tags', {})
                for t in split_multi_values(bt.get("偏好主题")):
                    if t not in top_tags:
                        top_tags.append(t)
                for t in split_multi_values(bt.get("偏好赛道")):
                    if t not in top_tags:
                        top_tags.append(t)
                
                # 如果标签不够，补充行业
                if len(top_tags) < 2 and 'research_industries' in rsc_info:
                    ind = rsc_info['research_industries']
                    if isinstance(ind, list):
                        top_tags.extend(ind[:2-len(top_tags)])

                for k in ("shenwan_1", "shenwan_2", "shenwan_3"):
                    v = str(rsc_info.get(k) or "").strip()
                    if v and v not in pref_industries_top3:
                        pref_industries_top3.append(v)
            except:
                pass
                
        prefer_financial_title = sort_by == "latest_register"
        if not prefer_financial_title:
            rsc_inst = str(row['rsc_institution'] or "").strip()
            rsc_title = str(row['rsc_title'] or "").strip()
            if rsc_inst:
                current_institution = rsc_inst
            if rsc_title:
                title = rsc_title
        else:
            if not current_institution:
                current_institution = str(row['rsc_institution'] or "")
            if not title:
                title = str(row['rsc_title'] or "")

        items.append({
            "id": row['id'],
            "name": row['name'] or "未知",
            "institution": current_institution or "",
            "source": row['source'],
            "title": title or "",
            "avatar_url": avatar_url,
            "past_match": past_institution_match,
            "is_rsc": True if row['is_rsc'] == 1 else False,
            "updated_at": str(row['updated_at']).rsplit(':', 1)[0] if row['updated_at'] else "",
            "reg_date": str(row['reg_date']) if row['reg_date'] else "",
            "is_outdated": True if row['is_outdated'] == 1 else False,
            "top_tags": top_tags[:2],
            "pref_industries_top3": pref_industries_top3[:3],
        })
        
    conn.close()

    if sort_by == "relevance":
        scored = []
        for idx, it in enumerate(items):
            cand_tags = []
            if it.get("is_rsc"):
                try:
                    key = f"{it.get('source')}::{it.get('id')}"
                    cand_tags = relevance_tags_by_item.get(key, [])
                except Exception:
                    cand_tags = []
            score = compute_relevance_score(desired_tags_soft, cand_tags)
            reg = str(it.get("reg_date") or "")
            scored.append((score, reg, idx, it))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        items = [x[3] for x in scored[offset: offset + size]]
    
    return {
        "total": total,
        "items": items,
        "page": page,
        "size": size,
        "meta": meta
    }

@app.get("/api/rsc/experts", response_model=SearchResponse)
def search_rsc_experts(
    query: str = "",
    tags: str = "",
    aum: str = "",
    is_matched: Optional[bool] = None,
    is_outdated: Optional[bool] = None,
    adv_org_type: str = "",
    adv_cert_type: str = "",
    adv_shenwan_1: str = "",
    adv_region: str = "",
    adv_is_foreign: str = "",
    adv_org_group: str = "",
    adv_org_subtype: str = "",
    adv_office_location: str = "",
    adv_pref_theme: str = "",
    adv_pref_track: str = "",
    adv_agg_research: str = "",
    adv_office_country: str = "",
    adv_office_province: str = "",
    adv_office_city: str = "",
    adv_mobile_country: str = "",
    adv_mobile_province: str = "",
    adv_mobile_city: str = "",
    adv_active_date_start: str = "",
    adv_active_date_end: str = "",
    adv_cert_date_start: str = "",
    adv_cert_date_end: str = "",
    sort_by: str = "",
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    offset = (page - 1) * limit
    
    # Base query
    base_sql = """
        SELECT u.uid as id, u.name, u.org_name as institution, 'RSC' as source, 
               u.position as title, u.ext_data as rsc_info,
               o.aum as org_aum, o.value_score,
               m.practitioner_id, m.is_outdated
        FROM rsc_users u
        LEFT JOIN rsc_orgs o ON u.oid = o.oid
        LEFT JOIN rsc_user_mapping m ON u.uid = m.rsc_uid
    """
    
    where_clauses = []
    params = []
    
    if query:
        where_clauses.append("(u.name LIKE ? OR u.org_name LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
        
    if is_matched is not None:
        if is_matched:
            where_clauses.append("m.practitioner_id IS NOT NULL")
        else:
            where_clauses.append("m.practitioner_id IS NULL")
            
    if is_outdated is not None:
        if is_outdated:
            where_clauses.append("m.is_outdated = 1")
        else:
            where_clauses.append("(m.is_outdated = 0 OR m.is_outdated IS NULL)")
            
    # Advanced Filters
    if adv_org_type:
        vals = [v.strip() for v in adv_org_type.split(',') if v.strip()]
        if vals:
            placeholders = ','.join(['?'] * len(vals))
            where_clauses.append(f"json_extract(u.ext_data, '$.org_type') IN ({placeholders})")
            params.extend(vals)
    if adv_cert_type:
        vals = [v.strip() for v in adv_cert_type.split(',') if v.strip()]
        if vals:
            placeholders = ','.join(['?'] * len(vals))
            where_clauses.append(f"json_extract(u.ext_data, '$.cert_type') IN ({placeholders})")
            params.extend(vals)
    if adv_shenwan_1:
        vals = [v.strip() for v in adv_shenwan_1.split(',') if v.strip()]
        if vals:
            placeholders = ','.join(['?'] * len(vals))
            where_clauses.append(f"json_extract(u.ext_data, '$.shenwan_1') IN ({placeholders})")
            params.extend(vals)
    if adv_region:
        vals = [v.strip() for v in adv_region.split(',') if v.strip()]
        if vals:
            placeholders = ','.join(['?'] * len(vals))
            where_clauses.append(f"json_extract(o.ext_data, '$.region') IN ({placeholders})")
            params.extend(vals)
    if adv_is_foreign:
        vals = [v.strip() for v in adv_is_foreign.split(',') if v.strip()]
        if vals:
            placeholders = ','.join(['TRIM(?)'] * len(vals))
            where_clauses.append(f"TRIM(json_extract(o.ext_data, '$.is_foreign')) IN ({placeholders})")
            params.extend(vals)
    if adv_org_group:
        vals = [v.strip() for v in adv_org_group.split(',') if v.strip()]
        if vals:
            clauses = []
            for v in vals:
                clauses.append(f"json_extract(o.ext_data, '$.org_group') LIKE ?")
                params.append(f"%{v}%")
            where_clauses.append("(" + " OR ".join(clauses) + ")")
    if adv_org_subtype:
        vals = [v.strip() for v in adv_org_subtype.split(',') if v.strip()]
        if vals:
            clauses = []
            for v in vals:
                clauses.append(f"json_extract(o.ext_data, '$.org_subtype') LIKE ?")
                params.append(f"%{v}%")
            where_clauses.append("(" + " OR ".join(clauses) + ")")
    if adv_office_location:
        vals = [v.strip() for v in adv_office_location.split(',') if v.strip()]
        if vals:
            clauses = []
            for v in vals:
                clauses.append(f"json_extract(o.ext_data, '$.office_location') LIKE ?")
                params.append(f"%{v}%")
            where_clauses.append("(" + " OR ".join(clauses) + ")")
    if adv_pref_theme:
        vals = [v.strip() for v in adv_pref_theme.split(',') if v.strip()]
        if vals:
            clauses = []
            for v in vals:
                clauses.append(f"json_extract(u.ext_data, '$.pref_theme') LIKE ?")
                params.append(f"%{v}%")
            where_clauses.append("(" + " OR ".join(clauses) + ")")
    if adv_pref_track:
        vals = [v.strip() for v in adv_pref_track.split(',') if v.strip()]
        if vals:
            clauses = []
            for v in vals:
                clauses.append(f"json_extract(u.ext_data, '$.pref_track') LIKE ?")
                params.append(f"%{v}%")
            where_clauses.append("(" + " OR ".join(clauses) + ")")
    if adv_agg_research:
        vals = [v.strip() for v in adv_agg_research.split(',') if v.strip()]
        if vals:
            clauses = []
            for v in vals:
                clauses.append(f"json_extract(u.ext_data, '$.agg_research_industry') LIKE ?")
                params.append(f"%{v}%")
            where_clauses.append("(" + " OR ".join(clauses) + ")")
    if adv_office_country:
        vals = [v.strip() for v in adv_office_country.split(',') if v.strip()]
        if vals:
            placeholders = ','.join(['?'] * len(vals))
            where_clauses.append(f"json_extract(u.ext_data, '$.office_country') IN ({placeholders})")
            params.extend(vals)
    if adv_office_province:
        vals = [v.strip() for v in adv_office_province.split(',') if v.strip()]
        if vals:
            placeholders = ','.join(['?'] * len(vals))
            where_clauses.append(f"json_extract(u.ext_data, '$.office_province') IN ({placeholders})")
            params.extend(vals)
    if adv_office_city:
        vals = [v.strip() for v in adv_office_city.split(',') if v.strip()]
        if vals:
            placeholders = ','.join(['?'] * len(vals))
            where_clauses.append(f"json_extract(u.ext_data, '$.office_city') IN ({placeholders})")
            params.extend(vals)
    if adv_mobile_country:
        vals = [v.strip() for v in adv_mobile_country.split(',') if v.strip()]
        if vals:
            placeholders = ','.join(['?'] * len(vals))
            where_clauses.append(f"json_extract(u.ext_data, '$.mobile_country') IN ({placeholders})")
            params.extend(vals)
    if adv_mobile_province:
        vals = [v.strip() for v in adv_mobile_province.split(',') if v.strip()]
        if vals:
            placeholders = ','.join(['?'] * len(vals))
            where_clauses.append(f"json_extract(u.ext_data, '$.mobile_province') IN ({placeholders})")
            params.extend(vals)
    if adv_mobile_city:
        vals = [v.strip() for v in adv_mobile_city.split(',') if v.strip()]
        if vals:
            placeholders = ','.join(['?'] * len(vals))
            where_clauses.append(f"json_extract(u.ext_data, '$.mobile_city') IN ({placeholders})")
            params.extend(vals)

    # Date Filters
    if adv_active_date_start:
        where_clauses.append("json_extract(u.ext_data, '$.last_active_time') >= ?")
        params.append(adv_active_date_start)
    if adv_active_date_end:
        where_clauses.append("json_extract(u.ext_data, '$.last_active_time') <= ?")
        params.append(adv_active_date_end + " 23:59:59")
        
    if adv_cert_date_start:
        where_clauses.append("u.cert_time >= ?")
        params.append(adv_cert_date_start)
    if adv_cert_date_end:
        where_clauses.append("u.cert_time <= ?")
        params.append(adv_cert_date_end + " 23:59:59")
            
    # Handle tags and aum using existing memory indices
    valid_ids = None
    if tags:
        tag_list = [t.strip() for t in tags.split(',')]
        tag_ids = set()
        for t in tag_list:
            if t in tag_index:
                tag_ids.update(tag_index[t])
        valid_ids = tag_ids if valid_ids is None else valid_ids.intersection(tag_ids)
        
    if aum:
        aum_list = [a.strip() for a in aum.split(',')]
        aum_ids = set()
        for a in aum_list:
            if a in aum_index:
                aum_ids.update(aum_index[a])
        valid_ids = aum_ids if valid_ids is None else valid_ids.intersection(aum_ids)
        
    if valid_ids is not None:
        if not valid_ids:
            return {"total": 0, "items": [], "page": page, "size": limit}
            
        valid_ids_list = list(valid_ids)[:900]
        placeholders = ','.join(['?'] * len(valid_ids_list))
        where_clauses.append(f"u.uid IN ({placeholders})")
        params.extend(valid_ids_list)
        
    if where_clauses:
        base_sql += " WHERE " + " AND ".join(where_clauses)
        
    count_sql = f"SELECT COUNT(*) FROM ({base_sql})"
    cursor.execute(count_sql, params)
    total = cursor.fetchone()[0] or 0
    
    paginated_sql = base_sql + " LIMIT ? OFFSET ?"
    cursor.execute(paginated_sql, params + [limit, offset])
    rows = cursor.fetchall()
    
    items = []
    for row in rows:
        top_tags = []
        avatar_url = ""
        if row['rsc_info']:
            try:
                info = json.loads(row['rsc_info'])
                if isinstance(info, dict):
                    avatar_url = clean_str(info.get("avatar_url"))
                bt = info.get('behavior_tags', {})
                for t in split_multi_values(bt.get("偏好主题")):
                    if t not in top_tags:
                        top_tags.append(t)
                for t in split_multi_values(bt.get("偏好赛道")):
                    if t not in top_tags:
                        top_tags.append(t)
                if len(top_tags) < 2 and 'research_industries' in info:
                    ind = info['research_industries']
                    if isinstance(ind, list): top_tags.extend(ind[:2-len(top_tags)])
            except:
                pass
                
        items.append({
            "id": row['id'],
            "name": row['name'] or "未知",
            "institution": row['institution'] or "",
            "source": row['source'],
            "title": row['title'] or "",
            "avatar_url": avatar_url,
            "is_rsc": True,
            "is_outdated": True if row['is_outdated'] == 1 else False,
            "top_tags": top_tags[:2],
            # Add past_match, updated_at, reg_date to match SearchResultItem model
            "past_match": None,
            "updated_at": "",
            "reg_date": ""
        })
        
    conn.close()
    return {"total": total, "items": items, "page": page, "size": limit}

def clean_str(val):
    if not val:
        return ""
    s = str(val).strip()
    if s in ("-", "--", "---", "无", "暂无", "未知", "未披露", "null", "None"):
        return ""
    return s

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"error": str(exc), "traceback": traceback.format_exc()})

@app.get("/api/talents/{source}/{talent_id}")
def get_talent_detail(source: str, talent_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if source.upper() == 'RSC':
        cursor.execute('''
            SELECT u.*, o.value_score, o.influence_score, o.aum, o.short_name as org_short, o.ext_data as org_ext_data
            FROM rsc_users u
            LEFT JOIN rsc_orgs o ON u.oid = o.oid
            WHERE u.uid = ?
        ''', (talent_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Talent not found in RSC")
            
        raw_data = {}
        if row and "ext_data" in row.keys() and row["ext_data"]:
            try:
                parsed = json.loads(row["ext_data"])
                if isinstance(parsed, dict):
                    raw_data = parsed
            except:
                pass
                
        org_ext = {}
        if row and "org_ext_data" in row.keys() and row["org_ext_data"]:
            try:
                parsed = json.loads(row["org_ext_data"])
                if isinstance(parsed, dict):
                    org_ext = parsed
            except:
                pass
                
        user_ext = raw_data
        
        behavior_tags = user_ext.get("behavior_tags", {}) if isinstance(user_ext, dict) else {}
        if not isinstance(behavior_tags, dict):
            behavior_tags = {}
        research_industries = user_ext.get("research_industries", []) if isinstance(user_ext, dict) else []
        if isinstance(research_industries, str):
            research_industries = [i.strip() for i in research_industries.split(",") if i.strip()]
            
        cert_no = ""
        if "cert_no" in row.keys():
            cert_no = row["cert_no"]
        elif "cert_type" in row.keys():
            cert_no = row["cert_type"]
            
        cert_time = ""
        if "cert_time" in row.keys():
            cert_time = row["cert_time"]
            
        row_dict = dict(row)
        profile = {
            "id": clean_str(row_dict.get('uid')),
            "name": clean_str(row_dict.get('name')),
            "institution": clean_str(row_dict.get('org_name') or row_dict.get('org_short')),
            "source": "RSC",
            "gender": clean_str(row_dict.get('gender')),
            "education": clean_str(row_dict.get('highest_edu')),
            "cert_no": clean_str(cert_no),
            "avatar_url": clean_str(user_ext.get("avatar_url")),
            "origin_url": "",
            "rsc_info": {
                "uid": clean_str(row_dict.get('uid')),
                "org": clean_str(row_dict.get('org_name')),
                "cert_time": clean_str(cert_time).rsplit(':', 1)[0] if cert_time else "",
                "is_outdated": False,
                "cert_org": clean_str(row_dict.get('org_full_name') or row_dict.get('org_name')),
                "title": clean_str(row_dict.get('position')),
                "department": clean_str(row_dict.get('department')),
                "intro": clean_str(user_ext.get("personal_intro") or row_dict.get("intro")),
                "highest_edu": clean_str(row_dict.get("highest_edu")),
                "university": clean_str(row_dict.get("university")),
                "behavior_tags": behavior_tags,
                "behavior_summary": clean_str(user_ext.get("behavior_summary") or user_ext.get("行为汇总") or behavior_tags.get("行为汇总")),
                "research_industries": research_industries,
                "org_value_score": row_dict.get("value_score") if row_dict.get("value_score") is not None else 0,
                "org_influence_score": row_dict.get("influence_score") if row_dict.get("influence_score") is not None else 0,
                "org_aum": clean_str(row_dict.get("aum")),
                
                # New Advanced Fields
                "register_time": clean_str(user_ext.get("register_time")).rsplit(':', 1)[0] if user_ext.get("register_time") else "",
                "last_active_time": clean_str(user_ext.get("last_active_time")).rsplit(':', 1)[0] if user_ext.get("last_active_time") else "",
                "org_type": clean_str(user_ext.get("org_type")),
                "cert_type": clean_str(user_ext.get("cert_type")),
                "shenwan_1": clean_str(user_ext.get("shenwan_1")),
                "shenwan_1_score": clean_str(user_ext.get("shenwan_1_score")),
                "shenwan_2": clean_str(user_ext.get("shenwan_2")),
                "shenwan_2_score": clean_str(user_ext.get("shenwan_2_score")),
                "shenwan_3": clean_str(user_ext.get("shenwan_3")),
                "shenwan_3_score": clean_str(user_ext.get("shenwan_3_score")),
                "pref_theme": clean_str(user_ext.get("pref_theme")),
                "pref_track": clean_str(user_ext.get("pref_track")),
                "value_tags": user_ext.get("value_tags", []) if isinstance(user_ext.get("value_tags"), list) else [],
                "agg_research_industry": clean_str(user_ext.get("agg_research_industry")),
                "office_address": clean_str(user_ext.get("office_address")),
                "office_country": clean_str(user_ext.get("office_country")),
                "office_province": clean_str(user_ext.get("office_province")),
                "office_city": clean_str(user_ext.get("office_city")),
                "mobile_country": clean_str(user_ext.get("mobile_country")),
                "mobile_province": clean_str(user_ext.get("mobile_province")),
                "mobile_city": clean_str(user_ext.get("mobile_city")),
                "recent_follow_companies": split_multi_values(user_ext.get("recent_follow_companies")),
                
                # New Org Fields
                "org_region": clean_str(org_ext.get("region")),
                "org_group": clean_str(org_ext.get("org_group")),
                "org_subtype": clean_str(org_ext.get("org_subtype")),
                "org_office_location": clean_str(org_ext.get("office_location")),
                "org_is_foreign": clean_str(org_ext.get("is_foreign")),
                "org_tags": org_ext.get("org_tags", []) if isinstance(org_ext.get("org_tags"), list) else [],
                "org_logo": clean_str(org_ext.get("logo")),
                "org_amac_website": clean_str(org_ext.get("amac_website")),
                "org_website": clean_str(org_ext.get("website")),
                "org_email": clean_str(org_ext.get("email")),
                "org_one_sentence_pos": clean_str(org_ext.get("one_sentence_pos")),
                "org_core_figures": clean_str(org_ext.get("core_figures")),
                "org_value_score_desc": clean_str(org_ext.get("value_score_desc")),
                "org_influence_score_desc": clean_str(
                    org_ext.get("influence_score_desc")
                    or org_ext.get("influence_score_reason")
                    or org_ext.get("influence_desc")
                    or org_ext.get("影响力评分理由")
                    or org_ext.get("✅影响力评分描述")
                ),
                "org_invest_pos": clean_str(org_ext.get("invest_pos")),
                "org_invest_style": clean_str(org_ext.get("invest_style")),
                "org_intro": clean_str(org_ext.get("org_intro")),
                "org_rsc_profile_url": clean_str(org_ext.get("rsc_profile_url"))
            },
            "timeline": []
        }
        
        try:
            if profile.get("timeline"):
                profile["timeline"].sort(key=lambda x: str(x.get("start_date") or ""), reverse=True)
        except Exception as e:
            print("Warning: Failed to sort timeline:", e)
            
        # Add basic timeline if available from raw_data
        if isinstance(raw_data, dict) and "timeline" in raw_data and isinstance(raw_data["timeline"], list):
            for h in raw_data["timeline"]:
                profile["timeline"].append({
                    "start_date": clean_str(h.get("start_date")),
                    "end_date": clean_str(h.get("end_date")) or "至今",
                    "institution": clean_str(h.get("institution")),
                    "role": clean_str(h.get("role")),
                    "status": clean_str(h.get("status"))
                })
        
        try:
            if profile.get("timeline"):
                profile["timeline"].sort(key=lambda x: str(x.get("start_date") or ""), reverse=True)
        except Exception as e:
            print("Warning: Failed to sort timeline:", e)
            
        conn.close()
        return profile

    if source.upper() == 'SAC':
        cursor.execute("SELECT * FROM sac_practitioners WHERE practitioner_id = ?", (talent_id,))
    else:
        cursor.execute("SELECT * FROM amac_practitioners WHERE practitioner_id = ?", (talent_id,))
        
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Talent not found")
        
    # Check for RSC mapping
    cursor.execute("SELECT * FROM rsc_user_mapping WHERE practitioner_id = ? AND source_type = ?", (talent_id, source.upper()))
    rsc_mapping_row = cursor.fetchone()
    
    raw_data = {}
    if row['raw_data']:
        try:
            parsed = json.loads(row['raw_data'])
            if isinstance(parsed, dict):
                raw_data = parsed
        except:
            pass
    
    # 尝试解析头像
    avatar_url = ""
    if source.upper() == 'SAC':
        photo_path = raw_data.get("photoPath")
        if photo_path:
            # 拼接 SAC 头像链接，SAC使用此接口下载图片，需要传入 base64 加密的路径
            avatar_url = f"https://gs.sac.net.cn/publicity/v2/regFile/downLoadUserPhoto?photoPath={photo_path}"
    else:
        # AMAC 的人员照片是 base64 返回，通常为空
        photo_b64 = raw_data.get("personPhotoBase64")
        if photo_b64:
            avatar_url = f"data:image/jpeg;base64,{photo_b64}"
            
    # 获取原始链接
    origin_url = ""
    if source.upper() == 'SAC':
        person_id = ""
        if isinstance(raw_data, dict):
            person_id = raw_data.get('RPI_ID') or raw_data.get('pti_id') or raw_data.get('raw_list_data', {}).get('uuid') or row['practitioner_id']
            if raw_data.get('pti_id'):
                origin_url = f"https://exam.sac.net.cn/pages/registration/sac-publicity/finish-publicity.html?ptiID={person_id}"
            elif raw_data.get('uuid'):
                origin_url = f"https://gs.sac.net.cn/pages/registration/new-sac-finish-person.html?uuid={raw_data.get('uuid')}"
            else:
                origin_url = f"https://gs.sac.net.cn/pages/registration/new-sac-finish-person.html?uuid={person_id}"
        else:
            person_id = row['practitioner_id']
            origin_url = f"https://gs.sac.net.cn/pages/registration/new-sac-finish-person.html?uuid={person_id}"
    else:
        # AMAC 的 accountId 可以用来直接拼接
        account_id = ""
        if isinstance(raw_data, dict):
            account_id = raw_data.get('accountId', row['practitioner_id'])
        else:
            account_id = row['practitioner_id']
        origin_url = f"https://gs.amac.org.cn/amac-infodisc/res/pof/person/personDetail.html?accountId={account_id}"
            
    profile = {
        "id": clean_str(row['practitioner_id']),
        "name": clean_str(row['name']),
        "institution": "",
        "source": source.upper(),
        "gender": clean_str(raw_data.get("gender") or raw_data.get("sex")) if isinstance(raw_data, dict) else "",
        "education": clean_str(raw_data.get("edu") or raw_data.get("educationName")) if isinstance(raw_data, dict) else "",
        "cert_no": clean_str(raw_data.get("certifNo") or raw_data.get("certCode")) if isinstance(raw_data, dict) else "",
        "avatar_url": avatar_url,
        "origin_url": origin_url,
        "rsc_info": None,
        "timeline": []
    }
    
    if source.upper() == 'SAC':
        if isinstance(raw_data, dict) and raw_data.get('raw_list_data') and isinstance(raw_data.get('raw_list_data'), dict):
            profile["institution"] = clean_str(raw_data['raw_list_data'].get('orgName') or row['institution_id'])
    
    if rsc_mapping_row:
        rsc_uid = ""
        if "rsc_uid" in rsc_mapping_row.keys():
            rsc_uid = rsc_mapping_row["rsc_uid"]
        
        # Get rsc_cert_time safely handling sqlite3.Row
        rsc_cert_time = ""
        if "rsc_cert_time" in rsc_mapping_row.keys():
            rsc_cert_time = rsc_mapping_row["rsc_cert_time"]
            
        rsc_org = ""
        if "rsc_org" in rsc_mapping_row.keys():
            rsc_org = rsc_mapping_row["rsc_org"]
            
        is_outdated = False
        if "is_outdated" in rsc_mapping_row.keys():
            is_outdated = bool(rsc_mapping_row["is_outdated"])
            
        profile["rsc_info"] = {
            "uid": clean_str(rsc_uid),
            "org": clean_str(rsc_org),
            "cert_time": clean_str(rsc_cert_time).rsplit(':', 1)[0] if rsc_cert_time else "",
            "is_outdated": is_outdated
        }
        
        # Fetch extended data
        cursor.execute('''
            SELECT u.intro, u.highest_edu, u.university, u.ext_data as user_ext_data,
                   u.org_name, u.position, u.department,
                   o.value_score, o.influence_score, o.aum, o.ext_data as org_ext_data
            FROM rsc_users u
            LEFT JOIN rsc_orgs o ON u.oid = o.oid
            WHERE u.uid = ?
        ''', (rsc_uid,))
        rsc_user_row = cursor.fetchone()
        
        if rsc_user_row:
            rsc_user_dict = dict(rsc_user_row)
            user_ext = {}
            if rsc_user_dict.get("user_ext_data"):
                try:
                    parsed = json.loads(rsc_user_dict["user_ext_data"])
                    if isinstance(parsed, dict):
                        user_ext = parsed
                except:
                    pass

            org_ext = {}
            if rsc_user_dict.get("org_ext_data"):
                try:
                    parsed = json.loads(rsc_user_dict["org_ext_data"])
                    if isinstance(parsed, dict):
                        org_ext = parsed
                except:
                    pass
            
            behavior_tags = user_ext.get("behavior_tags", {}) if isinstance(user_ext, dict) else {}
            if not isinstance(behavior_tags, dict):
                behavior_tags = {}
            research_industries = user_ext.get("research_industries", []) if isinstance(user_ext, dict) else []
            if isinstance(research_industries, str):
                research_industries = [i.strip() for i in research_industries.split(",") if i.strip()]
            
            profile["rsc_info"].update({
                "intro": clean_str(user_ext.get("personal_intro") or rsc_user_dict.get("intro")),
                "highest_edu": clean_str(rsc_user_dict.get("highest_edu")),
                "university": clean_str(rsc_user_dict.get("university")),
                "behavior_tags": behavior_tags,
                "behavior_summary": clean_str(user_ext.get("behavior_summary") or user_ext.get("行为汇总") or behavior_tags.get("行为汇总")),
                "research_industries": research_industries,
                "org_value_score": rsc_user_dict.get("value_score") if rsc_user_dict.get("value_score") is not None else 0,
                "org_influence_score": rsc_user_dict.get("influence_score") if rsc_user_dict.get("influence_score") is not None else 0,
                "org_aum": clean_str(rsc_user_dict.get("aum")),
                "org_value_score_desc": clean_str(org_ext.get("value_score_desc")),
                "org_influence_score_desc": clean_str(
                    org_ext.get("influence_score_desc")
                    or org_ext.get("influence_score_reason")
                    or org_ext.get("influence_desc")
                    or org_ext.get("影响力评分理由")
                    or org_ext.get("✅影响力评分描述")
                ),
                "cert_org": clean_str(rsc_user_dict.get("org_full_name") or rsc_user_dict.get("org_name")),
                "title": clean_str(rsc_user_dict.get("position")),
                "department": clean_str(rsc_user_dict.get("department")),
                
                # New Advanced Fields
                "register_time": clean_str(user_ext.get("register_time")).rsplit(':', 1)[0] if user_ext.get("register_time") else "",
                "last_active_time": clean_str(user_ext.get("last_active_time")).rsplit(':', 1)[0] if user_ext.get("last_active_time") else "",
                "org_type": clean_str(user_ext.get("org_type")),
                "cert_type": clean_str(user_ext.get("cert_type")),
                "shenwan_1": clean_str(user_ext.get("shenwan_1")),
                "shenwan_1_score": clean_str(user_ext.get("shenwan_1_score")),
                "shenwan_2": clean_str(user_ext.get("shenwan_2")),
                "shenwan_2_score": clean_str(user_ext.get("shenwan_2_score")),
                "shenwan_3": clean_str(user_ext.get("shenwan_3")),
                "shenwan_3_score": clean_str(user_ext.get("shenwan_3_score")),
                "pref_theme": clean_str(user_ext.get("pref_theme")),
                "pref_track": clean_str(user_ext.get("pref_track")),
                "value_tags": user_ext.get("value_tags", []) if isinstance(user_ext.get("value_tags"), list) else [],
                "agg_research_industry": clean_str(user_ext.get("agg_research_industry")),
                "office_address": clean_str(user_ext.get("office_address")),
                "office_country": clean_str(user_ext.get("office_country")),
                "office_province": clean_str(user_ext.get("office_province")),
                "office_city": clean_str(user_ext.get("office_city")),
                "mobile_country": clean_str(user_ext.get("mobile_country")),
                "mobile_province": clean_str(user_ext.get("mobile_province")),
                "mobile_city": clean_str(user_ext.get("mobile_city")),
                "recent_follow_companies": split_multi_values(user_ext.get("recent_follow_companies"))
            })
    
    if raw_data is None:
        raw_data = {}

    if source.upper() == 'SAC':
        history = []
        if isinstance(raw_data, dict):
            history = raw_data.get("regHistory", [])
        
        if history:
            # 取最后一条（最新的一条）作为当前机构
            profile["institution"] = clean_str(history[-1].get("org_name") or row['institution_id'])
            for h in history:
                profile["timeline"].append({
                    "start_date": clean_str(h.get("get_date")),
                    "end_date": clean_str(h.get("leave_date")) or "至今",
                    "institution": clean_str(h.get("org_name")),
                    "role": clean_str(h.get("reg_type")),
                    "status": clean_str(h.get("status"))
                })
        elif not profile["institution"]:
            profile["institution"] = clean_str((raw_data.get("raw_list_data") or {}).get("orgName") or row['institution_id']) if isinstance(raw_data, dict) else clean_str(row['institution_id'])
    elif source.upper() == 'AMAC':
        history = []
        if isinstance(raw_data, dict):
            history = raw_data.get("personCertHistoryList", [])
            
        if history:
            active_certs = [c for c in history if c.get("statusName") == "正常"]
            if active_certs:
                profile["institution"] = clean_str(active_certs[0].get("orgName") or row['institution_id'])
            else:
                profile["institution"] = clean_str(history[0].get("orgName") or row['institution_id'])

            for h in history:
                start_date = ""
                end_date = "至今"
                if h.get("certObtainDate"):
                    try:
                        import datetime
                        start_date = datetime.datetime.fromtimestamp(h["certObtainDate"]/1000).strftime('%Y-%m-%d')
                    except:
                        pass
                if h.get("certEndDate") and h.get("statusName") != "正常":
                    try:
                        import datetime
                        end_date = datetime.datetime.fromtimestamp(h["certEndDate"]/1000).strftime('%Y-%m-%d')
                    except:
                        pass
                    
                profile["timeline"].append({
                    "start_date": start_date,
                    "end_date": end_date,
                    "institution": clean_str(h.get("orgName")),
                    "role": clean_str(h.get("certName")),
                    "status": clean_str(h.get("statusName"))
                })
        else:
            profile["institution"] = clean_str(raw_data.get("orgName") or row['institution_id']) if isinstance(raw_data, dict) else clean_str(row['institution_id'])
            
    else:
        # Provide empty institution and default timeline for RSC
        profile["institution"] = ""
        
        # Add basic timeline if available from raw_data
        if isinstance(raw_data, dict) and "timeline" in raw_data and isinstance(raw_data["timeline"], list):
            for h in raw_data["timeline"]:
                profile["timeline"].append({
                    "start_date": clean_str(h.get("start_date")),
                    "end_date": clean_str(h.get("end_date")) or "至今",
                    "institution": clean_str(h.get("institution")),
                    "role": clean_str(h.get("role")),
                    "status": clean_str(h.get("status"))
                })
            
    try:
        if profile.get("timeline"):
            profile["timeline"].sort(key=lambda x: str(x.get("start_date") or ""), reverse=True)
    except Exception as e:
        print("Warning: Failed to sort timeline:", e)
        
    conn.close()
    return profile

# --- Admin Dashboard Endpoints ---

@app.get("/api/admin/data/quality")
def get_data_quality():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total counts
    cursor.execute("SELECT COUNT(*) FROM sac_practitioners")
    sac_total = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM amac_practitioners")
    amac_total = cursor.fetchone()[0] or 0
    
    # 2. Missing crucial fields
    cursor.execute("SELECT COUNT(*) FROM sac_practitioners WHERE json_extract(raw_data, '$.regDate') IS NULL")
    sac_missing_date = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM amac_practitioners WHERE json_extract(raw_data, '$.certObtainDate') IS NULL")
    amac_missing_date = cursor.fetchone()[0] or 0
    
    # 3. Added today
    cursor.execute("SELECT COUNT(*) FROM sac_practitioners WHERE date(created_at) = date('now', 'localtime')")
    sac_today = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM amac_practitioners WHERE date(created_at) = date('now', 'localtime')")
    amac_today = cursor.fetchone()[0] or 0
    
    # 4. RSC Stats
    cursor.execute("SELECT COUNT(*) FROM rsc_users")
    rsc_total = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(DISTINCT rsc_uid) FROM rsc_user_mapping")
    rsc_matched = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM rsc_user_mapping WHERE is_outdated = 1")
    rsc_outdated = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        "sac": {
            "total": sac_total,
            "missing_date": sac_missing_date,
            "completeness_pct": round((sac_total - sac_missing_date) / sac_total * 100, 2) if sac_total > 0 else 0,
            "today_new": sac_today
        },
        "amac": {
            "total": amac_total,
            "missing_date": amac_missing_date,
            "completeness_pct": round((amac_total - amac_missing_date) / amac_total * 100, 2) if amac_total > 0 else 0,
            "today_new": amac_today
        },
        "rsc": {
            "total": rsc_total,
            "matched": rsc_matched,
            "match_rate_pct": round(rsc_matched / rsc_total * 100, 2) if rsc_total > 0 else 0,
            "outdated": rsc_outdated
        }
    }

@app.get("/api/admin/scraper/status")
def get_scraper_status():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM progress_tracking WHERE status = 'in_progress'")
    in_progress = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM progress_tracking WHERE status = 'completed'")
    completed = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT task_name, status, updated_at FROM progress_tracking WHERE status = 'in_progress' ORDER BY updated_at DESC LIMIT 10")
    active_tasks = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "in_progress": in_progress,
        "completed": completed,
        "active_tasks": active_tasks
    }

@app.get("/api/admin/scraper/logs")
def get_scraper_logs(type: str = Query("monitor", regex="^(monitor|sac|amac)$")):
    log_file = f"../financial_scraper/{type}.log"
    if type == "monitor":
        log_file = "../financial_scraper/monitor.log"
    elif type == "sac":
        log_file = "../financial_scraper/sac_scraper.log"
    elif type == "amac":
        log_file = "../financial_scraper/amac_scraper.log"
        
    if not os.path.exists(log_file):
        return {"lines": ["Log file not found."]}
        
    try:
        # Read last 100 lines
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return {"lines": [line.strip() for line in lines[-100:]]}
    except Exception as e:
        return {"lines": [f"Error reading log: {str(e)}"]}
