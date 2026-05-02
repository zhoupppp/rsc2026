# V3 Dual-Engine Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a dual-engine search system separating the broad market talent database (SAC/AMAC) and the RSC certified expert database into two distinct search experiences.

**Architecture:** 
- Backend: Create a new `/api/rsc/experts` endpoint in FastAPI that queries `rsc_users` and `rsc_orgs` directly, supporting advanced JSON filtering (industry, tags, AUM).
- Frontend: Introduce a Tab layout on the Next.js homepage to switch between "Broad Market" (Engine A) and "RSC Experts" (Engine B), each maintaining distinct filter states and list rendering logic.

**Tech Stack:** FastAPI, SQLite (WAL), Next.js, React, TailwindCSS

---

### Task 1: Backend - Implement `/api/rsc/experts` endpoint

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add the new endpoint definition and basic query**
```python
@app.get("/api/rsc/experts")
def search_rsc_experts(
    query: str = "",
    tags: str = "",
    aum: str = "",
    is_matched: Optional[bool] = None,
    is_outdated: Optional[bool] = None,
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
            
    # Handle tags and aum using existing memory indices
    valid_ids = None
    if tags:
        tag_list = [t.strip() for t in tags.split(',')]
        tag_ids = set()
        for t in tag_list:
            if t in tag_index:
                # tag_index stores "{source}_{p_id}", we need to map back to rsc_uid, 
                # but wait, tag_index is built from rsc_user_mapping. 
                # For pure RSC users not mapped, they aren't in tag_index.
                pass # We will fix this in the next step
```

- [ ] **Step 2: Refactor memory indices to support pure RSC users**
Modify `build_memory_indices` in `backend/main.py` to index `rsc_users` directly instead of `rsc_user_mapping`.
```python
def build_memory_indices(cursor):
    global tag_index, aum_index
    tag_index.clear()
    aum_index.clear()
    
    try:
        cursor.execute("""
            SELECT u.uid, u.ext_data, o.aum 
            FROM rsc_users u
            LEFT JOIN rsc_orgs o ON u.oid = o.oid
        """)
        rows = cursor.fetchall()
        
        for row in rows:
            uid = row[0]
            rsc_info_str = row[1]
            aum_val = row[2]
            
            if rsc_info_str:
                try:
                    info = json.loads(rsc_info_str)
                    tags = []
                    if 'behavior_tags' in info:
                        bt = info['behavior_tags']
                        if '偏好主题' in bt: tags.append(bt['偏好主题'])
                        if '偏好赛道' in bt: tags.extend(bt['偏好赛道'].split(','))
                    if 'research_industries' in info and isinstance(info['research_industries'], list):
                        tags.extend(info['research_industries'])
                        
                    for tag in tags:
                        if tag:
                            tag_index[tag.strip()].add(uid)
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
    except sqlite3.OperationalError as e:
        print("Warning: Skipping memory indices.", e)
```

- [ ] **Step 3: Complete the `/api/rsc/experts` endpoint logic**
```python
    # Inside search_rsc_experts, after where_clauses setup
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
            
        placeholders = ','.join(['?'] * len(valid_ids))
        where_clauses.append(f"u.uid IN ({placeholders})")
        params.extend(list(valid_ids))
        
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
        if row['rsc_info']:
            try:
                info = json.loads(row['rsc_info'])
                bt = info.get('behavior_tags', {})
                if '偏好主题' in bt: top_tags.append(bt['偏好主题'])
                if '偏好赛道' in bt: top_tags.extend(bt['偏好赛道'].split(',')[:2])
                if len(top_tags) < 2 and 'research_industries' in info:
                    ind = info['research_industries']
                    if isinstance(ind, list): top_tags.extend(ind[:2-len(top_tags)])
            except:
                pass
                
        items.append({
            "id": row['id'],
            "name": row['name'],
            "institution": row['institution'],
            "source": row['source'],
            "title": row['title'],
            "avatar_url": "",
            "is_rsc": True,
            "is_outdated": True if row['is_outdated'] == 1 else False,
            "top_tags": top_tags[:2],
            "org_aum": row['org_aum']
        })
        
    conn.close()
    return {"total": total, "items": items, "page": page, "size": limit}
```

- [ ] **Step 4: Update `/api/talents/search` memory indices usage**
Modify `search_talents` in `backend/main.py` to use the new `uid` based indices by joining `rsc_user_mapping` to find `practitioner_id` for Engine A.

### Task 2: Frontend - Refactor Home Page to Dual-Tab Layout

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Introduce Engine State**
```typescript
const [activeEngine, setActiveEngine] = useState<'market' | 'rsc'>('market');
```

- [ ] **Step 2: Create Tab UI**
```tsx
<div className="flex space-x-4 border-b border-gray-800 mb-6">
  <button 
    className={`pb-2 px-4 ${activeEngine === 'market' ? 'border-b-2 border-[#C8A97E] text-[#C8A97E]' : 'text-gray-400'}`}
    onClick={() => setActiveEngine('market')}
  >
    全市场金融人才
  </button>
  <button 
    className={`pb-2 px-4 ${activeEngine === 'rsc' ? 'border-b-2 border-[#C8A97E] text-[#C8A97E]' : 'text-gray-400'}`}
    onClick={() => setActiveEngine('rsc')}
  >
    RSC 认证专家智库
  </button>
</div>
```

- [ ] **Step 3: Conditional Fetching Logic**
Update SWR or `useEffect` fetch logic to hit `/api/talents/search` when `activeEngine === 'market'`, and `/api/rsc/experts` when `activeEngine === 'rsc'`.

### Task 3: Frontend - Build RSC Expert FilterBar and List Integration

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Separate Filter States**
Create separate filter states for RSC Engine:
```typescript
const [rscFilters, setRscFilters] = useState({ tags: [], aum: [], is_matched: null, is_outdated: null });
```

- [ ] **Step 2: Render Distinct FilterBars**
```tsx
{activeEngine === 'market' ? (
  <MarketFilterBar filters={marketFilters} onChange={setMarketFilters} />
) : (
  <RSCFilterBar filters={rscFilters} onChange={setRscFilters} />
)}
```

- [ ] **Step 3: Render Lists**
Ensure the list item component gracefully handles the unified `items` array returned by either endpoint.
