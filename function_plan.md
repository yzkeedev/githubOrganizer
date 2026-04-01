# Enhancement Plan - GitHub Organizer

## Problem Statement

1. **Repeating ideas** - daily concepts drift back to the same shapes and audiences
2. **No cross-date collection** - there is no fast way to browse all ideas across report history
3. **Weak fallback logic** - deterministic fallback output collapses variety when the LLM path is unavailable

---

## Enhancement 1: Fresh & Creative Ideas

### Root Causes of Repetition
- The prompt used nearly the same trend and repo context every day
- Temperature was low enough to produce predictable structures
- No semantic memory of recent ideas existed before publishing
- Fallback ideas were hard-coded blueprints instead of generated from live context

### Restructured Generation Logic

#### A. Creative Forcing Layer
```python
payload = {
    "temperature": 0.78,
    "system": OPPORTUNITY_SYSTEM_PROMPT,
    "messages": [{"role": "user", "content": build_llm_prompt(...)}],
}
```

- Expand exploration space without making the output chaotic
- Ask for six candidates, then filter to the best four fresh ideas
- Push the model toward unexpected repo pairings and underserved operators

#### B. Daily Angle System
```python
generation_context = {
    "angle": choose_creative_angle(report_date, trends, repos, recent_ideas),
    "surprise_trends": pick_surprise_trends(trends, report_date),
    "repo_combos": build_repo_combo_candidates(repos, report_date),
    "recent_ideas": load_recent_idea_snapshots(reports_dir),
}
```

- Each date receives a stable creative angle derived from date, trends, repos, and history
- The angle contributes target audiences, product formats, and a directive
- The prompt now asks for contrarian or unexpected ideas instead of obvious wrappers

#### C. Reject-Similar Ideas Before Publishing
```python
ideas = select_fresh_ideas(
    idea_candidates,
    repo_lookup,
    repo_shortlist,
    trend_titles,
    trends,
    generation_context["recent_ideas"],
    limit=4,
)
```

- Compare semantic profiles built from category focus, audience, workflow shape, repo stack, and durable text tokens
- Reject close matches against recent days before the final list is chosen
- Allow only the freshest four ideas to pass into enrichment and publishing

#### D. Cross-Category Repo Combos
- Build category-pair candidates from the starred repo shortlist
- Prefer distant category combinations over same-category stacking
- Feed those pairings into both the LLM prompt and deterministic fallback generation

#### E. Surprise Trend Injection
- Promote lower-ranked trends from the lower portion of the feed
- Require the daily set to touch non-obvious signals, not just the most popular headlines
- Keep the surprise selection deterministic for the same date so reruns stay stable

#### F. Dynamic Fallback Ideas
- Replace static fallback blueprints with generated idea shells from repo pairs, surprise trends, and the daily angle
- Keep fallback output creative even when the LLM path fails
- Preserve automation instead of silently degrading into repeated templates

---

## Enhancement 2: All-Projects Collection View

### Current State
- `docs/data/index.json` only summarized reports at the day level
- History showed dates, not all individual ideas
- Users could not search or sort across the full opportunity archive

### Implemented Collection Data Structure
```python
{
  "generated_at": "2026-04-01T...",
  "latest_date": "2026-04-01",
  "all_ideas": [
    {
      "id": "sha256(date::position::name)",
      "date": "2026-04-01",
      "report_path": "data/reports/2026-04-01.json",
      "name": "Idea Name",
      "summary": "...",
      "founder_score": 72,
      "revenue_score": 65,
      "opportunity_score": 70,
      "trend_repo_match_score": 68,
      "category_focus": ["SEO & Marketing"],
      "trends": ["trend1", "trend2"],
      "repos": ["owner/repo1", "owner/repo2"],
      "build_decision": {"label": "Build now", "tone": "good"},
      "confidence": "high",
      "semantic_signature": "c:cat:seo-marketing | a:marketing | w:workflow,brief",
      "recurrence_group_id": "ab12cd34ef56",
      "first_seen": "2026-03-28",
      "last_seen": "2026-04-01",
      "is_latest": true,
      "is_recurring": false,
      "appearance_count": 1,
      "exact_appearance_count": 1
    }
  ],
  "stats": {
    "total_ideas": 120,
    "total_dates": 30,
    "avg_founder_score": 58.4,
    "top_categories": [...],
    "top_trends": [...],
    "ideas_by_date": {...},
    "recurring_ideas": 7,
    "exact_recurring_ideas": 3
  }
}
```

### Collection Dashboard Features
1. **Side menu titles** keep the archive always visible without adding a second full-width content band
2. **Middle detail pane** shows the selected collection group's latest idea, lifecycle state, and report history
3. **Search** works across names, summaries, trends, categories, and repos
4. **Filter by date** narrows the collection to a specific report window
5. **Reuse category filter** so collection and daily view stay aligned
6. **Sort** by momentum, latest, founder score, revenue score, or name
7. **Open day** jumps directly from a selected collection group to the full daily report
8. **Lifecycle window** shows when a clustered idea first appeared and when it last reappeared

---

## Enhancement 3: Idea Lifecycle Tracking

### Current Tracking Level
- Build a semantic signature from category focus, inferred audience, workflow family, repo stack, and durable summary tokens
- Cluster ideas across saved reports when the semantic similarity score crosses a stable threshold
- Mark items as latest, fresh, or recurring based on semantic group size instead of exact-name reuse

### Implemented Lifecycle Grouping
```python
{
  "group_id": "semantic-cluster-hash",
  "first_seen": "2026-03-28",
  "last_seen": "2026-04-01",
  "appearance_count": 3,
  "semantic_signature": "...",
  "label": "Latest strongest idea name in the cluster",
  "momentum_score": 74,
  "momentum_label": "Accelerating",
  "score_history": [
    {"date": "2026-03-28", "founder_score": 62, "revenue_score": 59, "opportunity_score": 61},
    {"date": "2026-04-01", "founder_score": 76, "revenue_score": 70, "opportunity_score": 79}
  ]
}
```

- The grouping logic now catches “same idea, different wording” when the buyer, workflow, and stack stay materially the same
- Exact-name counts are still kept as a lower-level metric for auditability
- Lifecycle momentum now captures whether the cluster is strengthening, steady, or cooling based on score movement plus repeat appearances

---

## Enhancement 4: Repo Connection Graph

### Future Extension
```python
repo_connections = {
  "owner/repo-name": {
    "appears_in": ["idea1", "idea2"],
    "times_used": 5,
    "last_used": "2026-04-01",
    "connections": ["other-repo-1", "other-repo-2"]
  }
}
```

- Collection data now includes the raw idea-to-repo links needed for this step
- A graph layer can be added after the collection model proves stable

---

## Execution Order

### Phase 1: Generation Engine
1. Raise LLM temperature and expand prompt diversity
2. Build generation context from history, trends, and repo pairings
3. Filter repeated concepts before enrichment
4. Generate dynamic fallback ideas instead of static templates

### Phase 2: Collection Surface
5. Aggregate all reports into `docs/data/collection.json`
6. Move the collection into a left-side title menu with one-click selection
7. Show the selected collection content in the middle panel instead of another archive card grid
8. Add momentum-first sorting, search, date filtering, and open-day navigation

### Phase 3: Lifecycle
9. Improve recurring detection from exact-name to semantic clustering
10. Persist lifecycle momentum scoring for each semantic group
11. Add semantic group browsing cues in the dashboard
12. Add richer cross-date trend and repo linkage views
13. Optionally add repo connection visualization

---

## Files to Modify

| File | Action | Description |
|-------|--------|-------------|
| `generate_opportunities.py` | Modify | Add creative context, semantic anti-repetition filtering, lifecycle grouping, and persistent momentum scoring |
| `docs/app.js` | Modify | Add collection sidebar navigation, middle detail rendering, sorting, filtering, and lifecycle cues |
| `docs/styles.css` | Modify | Add three-column layout, clean side menu states, and responsive detail styling |
| `docs/index.html` | Modify | Move collection into the side menu and add a dedicated detail panel |
| `function_plan.md` | Modify | Reflect the implemented architecture |
| `plan.md` | Modify | Align the product and UI structure with the collection-first flow |

---

## Verification Checklist

- [ ] Ideas vary meaningfully day-over-day, not just by wording
- [ ] Semantic recurrence groups catch reworded versions of the same core idea
- [ ] Fallback mode still produces fresh combinations from live context
- [ ] Collection side menu stays clean while opening the correct detail in the middle panel
- [ ] Search returns relevant matches across names, summaries, trends, categories, and repos
- [ ] Recurring ideas show lifecycle momentum rather than raw recurrence alone
