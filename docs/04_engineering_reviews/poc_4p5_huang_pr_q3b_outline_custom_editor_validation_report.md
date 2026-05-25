# PR-Q3b Local Validation — Outline Editor + Template Page Index Calibration

Date: 2026-05-25 · Repo: `/Users/tylerzhao/Code/pptx-huang-poc` · Branch: `main`
**Local validation only.** No commit, no push, no Alibaba Cloud deploy. Built on top of the
committed Q3a (`693e7a7`). Scopes A–G per the task brief.

## 0. Verdict (TL;DR)
Outline editor (A), confirmed-outline validation (B), agenda structural warnings (C), `/custom`
page-index calibration + page_type save (D), and 8-page quick mode (G) are **implemented and pass
local validation**. Single-page reanalysis (E) is an **honest `501 not_implemented` stub, deferred
to Q3c** (as agreed). The **edit→outline plumbing is verbatim-correct** and body-slot edits render;
**cover/agenda render fidelity is a pre-existing template-residue/slot-fill limitation** (not a Q3b
regression) — recommend a Q3c follow-up. **Recommend commit** (additive, 12-page path unchanged).
**Hold cloud deploy** until cover/agenda fidelity is validated on the cloud template.

---

## 1. Scope / files changed (7 files, all additive & backward-compatible)
| File | Change |
|---|---|
| `database/db.py` | `TemplatePageDAO.update_by_template_page(...)` — in-place single-row update (page_type save; future Q3c reanalysis) |
| `core/agent.py` | `_select_template_page()` honors outline `template_page_number` in content + layout steps; falls back to positional (12-page identical). Stamps `_template_page_number` on slide_data |
| `core/content_generator.py` | `generate_outline(page_numbers=…)` — optional master-page subset for shorter decks; spec block + RULES say "Deck slide N → Template Page M" |
| `core/template_cloner.py` | `clone_and_fill` selects source slide by `_template_page_number`; **drops unused master slides** for short decks (only when no duplication; 12-page keeps all) |
| `web/app.py` | canonical `page_type` on cards; `_subset_page_numbers` (8-page map); `_validate_confirmed_outline` (Scope B); poc_outline returns options/agenda_items/structure_warnings + passes page map; poc_generate blocks on structural errors + surfaces warnings; `/api/custom-template/page-type` (save) + `/reanalyze-page` (501 stub); `_build_template_index` adds md_preview/hints_summary/page_type_raw/persisted |
| `static/templates/index.html` | Step-3 editor: per-page page_type `<select>` (cover/agenda/content/table/chart/closing), editable title/points/section_title/role, cover/agenda/closing labels, agenda warning banner, **保存大纲** + confirm; handles validation errors |
| `static/templates/custom.html` | Page index shows md/hints preview + persisted/auto badge; per-page page_type `<select>`+保存类型; 重新分析本页 button (shows the 501 stub message) |

---

## 2. UI behavior (text walkthrough)
**Main POC · Step 3 (outline editor).** Each page renders as a card with: page no. + colored role tag
(封面/目录/正文/表格/图表/结束) + `模板页 #N · 章节 X`; a **页面类型** dropdown (6 canonical values);
an editable **title**; for body pages editable **所属章节 (section_title)** and **本页作用 (role)**;
and a **要点** textarea (labelled "目录项（每行一个，可增删/调整顺序）" on the agenda page,
"副标题/要点" on the cover). A warning banner lists structural issues (page1/2/last role, body
sections not in the agenda) and updates live. Buttons: **确认大纲并生成 PPT**, **保存大纲** (re-validate
+ toast), **返回修改**. No drag editor (per constraint). Changing a page's type re-renders the card
(cover/agenda/closing show/hide section fields).
**/custom · page index.** Each page tile now shows thumbnail, `page_type` + 已保存/自动判定 badge,
slot counts, a markdown preview, a generation_hints preview, warnings, a **page_type `<select>` +
保存类型**, and **重新分析本页**. Saving persists immediately; reanalyze shows the deferral message.

---

## 3. Backend API diff (behavioral)
- `POST /api/poc/outline` → now also returns `page_type_options`, `agenda_items`, `structure_warnings`;
  when `page_count < template pages`, maps to a cover/agenda/body/closing subset and tells the LLM the
  slide→master-page mapping. Schema unchanged for existing consumers (additive keys).
- `POST /api/poc/generate` → validates the confirmed outline (Scope B). **Blocks** (HTTP 200,
  `status:"error"`, `code:"outline_structure_invalid"`, clear `message`) on: empty outline, count >
  template pages, page 1 ≠ cover/title, page 2 ≠ agenda/section, last ≠ closing/ending. **Advisory**
  `structure_warnings` for body sections missing from the agenda. Confirmed outline still used verbatim.
- `POST /api/custom-template/page-type` → `{template_id, page_number, page_type}`; validates against
  the canonical set; updates only that row; clear errors for missing row / bad type.
- `POST /api/custom-template/reanalyze-page` → `501 {status:"not_implemented", code:
  "single_page_reanalysis_deferred"}` (never a fake success).

---

## 4. Outline edit validation (Scope F)
Driver: real HTTP against a local server (T5 = 商务风格 → resolves to id 28, 12 pages, page_type
populated). Edited cover title+subtitle, agenda items, one body slide (title+points+section_title).

- **Edit → confirmed outline is verbatim-correct.** `logs/job_104/confirmed_outline.json`:
  `title="Q3B封面验证标题"`, slide 1 `title="Q3B封面验证标题"`, slide 2 `key_points=["Q3B章节甲",
  "Q3B章节乙","Q3B章节丙"]`. ✅ The editor plumbing works end-to-end.
- **Structural validation works:** valid outlines pass; a bad outline (no cover/agenda/closing) returns
  3 clear errors (unit-tested); orphan-section **warning fired** in both runs.
- **Final PPTX opens:** job 104 = 12 slides, job 106 = 8 slides. ✅
- **Edit markers in the rendered PPTX:**
  | marker | 12-page (job 104) | 8-page (job 106) |
  |---|---|---|
  | body point `Q3B正文要点ALPHA` | — | **slide 4 ✓** |
  | body title `Q3B正文验证标题` | **slide 4 ✓** | — |
  | agenda items `Q3B章节甲/乙/丙` | not rendered | **slide 2 ✓** |
  | cover title / subtitle | not rendered | not rendered |

### 4.1 Cover/agenda render fidelity — pre-existing limitation (NOT a Q3b regression)
The edited values reach `confirmed_outline.json` verbatim and feed the pipeline, but the **rendered
cover/agenda slides show template residue** (e.g. cover title shape `标题 3` keeps
`央国企穿透式监管解决方案介绍`; agenda shapes keep `国资委…`). Root cause is the **template's analyzed
slot mapping vs. its actual cover/agenda shapes** (layered/duplicate text boxes) plus the agenda being
driven by body `section_title`s + `deck_polish`, not the agenda slide's own points. This is exactly the
"模板/slot 残留" the brief anticipated for these calibration tools to *help diagnose*, and it is
**present without Q3b** (same residue in the Q3a control job 102). Body slots fill correctly; the
8-page run even rendered the edited agenda items. **Recommended Q3c:** (a) fill the cover title slot
from `slide_data["title"]` even when the master page has residual/duplicate title shapes;
(b) optionally let the agenda render from the edited agenda-slide points when explicitly edited.

---

## 4.2 Scope A+ · Outline hierarchy synchronization
Minimal cross-level linkage in the outline editor so editing a 一级/二级 title affects the 三级
口径 — without any full-text rewrite and without re-calling Kimi. **Frontend-only**
(`static/templates/index.html`); no backend, prompt, or main-generation changes.

- **Agenda item edit → body `section_title` sync.** The agenda page renders one input per item;
  editing an item finds body slides whose `section_title` equals the old value and updates them to
  the new value, preserving each body slide's `title`/`points`, and shows a warning toast that
  正文要点未自动重写（请人工确认）.
- **Orphan section warning + add-to-agenda.** A body `section_title` not present in the agenda items
  is listed in the advisory warning banner with a 「加入目录」 button that appends it to the agenda
  (never silently dropped).
- **Title-with-empty-points warning.** A body slide with a title but no points raises an advisory
  warning (points are never force-rewritten).
- **Generate path unchanged.** `confirmed_outline.json` is saved verbatim with the synced
  `section_title`; the per-slide prompt already injects the new `section_title` + `title` (proven by
  job 104 `llm_prompt_slide_4.txt`: `"section_title":"Q3B章节甲"` + `"title":"Q3B正文验证标题"` in the
  「目录归属（必须遵守）」 block). No Kimi outline re-generation, no full re-planning.
- **Validation.** **9/9 frontend logic assertions passed** (Node unit test against the code extracted
  from `index.html`): agenda→body sync, unrelated slides untouched, title/points preserved, rewrite
  warning, orphan detection, add-to-agenda, title-without-points warning, item add/delete. Script
  passes `node --check`. **No prompt / main-generation changes → 8-page and 12-page do not regress**
  (no backend files touched).

## 5. Custom page index validation (Scope D)
- `_build_template_index` returns per page: `page_type` (human) + `page_type_raw` (canonical) +
  `page_type_persisted` flag + `page_type_options` + `md_preview` + `hints_summary` + slot counts +
  warnings. Verified for template 28 (persisted) and a NULL custom/T6 template (runtime fallback).
- **page_type save:** `POST /api/custom-template/page-type {28,5,"chart"}` → `ok`; DB confirmed
  `page_type='chart'`; restored to `content`. Invalid type → clear 400. Missing row → 404.
- **reanalyze:** returns `501 not_implemented` with the deferral message. ✅ (no fake success)

---

## 6. Single-page reanalysis (Scope E) — DEFERRED to Q3c
Per the agreed decision, this round ships an explicit `501` stub only. **Q3c plan** (reference:
Huang 20260525, selectively — do not bulk-port): port `regenerate_single_page(template_id,
page_number)` + `--template_id/--page_number` CLI + `skills/skill_ppt_screenshot.export_single_slide`;
reuse the new `TemplatePageDAO.update_by_template_page` (already added) to update only that page's
`markdown_content/layout_json/visual_json/generation_hints/page_type`; generate-then-replace so a
failure never corrupts the existing row; idempotent on repeat. The `/api/custom-template/reanalyze-page`
endpoint and the UI button are already wired to call it.

---

## 7. T5 generation result
- **12-page (job 104):** outline 12 pages (types cover/agenda/content/chart…/closing); generate
  submitted, agenda guard ran, structure warning surfaced; final opens, **12 slides** — no regression
  from honoring `template_page_number` (positional path is unchanged when tpn == position).
- **8-page (job 106, Scope G):** outline returned **8 pages**; master page map `[1,2,3,4,5,6,7,12]`;
  final opens, **slide_count = 8** (cloner dropped the 4 unused master slides); the **last slide uses
  the closing master page** (shape signature `标题 2 + 灯片编号占位符 1`, text "谢 谢！") — Scope G #7
  satisfied. No silent fallback to 12.

---

## 8. T6 smoke result
`templates_storage/t6.pptx` is **missing locally** → no full T6 render (allowed fallback).
- `/api/poc/outline` for 科技蓝风格 → `ok`, 12 pages with page_types, **no error** (14-page master →
  subset map applied).
- `_build_template_index("科技蓝风格")` → 14 pages, all NULL page_type → **runtime fallback, no error**;
  new md_preview/hints_summary/options fields populated. ✅

---

## 9. Should this be committed?
**Recommend YES.** All changes are additive and backward-compatible:
- 12-page T5 path is byte-for-byte unchanged (tpn == position → positional selection; cloner deletes
  nothing when all master slides are used).
- New columns/endpoints/fields are additive; NULL page_type still falls back to runtime classify.
- Validation blocks only clearly-invalid outlines (normal LLM outlines pass; unit-tested).
Carry-forward caveat (document in the commit/PR): **cover/agenda render fidelity is a known Q3c
follow-up** — the editor is correct, the special-page rendering is not yet faithful.

Suggested explicit-path commit (do **not** `git add -A`):
```
git add core/agent.py core/content_generator.py core/template_cloner.py database/db.py \
        web/app.py static/templates/index.html static/templates/custom.html
git add docs/04_engineering_reviews/poc_4p5_huang_pr_q3b_outline_custom_editor_validation_report.md
```

## 10. Should this be deployed to Alibaba Cloud?
**Not yet.** The editor/validation/custom/8-page backend is safe, but two things should be checked on
the **cloud template** first: (1) whether cover/agenda render fidelity is better there (the live deck
uses a different analyzed template than local id 28); (2) an 8-page end-to-end on the cloud template
(local `t6.pptx` is absent, and 8-page deletes master slides — worth one cloud dry-run). Deploy after
Q3c addresses cover/agenda fidelity, or as a gated frontend-only rollout if cloud cover/agenda already
render acceptably.

---

## 11. Git discipline (this round)
No commit / push / deploy performed. `git status`: 7 modified files (4 core/db + web + 2 html), staging
empty. `.zshrc` and `data/pptx_agent_20260525/` are gitignored (Q3a) and do not appear. Generated
artifacts (jobs 103–106, `output/*.pptx`, `logs/`) are gitignored and will not be committed.

— End Q3b local validation report (no commit / push / deploy) —
