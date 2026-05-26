# P1 · Agenda-Slide-Only Deterministic Fill — Implementation & Validation Report

Date: 2026-05-26 · Repo: `/Users/tylerzhao/Code/pptx-huang-poc` · Baseline tag
`poc-4.5-q3c-content-baseline-job28`.
**P1 only. Agenda slide only. No push, no deploy, no reindex.**

## 0. Goal & verdict
Fix the rendered-agenda mismatch (目录 items not matching 正文 section_titles) **without touching body
content**. Done: the agenda page's item slots are now deterministically filled with the exact deduped
body `section_title`s. **P0 content smoke stays PASS/WARN (not FAIL)** on the post-fix deck — body
content (P4/P8/P9) is unchanged. Ready for review.

## 1. Scope honored (hard rules)
Changed files: **`core/deck_polish.py`** + **`web/app.py`** only.
- NOT modified: `content_generator.py`, `content_normalizer.py`, `template_cloner.py` (table fill),
  `typography_polish.py`, `skills/skill_llm/llm_skill.py`. (verified `git diff --name-only`)
- NO global residue cleaning added (the Q3d regression cause); NO cover change; NO DB schema change;
  NO reindex/deploy. `deck_polish` contains **no** `fix_cover_slide`/`clear_known_residue` (grep=0).

## 2. Implementation
- `core/deck_polish.py`:
  - `_find_shape(slide, shape_id, name)` — locate a shape by id (then name).
  - `fill_agenda_deterministic(prs, agenda_slide_number, section_titles, slot_refs, log)` — overwrite
    the agenda page's content-slot shapes (by `slot_refs`) with the exact `section_titles` in order;
    clear extra agenda slots; log `agenda_overflow` when sections > slots. **Touches only the agenda
    slide's content-slot shapes — never another slide, never a table cell, never residue.**
  - `polish_deck(..., agenda_slot_refs=None)` — when slot refs are provided, run
    `fill_agenda_deterministic`; else fall back to the existing conservative `fix_agenda_slide`. All
    other passes (numbering strip / placeholder clear) unchanged.
- `web/app.py` (`_run_generation`, minimal wiring): read the agenda page's content-slot refs from the
  already-saved `blueprints.json` (slot_mappings, else content slots) and pass them + `ag.agenda_items`
  (deduped body section_titles, ordered by section_id, excludes cover/agenda/closing) to `polish_deck`.
- Agenda-item derivation (implements the requested steps): items = body `section_title`s
  (cover/agenda/closing/ending excluded by `_agenda_consistency`), **deduped preserving order**;
  fill first N where N = template agenda slots; log overflow; clear extra slots only.

## 3. Validation
**12-page T5 (job 123):**
- P0 smoke (`scripts/poc_content_baseline_smoke.py`): **OVERALL WARN, exit 0** — `slide_count 12 PASS`,
  `P4 360ch PASS`, `P8 30 cells PASS`, `P9 24 cells PASS`, contamination WARN (residue, not cleaned).
  **No body regression** (baseline job_121: 367/30/24 → 360/30/24).
- Agenda fill: `agenda_filled = [经营质效与财务表现, 产能效率与智能制造, 成本控制与精益运营]` — all **exact
  body section_titles** (no LLM rephrasing/numbering). `agenda_overflow = {sections:5, slots:3}`.
- closing title `致谢` **not** in agenda ✅. PPTX opens, 12 slides ✅.

**8-page T5 (job 125)** — agenda behavior only (12-page P0 gate intentionally NOT applied):
- 8 slides; `agenda_filled = [经营质效与财务表现, 产能效率与智能制造, 成本精益与运营优化]` (exact section_titles);
  closing `谢谢` not in agenda; `agenda_overflow = {5,3}`.

## 4. Results vs the requested checks
| Check | Result |
|---|---|
| 1. Generate 12-page T5 | ✅ job 123 |
| 2. Run P0 smoke on output | ✅ run |
| 3. P0 PASS/WARN (not FAIL) | ✅ WARN (exit 0) |
| 4. Rendered agenda items == first N actual body section_titles | ✅ exact section_titles (N=3 template slots) |
| 5. Closing not in agenda | ✅ |
| 6. PPTX opens | ✅ |
| 7. P4/P8/P9 not below baseline | ✅ 360 / 30 / 24 |
| 8. 8-page agenda behavior (no 12-page gate) | ✅ job 125 exact section_titles |

## 5. Known template-side items (NOT P1 defects; documented)
- The T5 agenda page has **3 item slots** but decks produce **5–6 sections** → only the first 3 are
  shown (logged `agenda_overflow`). Showing all needs fewer sections or a richer agenda layout
  (template/outline-planning) — out of P1.
- The 3 shown items' **visual top-to-bottom order** follows the template's slot geometry (shape order),
  not strict section order; content is exact section_titles.
- **Residue rectangles** on the agenda slide (e.g. `国资委穿透式监管解读`, `落地路径及相关保障`, `案例实践`)
  remain — P1 does **not** clean residue (no global cleaner). These are reported by P0 as WARN and are
  in P2's (table-header-only) scope decision, not P1.

## 6. Git / next
Changed `core/deck_polish.py` + `web/app.py` only. Explicit-path commit; **no push** until review.
Recommend: review → push → P2 (table-header residue only) using the P0 smoke as the regression gate.

— End P1 report (agenda slide only; body content unchanged; no push/deploy) —
