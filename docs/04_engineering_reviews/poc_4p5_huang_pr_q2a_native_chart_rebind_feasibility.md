# PR-Q2A — Native Chart Clone / Rebind Feasibility

Date: 2026-05-23 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Feasibility only — no chart skill implemented, no TemplateCloner redesign, no old-mainline
code imported, nothing committed.

## Verdict: **GO WITH CONDITIONS — native chart rebind**

Native charts clone-preserve perfectly and their data **can** be updated while staying
native+styled, but **not** via python-pptx `replace_data()` (the template charts link an
external workbook). A small **numeric-cache XML rewrite** is required, plus designer
clean-up. Hybrid image fallback is **not** needed.

## Task 1 · Template chart objects

- **t5 (id 19):** **no native charts** — `ppt/charts/` empty, `ppt/embeddings/` empty.
- **t6 (id 20, clean master):** **slide 7 has two native charts** `图表 50` / `图表 51`,
  both `COLUMN_CLUSTERED`, 1 series each. python-pptx detects them (`shape.has_chart`,
  `shape.chart.chart_type`). Package: `ppt/charts/chart1.xml`, `chart2.xml` (+ style1/2,
  colors1/2). **No embedded workbook** (`ppt/embeddings/` empty).
- Chart data source: `chart1.xml.rels` → `rId3` `oleObject` **TargetMode="External"**,
  `Target=file:///D:\日常工作\吴部长\技术群\优秀智能体、模型清单.xlsx` — a broken Windows
  path from the original author (also a privacy/contamination leak).
- The chart renders from `<c:numCache>` (values 9,8,7,4,1) + `<c:strCache>` (series name
  「汇总」; category cache 「AI+生产…」 — more residue).

## Task 2 · Clone preservation

- The cloner's first step is `shutil.copy(master → output)`; it then mutates only **text
  frames and tables**. Charts are `graphicFrame` objects in neither slot list, so they are
  **never touched** → preserved 1:1 (type/axis/legend/colors intact).
- Verified: a cloned copy of t6 still reports both charts on slide 7
  (`图表 50`/`图表 51`, COLUMN_CLUSTERED). Style/colors parts (`style1.xml`,`colors1.xml`)
  are not referenced by the fill path → unchanged.
- (Note: `clone_and_fill` with **no blueprint** hits an unrelated pre-existing crash in the
  heuristics path — `_fill_with_heuristics` slide-height lookup. Real generation always
  passes blueprints, so this does not affect chart preservation. Out of scope here.)

## Task 3 · Minimal data rebind

Test dataset: x=`Q1..Q4`; 营业收入=`728.8,784.9,810.6,850.7`; 归母净利润=`24.3,24.5,30.8,23.9`.

1. **python-pptx `chart.replace_data(CategoryChartData)` → FAILS.**
   `ValueError: .target_part ... undefined when target-mode is external`. Cause: the chart's
   data rel is an **external** workbook and there is **no embedded xlsx** for python-pptx to
   update. This is the standard, expected python-pptx path and it is blocked here.
2. **Direct `<c:numCache>` / `<c:strCache>` XML rewrite → WORKS.** Rewrote the value cache to
   `728.8,784.9,810.6,850.7` and the category cache to `Q1..Q4`, repackaged the pptx, and
   re-read with python-pptx:
   - series values now `[728.8, 784.9, 810.6, 850.7]`, categories `['Q1','Q2','Q3','Q4']`
   - `chart_type` still `COLUMN_CLUSTERED` (remains a native, editable chart)
   - `style1.xml` / `colors1.xml` untouched → **styles/axis/legend/colors preserved**.
   - Multi-series (2-series test data) not applied: the template chart has **1 series**, so
     adding a second series needs extra `<c:ser>` node surgery (single-series rebind is the
     simple, proven case).

## Task 4 · Evidence

- Cloned (preservation) PPTX: `/tmp/q2a_clone.pptx` — both charts present.
- Cache-rebind PPTX: `/tmp/q2a_cache_rebind.pptx` — series/categories updated, native.
- **Visual update after opening in PowerPoint:** *not verifiable on this machine* (no
  PowerPoint/LibreOffice-render check performed). PowerPoint renders charts from
  `<c:numCache>`, so the updated values should display; **Jackie should open
  `/tmp/q2a_cache_rebind.pptx` in PowerPoint to confirm rendering.**
- **Native/editable:** yes — remains a real chart object.
- **Styles preserved:** yes (style/colors parts unchanged).
- **Code path used:** `zipfile` read → regex rewrite of `c:numCache`/`c:strCache` in
  `ppt/charts/chart1.xml` → repackage. (NOT python-pptx `replace_data`.)

### Risks / limitations
1. `replace_data()` unusable until the chart has an **embedded** workbook (currently external).
2. With cache-only rewrite, PowerPoint **"Edit Data"** points at the broken external file —
   the chart *displays* correctly but in-PPT data editing is broken.
3. Multi-series / changing series count needs `<c:ser>` add/remove logic, not just cache edits.
4. Template charts carry **contamination** (external path, category 「AI+生产…」, series
   「汇总」) → must be de-branded.
5. Real-PowerPoint render not yet confirmed (manual check needed).

## Conditions to reach a clean "GO"
1. **Designer:** in PowerPoint, open the master chart → *Edit Data* → which **embeds an
   xlsx workbook** (removes the external link) and de-brands categories/series names. After
   that, python-pptx `replace_data()` works cleanly **and** "Edit Data" is functional.
2. **Engineering (small, scoped):** a minimal `native_chart_rebind` helper that either
   (a) calls `replace_data` when an embedded workbook exists, or (b) falls back to the
   proven `numCache/strCache` rewrite — both keep the chart native and styled. No new chart
   library, no image stack.
3. Handle series-count changes (multi-series) explicitly.
4. De-brand chart caches/external links as part of the master cleanup.

**Recommended next PR:** PR-Q2B — designer embeds+de-brands the t6 chart workbook, then a
minimal `native_chart_rebind` helper (replace_data with numCache-rewrite fallback),
single-series first. Keep hybrid image chart skill as the documented fallback only if a
future chart type can't be expressed natively.

— End PR-Q2A —
