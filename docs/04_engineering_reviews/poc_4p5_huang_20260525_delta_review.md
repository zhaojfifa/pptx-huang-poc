# Delta Review — `data/pptx_agent_20260525` vs current `pptx-huang-poc`

Date: 2026-05-25 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
**Read-only review.** No current code/DB/templates/deployment changed; no migrations; no
re-index; no commit. The current project is **live on Alibaba Cloud** (T5 main / T6 backup /
`/custom` upload flow validated).

## 1. Overall verdict
**NO-GO to direct replacement. GO for narrow selective absorption (analyzer robustness only),
AFTER deployment, with manual validation. HOLD on `page_type` adoption.**

`data/pptx_agent_20260525` is **not a newer superset** — it is a leaner/divergent branch. Its
`web/app.py` is **218 lines vs the current 1076**, and it is **missing the entire deployed
product surface** and recent hardening:
- Missing endpoints: all `/api/poc/*` (outline/generate/status/source.upload) and all
  `/api/custom-template/*` (upload/analyze/status/thumbnail/outline/generate).
- Missing frontend: `static/templates/custom.html` (whole custom-flow UI); `index.html` is a
  minimal form (no template select / outline editor / page-type badges).
- Missing core modules present only in current: `core/page_type_prompt.py`,
  `core/deck_polish.py`, `core/typography_polish.py`, `core/native_chart_rebind.py`.
- Missing web helpers: `_agenda_consistency`, `_outline_quality_gate`,
  `_slot_fragmentation_report`, `_final_contamination_scan`, `_build_template_index`
  (incl. the `_as_dict` decode fix).

Replacing current code with this branch would severely regress the live POC.

## 2. Major improvements in the new branch (genuine)
- **Robust per-page markdown split** — `split_markdown_by_slides()` (analyzer L412–461): prefix-
  before-first-marker handling + duplicate-marker dedup, vs current `split_markdown_by_slide()`
  (L229) cruder split.
- **Consistent `enable_thinking=False`** on analyzer LLM calls incl. the **vision** call
  (`chat_with_image`, L294) and style/hints calls (L253/391/489) → cost/latency. Current sets
  it on fewer analyzer calls (only L426 confirmed).
- **Fresh table headers** — slide prompt tells the LLM to design its own headers
  ("不要照搬模板原表头", ≥3 cols / ≥3 rows) instead of echoing template headers → less template
  residue at the source (current instead neutralizes via Q2I de-brand + Q2G centering).
- **Correction prompt carries `original_prompt`** for better module-count recovery.
- Schema/DAO: `page_type VARCHAR(50)` column + duplicate-tolerant `ALTER` migration +
  `TemplatePageDAO.create(page_type=...)` + new `update_by_template_page()`.

## 3. Bug fixes found (and current parity)
| New-branch fix | Current status |
|---|---|
| Markdown split prefix/dedup robustness | current lacks → **worth absorbing** |
| `enable_thinking=False` on vision/analyzer calls | partial in current → **worth absorbing** |
| Fresh self-designed table headers | current solves differently (de-brand + centering) |
| Correction prompt includes original prompt | minor; optional |
| SameFileError | **already fixed in current** (commit 7f22623); new branch also tolerant |
| JSON-fenced LLM parse (```` ```json ````) | NOT visibly fixed in either; current relies on retry — unchanged risk |
| Agenda-as-KPI misread / missing page_type / md residue | current addresses via Q2D agenda guard + Q2I de-brand; new branch addresses md residue via fresh headers only |

## 4. Schema changes & migration requirements
- New code adds **only `page_type VARCHAR(50)`** to `template_pages` (db.py L71, L117–129). The
  DDL pasted by the architect also shows **`pagetype LONGTEXT`**, which is **NOT in the new
  code's `init_db()`** — likely a manual/experimental column in the architect's live MySQL, not
  a code artifact. Treat `pagetype` as out-of-band; only `page_type` is real in code.
- **`page_type` is half-wired in the new branch:** schema + DAO + read-path exist
  (`content_generator` reads `tp.get("page_type")` L165/460), **but the analyzer never writes
  it** — both `update_by_template_page(...)` (L575) and `create(...)` (L694) omit `page_type`,
  so it stays NULL. No classifier persists it. The advertised "页面类型标识能力" is therefore not
  actually populated by the shipped analyzer.
- Absorbing `page_type` would be **backward compatible**: nullable additive column via the same
  duplicate-tolerant `ALTER TABLE ... ADD COLUMN` pattern current `init_db()` already uses for
  `generation_hints`. Existing rows **id23 / id24 / custom id26** get NULL — **no breakage**
  (current never references `page_type`; it classifies at runtime via
  `core/page_type_prompt.classify()`; DAOs name columns explicitly). **No DB wipe, no reseed, no
  re-analyze** just to add the column.

## 5. Risks to current T5/T6 baseline
- **Direct replacement: critical regression** — loses POC + custom flow, frontend, agenda guard,
  typography polish, native chart rebind, contamination scan, and the `_build_template_index`
  decode fix → live Alibaba deployment would break. ❌
- **Adopting the new branch's simplified generation** (removed agenda binding + removed
  `page_type_prompt` injection): undoes Q2D agenda consistency and per-role guidance validated
  for the T5 main route → topic-drift regression. ❌
- **Adding the `page_type` column alone: low risk** (additive/nullable) but **low value** unless
  a writer/classifier populates it. ⚠️
- **Cherry-picking analyzer robustness** (markdown split, enable_thinking): **low risk** if done
  as a small isolated PR with re-validation of one T5 + one T6 run. ✅

## 6. Recommended absorption plan (classified)
1. **Must absorb before deployment:** NONE. Deployment is already live on the superset.
2. **Absorb after deployment (low-risk, real value):**
   - Port `split_markdown_by_slides()` (prefix/dedup) into current
     `template_analyzer/analyze_template.py`.
   - Add `enable_thinking=False` to current's analyzer vision/style/hints calls that lack it.
   - (Optional) add `original_prompt` to current's `_normalize_modules` correction prompt.
3. **Do not absorb / risky:**
   - New `web/app.py`, `static/` frontend, and the simplified `content_generator` outline
     (no agenda binding, no page_type_prompt injection) — they regress current capabilities.
   - The out-of-band `pagetype LONGTEXT` column.
4. **Needs manual validation before adopting:**
   - `page_type` persistence — only worth it if we **wire a writer** (e.g. persist current
     `ptp.classify()` into a new `page_type` column so `_build_template_index` / frontend show
     an authoritative page type and `content_generator` can read it). Validate it beats today's
     runtime classification first.
   - The "self-designed table headers" prompt change — A/B against current de-branded headers on T5.
   - Clarify with the architect how their live DB populates `page_type` / `pagetype`.

## 7. Exact next PR proposal (optional, post-deployment, gated)
**PR-Q3a · Analyzer robustness cherry-pick (no product/flow change).**
- Scope: current `template_analyzer/analyze_template.py` only — port robust
  `split_markdown_by_slides()` + add `enable_thinking=False` to vision/style/hints calls.
- Optional add-on: additive `page_type VARCHAR(50)` migration in `database/db.py` (duplicate-
  tolerant ALTER) + `TemplatePageDAO.create(page_type=)`, and persist `ptp.classify()` so the
  custom index/frontend show authoritative page types. Backward compatible with id23/24/26.
- Out of scope: any web/app.py, frontend, agenda/typography/chart/contamination logic; no DB
  wipe; no re-index of T5/T6 unless validating the new split end-to-end on a fresh analyze.
- Validation: re-analyze one small template, run one T5 + one T6 generation, confirm opens +
  agenda pass + contamination 0 + no regression; diff md-split output before/after.

## 8. Verification (factual basis)
- Schema: `data/pptx_agent_20260525/database/db.py` L67–129 (page_type add + ALTER), L178–241
  (DAO `create` / `update_by_template_page`).
- Analyzer omits page_type write: `…/template_analyzer/analyze_template.py` L575, L694.
- page_type read-only use: `…/core/content_generator.py` L165–166, L460.
- Divergence: `core/` listing (current has page_type_prompt / deck_polish / typography_polish /
  native_chart_rebind; new branch does not); `wc -l web/app.py` = 1076 (current) vs 218 (new).

— End delta review (read-only; no code/DB/template/deploy changes; not committed) —
