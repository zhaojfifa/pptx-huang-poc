# Q3c-final Plan · Functional Closure Before Final Cloud Reindex

> Plan accepted for execution as a single continuous round in **two commits** (no long-term PR split):
> Commit A = agenda freeze + `/custom` frontend closure + `.gitignore` safety; Commit B = single-page
> reanalysis backend + real `/custom` reanalyze API. No local `t5_new` reindex; no deploy; no wholesale
> Huang port; no `web/app.py` replacement.

## Context
The Q3b outline editor + page-type calibration is committed and live (`88b7ce2`, in sync with
origin/main). Before the final cloud reindex onto the real master `t5_new`, we close functional gaps:
freeze the agenda editor to a safe scope, make the `/custom` "重新分析本页" button real, and absorb a
genuinely-new capability (single-page reanalysis) from the newest Huang package — selectively, not
wholesale. The new master `t5_new.pptx` is already in `templates_storage/` but is **reindexed on
Alibaba Cloud, not locally**.

## 1. Overall verdict
- Enter Q3c-final: **YES**, one continuous round, **two commits** (A then B).
- **Absorb:** agenda freeze; custom frontend closure; single-page reanalysis (idea from Huang-new
  `regenerate_single_page` + `--template_id/--page_number`, re-implemented on current helpers);
  `export_single_slide` as a **dual backend** (COM + LibreOffice/PDF/pypdfium2 single-page render);
  reuse current `update_by_template_page`; `.gitignore` protection for the space-named package.
- **Do NOT absorb this round:** overflow/truncation/line-count helpers → **deferred to Q3c-3**; no
  cover/agenda render specialization; no `web/app.py` replacement; no wholesale Huang port; no local
  `t5_new` reindex; no deploy.

## 2. Current repo state
- HEAD = `88b7ce2`, clean, in sync with origin/main. Suitable to start.
- Untracked risk: `data/pptx_agent _20260525new/` (**space** in name) is NOT matched by the existing
  `.gitignore` rule `/data/pptx_agent_20260525/` → must add an explicit ignore rule.
- `templates_storage/` gitignored; holds `t5_new.pptx` + stale `~$t5.pptx` lock (harmless).

## 3. Huang 20260525new scan summary (reference only)
| Capability | In current? | Huang-new | Action |
|---|---|---|---|
| `regenerate_single_page(template_id,page_number)` | ❌ | ✅ analyzer L492–584 | **Adapt** with current helpers |
| `--template_id/--page_number` argparse | ❌ | ✅ L586–599 | **Adopt** (small branch) |
| `update_by_template_page` | ✅ robust (rowcount, JSON whitelist) | ✅ simpler | **Reuse current** |
| `export_single_slide` | ❌ | ⚠️ Windows-COM only | **Reimplement dual backend** |
| markdown split / SameFileError guard | ✅ (Q3a) | mixed | none |
| JSON-fence parsing | ❌ | ❌ (same gap) | optional, separate |
| `_count_actual_lines` / truncation / capacity override | ❌ | ✅ | **DEFER (Q3c-3)** |

Current analyzer already has all per-page building blocks (`analyze_with_llm`, `analyze_with_vision`,
`analyze_generation_hints`, `split_markdown_by_slide`, page_type classify+persist via
`core.page_type_prompt` + `_PAGE_TYPE_CANON`, SameFileError guard) → `regenerate_single_page` mostly
reassembles existing current functions for one page.

## 4. Scope
**A. Agenda freeze** (`static/templates/index.html`): remove per-item add ("+ 添加目录项") + delete
("×") + warning-box "加入目录"; remove/stub `addAgendaItem`/`delAgendaItem`/`addToAgenda`; keep
`editAgendaItem` (edits + syncs body `section_title` old→new); keep orphan **warning** (display only);
closing/ending stay out of the agenda via existing `roleOf` + `_validate_confirmed_outline`.

**B. Single-page reanalysis** (Commit B): `regenerate_single_page(N,K)` generate-then-replace using
current helpers + new `export_single_slide`; CLI `--template_id N --page_number K`; real
`/api/custom-template/reanalyze-page`; one-row `update_by_template_page`; failure leaves row intact;
idempotent. `export_single_slide(pptx,out,idx)`: COM exports slide idx; LibreOffice converts deck→PDF
(reusing `_export_via_libreoffice`) and renders only PDF page idx-1 → `slide_idx.png`.

**C. Custom closure** (`static/templates/custom.html`): index + page_type save stay working; reanalyze
button → pending state in Commit A, real API + on-success index refresh + clear failure in Commit B.

**D. Overflow/truncation — DEFER (Q3c-3).** Not implemented this round.

**E. Cloud `t5_new` reindex handoff** (operator-run, after push): pull → `init_db` → back up
`t5.pptx`, put `t5_new` in place (same path/name to keep `商务风格` + file_path valid) → analyze
`商务风格` → validate 8-page + 12-page → manual open.

## 5. File impact
- Commit A: `static/templates/index.html`, `static/templates/custom.html`, `.gitignore`,
  `docs/.../poc_4p5_huang_q3c_final_plan.md`.
- Commit B: `template_analyzer/analyze_template.py`, `skills/skill_ppt_screenshot/ppt_screenshot_skill.py`,
  `web/app.py` (endpoint body only), `static/templates/custom.html` (wire real API),
  `docs/.../poc_4p5_huang_q3c_final_functional_closure_report.md`. `database/db.py`: no change unless required.

## 6. Risks
- Single-page DB: Low — generate-then-replace, one-row update, failure-safe, idempotent.
- Screenshot/vision: Medium — soffice/pypdfium2 required; **abort-without-write on screenshot failure,
  vision optional** (mirrors full-analyze tolerance).
- /custom API: Low — additive, threaded, clear errors.
- Agenda freeze: Low — removes add/del only; edit+sync intact.
- 8/12-page regression: Very low — no generation/clone-chain change.
- Cloud reindex: Medium — keep `t5.pptx` path, back up first, validate before relying.

## 7. Validation
Local: `/custom` 200; page_type save (one row, restore); single-page reanalysis changes only page K
(snapshot/diff all rows); agenda add/del gone but edit still syncs; 8-page + 12-page + T6 smokes.
Cloud (final, operator): pull → init_db → replace t5_new → analyze 商务风格 → 8/12-page gen → open.

## 8. Split decision
Per adjudication: **no long-term PR split** — one continuous round, **two commits** (A: agenda freeze
+ custom closure + gitignore; B: single-page reanalysis). Q3c-3 (overflow/truncation) deferred to a
later dedicated visual-optimization PR.

## 9. Do-not-do
No wholesale Huang port; no `web/app.py` replacement; do not commit `data/pptx_agent _20260525new/`,
`data/pptx_agent_20260525/`, `templates_storage/`, PPTX/PNG, `logs/`, `output/`, `.env`, `.zshrc`,
DB dumps; no local t5_new reindex; no deploy; no cloud changes; Q3c-3 not implemented.
