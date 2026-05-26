# P1.6 · Cover-Only Deterministic Fill + Minimal Fidelity Gate — Validation Report

Date: 2026-05-26 · Repo: `/Users/tylerzhao/Code/pptx-huang-poc` · HEAD `86803ea` (P0+P1; Q3d reverted).
**Validation done; NOT committed (awaiting review). No push, no deploy, no reindex.**

## 0. Verdict
The final PPT's slide-1 cover title/subtitle now come **strictly from `confirmed_outline` page 1**, via a
targeted cover-slide-only fill in `deck_polish`. Validated: an edited cover title/subtitle appears
verbatim on slide 1; **P0 body smoke stays WARN/PASS (not FAIL)** — no body regression; agenda (P1) and
residue behavior unchanged (no global cleanup). Ready for review.

## 1. Scope honored
Changed files (allowed only):
- `core/deck_polish.py` — new `fix_cover_slide` (cover slide only) + `polish_deck` cover params.
- `web/app.py` — pass `confirmed_outline` page-1 title / first point to `polish_deck` (slide-1 only).
- `scripts/poc_outline_fidelity_gate.py` — **new, read-only** fidelity gate.
- this report.

Verified untouched (forbidden): `content_generator.py`, `content_normalizer.py`, `template_cloner.py`,
`typography_polish.py`, `skills/skill_llm/llm_skill.py`, `template_analyzer/*`, `database/*`, templates.
No global residue cleaning (`clear_known_residue`/`_HARD_RESIDUE` count = 0). No prompt change, no body
title/points overwrite, no table/row-cap/truncation/font change, no DB/schema/reindex/deploy.

## 2. Implementation
`core/deck_polish.fix_cover_slide(prs, cover_title, cover_subtitle, log)` — slide 1 only:
- title → visible title shape: prefer a shape whose **name contains 标题/title**; only if that fails, the
  conservative **topmost** text shape. Subtitle → only a shape whose **name contains 副标题/subtitle**
  (no fallback; skipped if absent). Writes ONLY those one/two shapes via `_set_first_para`. Never blanks
  arbitrary shapes, never touches other slides/tables/residue. Does not rely on the blueprint title slot.
- `polish_deck(..., cover_title=None, cover_subtitle=None)` runs `fix_cover_slide` first (cover only),
  then the existing P1 agenda fill + numbering-strip + placeholder-clear (unchanged).
- `web/app.py _run_generation`: `cover_title = confirmed_outline.slides[0].title`,
  `cover_subtitle = slides[0].key_points[0]` (if any), passed to `polish_deck`. Slide-1 only.

## 3. Minimal fidelity gate (read-only)
`scripts/poc_outline_fidelity_gate.py` (no LLM/DB, no writes, no auto-fix) reports against
`confirmed_outline.json`: `opens`, `slide_count`, `cover_title_match`, `cover_subtitle_match`
(skipped if no subtitle shape), `agenda_items_match` (PASS=all body section_titles present; WARN=leading
subset/template overflow), and P0 body metrics `P4_text_chars`, `P8_table_cells`, `P9_table_cells`.
Hard gates (exit 1): opens, slide_count, P4/P8/P9 floors, and a cover_title MISMATCH; subtitle/agenda
nuances are WARN. The P0 content smoke (`scripts/poc_content_baseline_smoke.py`) is unchanged.

## 4. Validation (12-page T5, job 127; cover title+subtitle edited to markers)
**P0 content smoke** → OVERALL **WARN, exit 0**:
`opens PASS · slide_count 12 PASS · P4 356ch PASS · P8 30 PASS · P9 24 PASS · contamination WARN`
(residue still present → confirms **no global cleanup ran**). Baseline job_121 was 367/30/24 → **no body regression**.

**Fidelity gate** → OVERALL **WARN, exit 0**:
| check | result |
|---|---|
| opens | PASS |
| slide_count | PASS (12) |
| **cover_title_match** | **PASS** — want `Q1P6封面标题验证XYZ`, got `Q1P6封面标题验证XYZ` |
| **cover_subtitle_match** | **PASS** — want `Q1P6副标题验证ABC`, got `Q1P6副标题验证ABC` |
| agenda_items_match | WARN — 3/6 present (leading subset; template has 3 agenda slots) |
| P4_text_chars | PASS (356 ≥ 150) |
| P8_table_cells | PASS (30 ≥ 12) |
| P9_table_cells | PASS (24 ≥ 12) |

`deck_polish` report: `cover_set = [{标题 3: title=Q1P6封面标题验证XYZ}, {副标题 5: subtitle=Q1P6副标题验证ABC}]`;
`agenda_filled = [经营质效与财务表现, 产能效率与智能制造, 成本管控与运营优化]` (P1 intact).

### Against the requested checks
1. Generate 12-page T5 ✅ (job 127) · 2. Run P0 smoke ✅ · 3. P0 PASS/WARN not FAIL ✅ (WARN) ·
4. Slide-1 title == confirmed cover title ✅ (cover_title_match PASS) · 5. Slide-1 subtitle == first point
(subtitle shape exists) ✅ · 6. Agenda still shows first N body section_titles ✅ (3/6, P1) ·
7. P4/P8/P9 not below thresholds ✅ · 8. No global cleanup evidence ✅ (residue still present as WARN) ·
9. PPTX opens ✅.

## 5. Notes / template-side (unchanged, not P1.6 defects)
- Cover fill found the visible name-matching shapes (`标题 3` / `副标题 5`) directly; the topmost fallback
  was not needed here and is the only non-name path (conservative). If a template has no 副标题/subtitle
  shape, subtitle is skipped (gate reports it skipped).
- Agenda 3/6 is template slot capacity (3 item slots) — logged `agenda_overflow`; the shown items are exact.
- Residue (穿透式监管 …) remains by design (no global cleaner); reported as WARN by both scripts. Table-header
  residue is the separate P2 decision (NOT started).

## 6. Git / next
Changed `core/deck_polish.py` + `web/app.py` + new `scripts/poc_outline_fidelity_gate.py` + this report.
**Not committed** (awaiting review). On approval: explicit-path commit, then push; P2 (table-header residue
only) remains separate and not started.

— End P1.6 report (cover slide only; body unchanged; not committed; no push/deploy) —
