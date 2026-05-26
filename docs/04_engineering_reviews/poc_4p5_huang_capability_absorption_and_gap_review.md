# POC 4.5 · Huang Capability Absorption & Gap Review

Date: 2026-05-26 · Repo: `/Users/tylerzhao/Code/pptx-huang-poc` · HEAD `155b760`
Tag `poc-4.5-q3c-content-baseline-job28` · **Review only — no code/DB/template/deploy changes.**

Reference trees (read-only): `data/pptx_agent_20260525`, `data/pptx_agent _20260525new` (note space).
Baseline: `job_28_final.pptx` (cloud-accepted POC 4.5 content baseline). Local note: jobs 17/24/26/28 are
**cloud** jobs, not present locally (local jobs reached 121); analysis below uses the **code paths**
(current HEAD = Q3c-final effective code that produced job_28) + local Q3c-equivalent runs (job 121).

---

## 1. Executive verdict
The current engine has **absorbed the substantive Huang analyzer + page_type + single-page reanalysis
capabilities**; job_28 content quality is good and is now tag-protected. The remaining gaps to 4.5+ are
**narrow and isolatable**: (1) agenda page items don't match the outline/section_titles in the rendered
deck; (2) P8/P9 tables carry **template-header residue** (`是否模型/分析场景/模型场景`) and look thin;
(3) custom single-page indexing UX (full re-analysis is slow, perceived as stuck). **The Q3d regression
was caused by a *global* residue hard-clean blanking legit body/table content (and a JSON-parse change)
— NOT by the agenda/cover targeted fills.** So the agenda fix can be redone safely if isolated to the
agenda slide and decoupled from any global cleaner. **Recommend: P0 protect → P1 agenda-only → P2
table-header residue (targeted) → P3 custom UX; keep overflow helper (P4) deferred.**

## 2. Current baseline status
- HEAD `155b760` (Revert Q3d) == origin/main; tag `poc-4.5-q3c-content-baseline-job28` → `155b760`
  (annotated, pushed). Effective code == **Q3c-final** (Q3c-1 `cc9ceb2` + Q3c-2 `6bcfa20` preserved).
- Local post-revert 12-page run (job 121) confirms the content path: **P4 367 chars/15 shapes, P8 30
  table cells, P9 24 table cells** — body content healthy (the Q3d P4/P8-P9 regression is gone).
- Working tree clean. job_28 = this code state.

## 3. Huang capability absorption map
| # | Capability | Status | Evidence |
|---|---|---|---|
|1|**Analyzer**: PPTX parse, screenshot/vision, markdown/layout/visual/generation_hints, page_type classify, full t5_new reindex| **Absorbed ✅** | `template_analyzer/analyze_template.py` (markitdown + `extract_layout_json` + `analyze_with_llm/vision/generation_hints` + page_type via `core.page_type_prompt`+`_PAGE_TYPE_CANON`); screenshot dual backend (COM + LibreOffice→PDF→pypdfium2). t5_new reindex = run full analyze CLI (not done locally, by instruction). |
|2|**page_type / template_page_number**| **Absorbed ✅** | DB `template_pages.page_type` (nullable, dup-tolerant migration); analyzer writes it; shown+editable in `/custom` index and outline editor; generation prefers persisted page_type (prompt injection) + `agent._select_template_page` honors `template_page_number`; 8-page quick map `[1,2,..,closing]` via `_subset_page_numbers` + cloner drops unused master slides. |
|3|**Outline editor**| **Absorbed ✅ (with known render gap)** | `static/templates/index.html`: cover/agenda/body title/points/section_title/role editable; **agenda freeze in effect** (Q3c-1: no add/del, edit-only, edit syncs body section_title). **Gap:** agenda items can still differ from the *rendered* PPT (see §8.1). |
|4|**Custom page**| **Absorbed ✅ (UX gap)** | upload → analyze → index (thumbnail/page_type/md+hints preview) → page_type save → 重新分析本页 button (wired to real API). "正在解析母版" = real full re-analysis subprocess (~20+ min for 12 pages), polled every 5 s — slow, not deadlocked (see §8.3). |
|5|**Single-page reanalysis**| **Absorbed ✅** | CLI `python -m template_analyzer.analyze_template --template_id N --page_number K` (`regenerate_single_page`, analyze_template.py:495); API `/api/custom-template/reanalyze-page` (real, web/app.py:1220); generate-then-replace updates **only that row**, failure leaves row intact, idempotent; custom button wired. Available locally + on cloud after deploying `6bcfa20`/`155b760`. |
|6|**Table fill**| **Absorbed (native) ✅; residue ⚠** | `template_cloner._fill_table` fills the **native** template table from `table_data` (headers+rows), preserves cell styling, adds/deletes rows/cols. Residue + thinness analyzed in §6/§8.2. |
|7|**Content generation**| **Absorbed ✅ (baseline-good)** | `content_generator` + `content_normalizer` produce job_28-quality body content. Critical paths in §7. |
|8|**Huang-new extras**| Mixed | fresh-header instruction **NOT absorbed** (valuable, fixes table residue); overflow/line-count helper **NOT absorbed** (deferred); JSON/markdown stability **NOT absorbed** (Q3d attempt reverted). See §4 + §8. |

## 4. `20260525` vs `20260525new` diff summary
- **Analyzers are identical** (`diff` of `template_analyzer/analyze_template.py` = 0 lines). Both equal what
  the current project already absorbed (markdown-split robustness, page_type, etc.).
- Divergence is in `core/`:
  - `content_generator.py` (new): **fresh self-designed table headers** — `…自行设计合适的表头（共 N 列），
    不要照搬模板原表头。` (new:396). **Current lacks this** → current still feeds template headers to the LLM.
  - `template_style_engine.py` (new): `_count_actual_lines()` + capacity override (overflow awareness).
    **Current lacks this** (Q3c-3 deferred; the Q3d attempt was reverted).
- Neither package fixes JSON-fence parsing (`chat_structured` is bare `json.loads` in both and in current).

## 5. Current implementation map (key files)
- Outline flow: `web/app.py` `poc_outline` → `_outline_to_cards` → editor → `poc_generate` → `_cards_to_slides`
  → `agent.step_generate_content_and_layout` → `step_normalize_layouts` → `step_render_preview/final` →
  `_run_generation` post-passes (native_chart_rebind T6, `deck_polish.polish_deck`, `typography_polish`,
  contamination scan).
- Content: `core/content_generator.py` (outline + per-slide expand, incl. `table_data` prompt at L464-502),
  `core/content_normalizer.py` (slot/table capacity normalization), `core/template_cloner.py`
  (`clone_and_fill` + `_fill_with_blueprint` + `_fill_table`).
- Polish: `core/deck_polish.py` (agenda fix / numbering strip / placeholder clear), `core/typography_polish.py`.
- Custom: `web/app.py` `_run_custom_analyze` (subprocess full analyze), `_build_template_index`,
  `/api/custom-template/{upload,analyze,status,page-type,reanalyze-page,outline,generate}`.

## 6. job_28 quality baseline analysis
- Body pages are good because the **Q3c-final content path is intact**: per-slot capacity normalization
  without aggressive truncation, no global residue blanking, native table fill from `table_data`.
- **P8/P9 table residue** (`是否模型 / 分析场景 / 模型场景`) traced to source (verified on the t5 analysis,
  template 28): the template's page-8/9 **table headers literally are**
  `['模块层级','分析场景','场景说明','是否模型','分析场景']` (p8) and `['模块层级','分析场景','场景说明','是否模型']`
  (p9) — CMCC/监管 residue captured by the analyzer into `layout_json`/`markdown_content`. Then
  `content_generator.py:489` feeds them to the LLM (`表格表头为: {headers}`) and instructs it to return
  `table_data` with matching headers → the LLM **echoes** the residue headers → `_fill_table` writes them.
  Residue source ranking: **(a) template header [primary] + (c) LLM prompt echo [primary] ; NOT (d) label
  mapping ; (e) only when table_data missing**.
- **Table thinness:** `content_normalizer` caps data rows to `template_rows-1` and `_truncate_cell_text`
  caps cell text to the column's `max_total_chars`. With a small template table, generated rows/cells are
  trimmed → thin. This is **template + capacity** driven, not a Q3d-style regression.

## 7. Remaining gaps to 4.5+
1. Agenda page items ≠ rendered deck agenda (cosmetic but visible). 
2. P8/P9 table-header residue + thin tables.
3. Custom single-page indexing UX (full re-analysis slow; single-page path exists but isn't used to
   "fix one page" in the upload flow).
4. (Lower) No overflow/line-count awareness (some long slots may visually overflow on P4/P6) — template-side.

## 8. Root cause analysis
### 8.1 Agenda mismatch
- Outline items ARE correct (editor + `_agenda_consistency` derive deduped section_titles).
- The **rendered** agenda differs because (i) the agenda slide content is LLM-expanded and **rephrased/
  numbered** ("1 经营概览…"), and (ii) `deck_polish.fix_agenda_slide` only overwrites when it detects a
  **repeated "generic" value** (count≥2) — when items are distinct it does nothing. (iii) The template's
  agenda page has **fewer item slots (3) than sections (5–6)**, so even a correct fill can't show all.
- (iv) Q3d's `fill_agenda_deterministic` *did* fix (i)/(ii) correctly — but Q3d was reverted **as a whole**
  for unrelated reasons, so the agenda gap returned.
- **Min fix:** redo a deterministic agenda fill **scoped to the agenda slide only** (overwrite the agenda
  content-slot shapes from the page blueprint with exact deduped section_titles; clear extras; log overflow
  when sections > slots). **Risk: LOW** if isolated to the agenda slide and not bundled with any global
  cleaner. The slot<section count gap is template-side (document; do not force).

### 8.2 P8/P9 table thinness / residue
- Residue = template header echo (see §6). **Min fix options (pick one, all avoid touching body logic):**
  (a) **Sanitize the table-header hint** at prompt-build (strip known residue tokens / replace with neutral
  `列N` before the `表格表头为:` line) — smallest behavioral change, but edits `content_generator` table
  prompt (medium sensitivity). (b) Adopt Huang-new's **fresh-header instruction** (`不要照搬模板原表头`) —
  also a `content_generator` prompt change. (c) **Targeted post-render table-header clean**: in
  `deck_polish`, replace residue tokens **only in table header cells** of table pages (never body text,
  never whole shapes) — safest re. Q3d, isolated to tables. **Recommend (c) + later (b).** **Risk: MEDIUM.**
- Thinness = template row count + capacity caps → **template-side / accept** for now (do NOT loosen caps
  globally; that risks overflow). **Risk of "fixing" by truncation changes: HIGH → do not.**

### 8.3 Custom single-page indexing
- `_run_custom_analyze` runs the **full** analyzer as a subprocess (`--input … --name …`, timeout 3600s).
  A 12-page master ≈ 3 LLM calls/page + screenshots ≈ **20+ minutes**. The frontend polls `/status` every
  5 s and shows "正在解析母版（{step}）… 数分钟" → **perceived as stuck** because the message under-promises
  the duration. On real failure the subprocess sets `state=failed` with stderr (surfaced) — so it is not a
  silent hang, but there's **no live progress** (only `state`/`step`).
- Single-page CLI/API **work and only touch one row** (Q3c-2, verified). The custom **重新分析本页** button
  is wired to the real API (Q3c-1/Q3c-2). 
- **Min fix:** (i) honest progress messaging / longer-running notice + per-page progress if cheap; (ii)
  confirm subprocess stderr surfaces to the UI on failure; (iii) document that **fixing one mis-detected
  page should use single-page reanalysis, not full re-analyze**. **Scope: custom/analyzer/API only. Risk: LOW.**

### 8.4 Cover/agenda regression risk (why Q3d broke body)
- Q3d bundled: cover targeted fill + deterministic agenda fill + **global `clear_known_residue`** (blanks any
  shape/table cell containing a residue token) + a `chat_structured` JSON-fence/retry change. The **global
  residue cleaner** is the prime suspect for P4/P8/P9 content loss (it blanks legit cells/shapes that contain
  a flagged token, e.g. table cells), and the JSON change may have altered content. **The agenda/cover
  targeted fills themselves are low-risk.** → Future cover/agenda fixes must be **targeted and decoupled**
  from any global cleaner, and must not change `chat_structured`/content prompts unless explicitly scoped.

## 9. Recommended repair plan (NOT implemented this round)
**P0 · Baseline protection**
- Tagging **done** (`poc-4.5-q3c-content-baseline-job28` → `155b760`, pushed).
- Add a **content smoke check** script (read-only, run after any change): generate one 12-page T5; assert
  P4 text ≥ N chars, P8/P9 each have ≥ M non-empty table cells, slide_count==12, opens, contamination only
  documented warnings. Compare against job_28/job_121 thresholds. Block merge if body metrics drop.

**P1 · Agenda-only isolated fix**
- Re-introduce **deterministic agenda fill scoped to the agenda slide** (reuse the reverted
  `fill_agenda_deterministic` logic, agenda-slide-only, blueprint slot refs) + log overflow.
- **Must NOT** touch content_generator / content_normalizer / table fill / body slides / any global cleaner.
- Risk: LOW.

**P2 · P8/P9 table cleanup (residue only)**
- Targeted **table-header residue clean** (replace residue tokens only in table header cells of table pages),
  preserving `table_data`/native table; optionally adopt Huang-new fresh-header instruction later.
- **No** aggressive truncation; **no** global residue cleaner; **no** capacity changes.
- Risk: MEDIUM (validate P8/P9 cell counts unchanged vs baseline).

**P3 · Custom single-page reanalysis fix**
- Fix custom "stuck" perception (progress/messaging + verify failure surfacing); validate single-page CLI+API
  end-to-end; ensure 重新分析本页 refreshes index. Scope: custom/analyzer/API only. Risk: LOW.

**P4 · Overflow/truncation helper**
- **Defer.** Only consider after P0 smoke proves it doesn't thin body content; would touch
  template_style_engine/normalizer (content-critical). Risk: HIGH until proven.

## 10. Explicit do-not-touch list
- **Files:** `core/content_generator.py` (body content + table_data prompt logic), `core/content_normalizer.py`,
  `core/template_cloner.py` (`clone_and_fill` / `_fill_with_blueprint` / `_fill_table` body behavior),
  `core/typography_polish.py`, and `core/deck_polish.py` **body passes** (numbering strip / placeholder clear).
- **Behaviors:** do NOT reintroduce a **global residue hard-clean** (`clear_known_residue`-style) — it caused
  the Q3d regression. Do NOT change `skills/skill_llm/llm_skill.py` `chat_structured` content behavior. Do NOT
  loosen/alter capacity caps or add font shrink. Do NOT change templates or reindex as part of a code fix.
- **Allowed surfaces:** `deck_polish` **agenda-slide-only** fill (P1) and **table-header-cell-only** residue
  replace (P2); `static/templates/custom.html` + custom/API/analyzer layer (P3); a new read-only smoke script (P0).

## 11. Suggested next commit split
1. **P0** `chore(poc): content baseline smoke check` — new read-only validation script + thresholds (no behavior change).
2. **P1** `fix(poc): deterministic agenda-slide fill (isolated)` — `core/deck_polish.py` (+ minimal `web/app.py`
   wiring to pass agenda blueprint slot refs); agenda slide only.
3. **P2** `fix(poc): clean table-header residue only` — `core/deck_polish.py` table-header-cell residue replace
   (+ optional later: Huang-new fresh-header instruction as a separate, gated commit).
4. **P3** `fix(poc): custom single-page reanalysis UX` — `static/templates/custom.html` + custom endpoints/analyzer
   progress + failure surfacing.
Each commit: explicit paths only; run the P0 smoke before/after; no push/deploy until review.

— End review (review-only; no code/DB/template/deploy changes; not committed) —
