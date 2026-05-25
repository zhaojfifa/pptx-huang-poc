# PR-Q3a Discovery Plan — `page_type` calibration & analyzer robustness absorption

Date: 2026-05-25 · Repo: `/Users/tylerzhao/Code/pptx-huang-poc` · Branch: `main`
**Read-only discovery.** No code/DB/template/deployment changed; no commit; no push. The live
service (Alibaba Cloud, T5 main / T6 backup / `/custom` flow) is the superset and source of truth.
This plan supersedes nothing in
[`poc_4p5_huang_20260525_delta_review.md`](poc_4p5_huang_20260525_delta_review.md); it extends it
with the **current uncommitted WIP** (which the prior review predates).

---

## 1. Executive verdict

**GO** for finishing and gating the **already-started PR-Q3a WIP** (page_type column + writer +
read-path + analyzer robustness). It is a clean, additive, backward-compatible slice that does
exactly what this task targets and is mostly already implemented in the working tree.

**Key correction to the prior delta review:** the prior review concluded "`page_type` is half-wired
— the analyzer never writes it." That is no longer true for *this* repo. The **uncommitted WIP has
wired the writer**, using the project's *own* `core/page_type_prompt.classify()` (no LLM, no
dependency on the Huang branch's logic) mapped to a canonical set. So the capability is functionally
present locally; it just needs validation + a commit decision.

**HOLD / net-new (not free to absorb):**
- **Single-page re-analyze** (`--template_id N --page_number K`) — *not* in current; exists in Huang
  and is a genuine absorb candidate (focus point #4).
- **Manual page_type correction UI** on `/custom` — *not present in either tree*; display-only today.
  Net-new if wanted (focus point #3).
- **`chart` page type** — not classifiable from a static template page; outline-time only.
- **JSON-fenced response hardening** — *absent in both trees*; net-new, not an absorb.

**NO-GO** (unchanged): whole-tree replacement, Huang `web/app.py`/frontend, Huang's simplified
`content_generator` outline (drops agenda binding + page_type injection), the out-of-band
`pagetype LONGTEXT` column.

---

## 2. Current repo state

```
git branch --show-current   → main
git log --oneline -5        → 5efc575 (HEAD) fix(poc): coerce LLM JSON fields to string before lower/strip
                              4c9ef81 (origin/main) docs(poc): add deployment readiness checklist
                              13bd8b0 fix(poc): custom template index decode and closure baseline
                              48769b7 feat(poc): clean t5 residue and align tables
                              f0d8e9e docs(poc): record final t5 t6 baseline reproduction
```
HEAD is **1 commit ahead of `origin/main`** (`5efc575`, the safe_text hotfix — already pushed in the
prior session; treat as published).

`git status --short`:
```
 M core/content_generator.py
 M database/db.py
 M template_analyzer/analyze_template.py
 M web/app.py
?? .zshrc
?? data/pptx_agent_20260525/
?? docs/04_engineering_reviews/poc_4p5_huang_20260525_delta_review.md
```
`git diff --stat`: 4 files, +76 / −18 (db.py +25/−4, analyze_template.py +43/−5, content_generator.py
+21/−5 leftover, web/app.py +5/−1).

---

## 3. Existing WIP classification

The four modified files are **one coherent PR-Q3a slice** (page_type) plus the residue of a prompt
change. They are *not* "the Huang big engineering" — they re-implement the capability against this
repo's own modules.

### A. Useful for this task — the page_type slice (additive, backward-compatible)
| File | Change | Risk |
|---|---|---|
| `database/db.py` | `page_type VARCHAR(50) DEFAULT NULL` in DDL + duplicate-tolerant `ALTER TABLE ... ADD COLUMN` migration + `TemplatePageDAO.create(page_type=None)` | **Low** — nullable/additive; same pattern as the existing `generation_hints` migration; existing rows id23/24/26 stay NULL and valid |
| `template_analyzer/analyze_template.py` | (a) robust `split_markdown_by_slide()` — keep pre-first-marker prefix, append duplicate markers; (b) `enable_thinking=False` on vision/style/hints LLM calls; (c) classify `page_type` via `core.page_type_prompt.classify()` → `_PAGE_TYPE_CANON` → persist through `create(page_type=)` | **Low–med** — (a)(b) pure robustness/cost wins; (c) only fills a previously-NULL column |
| `web/app.py` | `_build_template_index`: prefer persisted `page_type` (human-calibratable) over runtime classify; falls back when NULL | **Low** — single read-path line; behavior identical when column is NULL |

### B. Useful but must be GATED — the prompt-routing leftover
| File | Change | Risk |
|---|---|---|
| `core/content_generator.py` | `generate_slide_content` prefers `template_page["page_type"]` over runtime `ptp.classify()` for the **page-type guidance prompt block** | **Medium** — this touches the **generation prompt main path**, which the task says not to alter (`不改 prompt 主逻辑`). Behavior is identical while the column is NULL, but once populated it changes which guidance text is injected. Validate on one T5 + one T6 before committing. Safe-guarded by `isinstance(template_page, dict)`. |

> Note: `core/content_generator.py` already carries the **committed** `_safe_text` hotfix (5efc575);
> the only *uncommitted* part is the page-type routing block above.

### C. Must preserve (do not let absorption remove)
Untracked but valuable: `docs/04_engineering_reviews/poc_4p5_huang_20260525_delta_review.md` (the
prior review) — should be committed as documentation. Committed capabilities that must survive any
absorption: `core/page_type_prompt.py`, `core/deck_polish.py`, `core/typography_polish.py`,
`core/native_chart_rebind.py`, `static/templates/custom.html`, and the web helpers
(`_agenda_consistency`, `_outline_quality_gate`, `_final_contamination_scan`,
`_build_template_index` decode fix). None are touched by the WIP — confirmed.

### D. Must NOT commit
- `.zshrc` — personal shell config, unrelated to the repo.
- `data/pptx_agent_20260525/` — the entire Huang snapshot (large; contains `.env`, PPTX/PNG, logs,
  templates_storage, uploads). Per constraints, never commit. Recommend adding to `.gitignore`.
- Any `output/` / `*.pptx` / `*.png` / `logs/` / `templates_storage/` artifacts.

---

## 4. Huang `20260525` delta summary (focus dirs only)

`data/pptx_agent_20260525` is a **leaner, divergent branch**, not a newer superset. Confirmed by
file-level diff against `database/`, `template_analyzer/`, `web/`, `core/`, `static/templates/`:

- **`web/app.py`**: 218 lines (Huang) vs 1076 (current). Huang is **missing** all `/api/poc/*` and
  `/api/custom-template/*` endpoints, the custom UI, and the web quality helpers. ❌ do not absorb.
- **`static/templates/`**: Huang has **no `custom.html`**; its `index.html` is a minimal form. ❌
- **`core/`**: current has 4 modules Huang lacks (`page_type_prompt`, `deck_polish`,
  `typography_polish`, `native_chart_rebind`). `agent.py`, `content_generator.py`,
  `content_normalizer.py`, `template_style_engine.py` differ.
- **`database/db.py`**: Huang has `page_type` column **but no writer** (its analyzer omits it) — the
  current WIP is *ahead* here (writer wired). Huang additionally has
  `TemplatePageDAO.update_by_template_page()` (current lacks it).
- **`template_analyzer/analyze_template.py`**: Huang has `regenerate_single_page(template_id,
  page_number)` + `--template_id/--page_number` CLI + uses `update_by_template_page` +
  `skill_ppt_screenshot.export_single_slide()`. **Current lacks all of these.**
- **`core/agent.py`**: Huang adds a *job-level* `regenerate_single_page(job_id, page_number)` (debug
  re-gen of one slide from checkpoints) + an extended `_render_with_template(..., slides_data,
  blueprints)` signature.
- **`core/content_normalizer.py`** (24-line delta): Huang adds single-line "title + bullets merge"
  handling when a slot is 1-line but original text was long. Small quality tweak.
- **`skills/skill_llm/llm_skill.py`**: **identical** `chat_structured` — bare `json.loads(raw)`, no
  fence stripping in *either* tree. JSON-fence hardening is net-new, not an absorb.
- **`SameFileError`**: already handled in current (`analyze_template.py` L510–517 reuse-if-same).

---

## 5. Absorb candidates (ranked)

1. **[Already in WIP — finish + gate] page_type column + writer + read-path + analyzer robustness**
   (WIP buckets A & B). Lowest effort, highest fit. Just needs validation + commit decision.
2. **[Net absorb] Single-page template re-analyze (focus #4)** — port from Huang:
   `regenerate_single_page(template_id, page_number)`, `--template_id/--page_number` argparse,
   `TemplatePageDAO.update_by_template_page()`, `skill_ppt_screenshot.export_single_slide()`. Must
   also persist `page_type` in the update path. Medium effort; isolated to analyzer + DAO + screenshot
   skill (no web/generation change).
3. **[Optional] content_normalizer single-line merge tweak** — small, but A/B against current T5/T6
   first (touches slot text layout).
4. **[Optional, debug-only] job-level `agent.regenerate_single_page(job_id, page_number)`** — useful
   for iterating one slide without a full re-gen; isolated; only needed if you want content-level
   (not template-level) single-page iteration.

---

## 6. Do-not-absorb list

- Huang `web/app.py` (regresses the live product surface) and `static/` frontend.
- Huang's simplified `content_generator` outline path (drops agenda binding + page_type_prompt
  injection → topic-drift regression on T5).
- The out-of-band `pagetype LONGTEXT` column (architect's manual DB experiment, not in code).
- Huang's "self-designed table headers" prompt change — current solves residue differently (Q2I
  de-brand + Q2G centering); only adopt after explicit A/B.
- Wholesale copy of `data/pptx_agent_20260525/` into the repo or git.
- Anything that removes `page_type_prompt` / `deck_polish` / `typography_polish` /
  `native_chart_rebind` / agenda guard / contamination scan / custom upload flow.

---

## 7. Minimal implementation proposal (NOT executed this round)

**PR-Q3a (commit the WIP, gated):**
1. Validate the 4 WIP files on **one fresh small template analyze** + **one T5** + **one T6**
   generation. Confirm: file opens, agenda pass, contamination 0, page_type populated as expected,
   no slot-fragmentation regression. Diff md-split output before/after.
2. Commit **only** the 4 WIP files (db.py, analyze_template.py, web/app.py, content_generator.py
   page-type block) as one isolated PR. Keep `.zshrc` and `data/pptx_agent_20260525/` out (add to
   `.gitignore`). Commit the prior delta-review doc separately as docs.
3. Decide whether the `content_generator` page-type routing block ships now or waits — it is the only
   piece touching the generation prompt path.

**PR-Q3b (single-page re-analyze, separate, after Q3a):** port candidate #2 from §5 as an isolated
analyzer/DAO/screenshot change. No web or generation-path edits.

**PR-Q3c (optional, only if product wants it): page_type manual-correction UI** on `/custom` —
net-new: an edit endpoint writing via `update_by_template_page(page_type=...)` + an editable badge in
`custom.html`. Requires a small new API surface; out of scope for a "minimal" round.

---

## 8. Risks

- **Generation prompt path (WIP bucket B):** populating `page_type` changes injected guidance via
  `content_generator`. Mitigate by validating on T5+T6 and keeping NULL→runtime fallback (already
  present).
- **Classifier accuracy:** `page_type_prompt.classify()` is heuristic; a wrong persisted value is
  *worse* than runtime classification because it's authoritative. → needs the manual-correction path
  (Q3c) before relying on it for calibration, or hand-verify after analyze.
- **`chart` gap:** canonical map produces {cover, agenda, content, table, closing} — no `chart`
  (outline-time only). Focus #2 cannot be fully satisfied from static template analysis.
- **Accidental scope creep:** the `data/pptx_agent_20260525/` snapshot is untracked and easy to
  `git add -A` by mistake — guard with `.gitignore`.

---

## 9. Required manual decisions

1. **Commit the WIP page-type slice now, or keep validating?** (deployment is live; this is additive.)
2. **Ship the `content_generator` page-type routing block** (touches generation prompt) — yes/no/defer.
3. **Do you want single-page re-analyze (Q3b)?** It's the literal command in focus #4 but is net-new
   porting work, not yet present locally.
4. **Do you want a page_type editing UI on `/custom` (Q3c)?** Display exists; edit does not, in either
   tree. Confirms focus #3 = net-new feature, not an absorb.
5. **`chart` page type** — accept the {cover/agenda/content/table/closing} set, or require chart
   detection (would need outline-time or heuristic signals)?
6. **content_normalizer single-line merge** — A/B and adopt, or skip?

---

## 10. Recommended next command / next task

**Stop here for human confirmation** (per instructions). When approved, the recommended first
*executable* step is the gated validation in §7.1 — re-analyze one small throwaway template and run
one T5 + one T6 generation against the WIP, *without committing*, e.g.:

```bash
# (illustrative — run only after approval; uses a throwaway template, no T5/T6 re-index)
.venv_huang/bin/python -m template_analyzer.analyze_template --input <small_test.pptx> --name "q3a_validate"
# then a normal T5 + T6 generation and inspect page_type population + agenda/contamination gates
```

Single-page re-analyze (`--template_id 5 --page_number 3`) is **not yet wired in this repo** — it
would be PR-Q3b, a separate approved task, not part of this validation.

— End discovery plan (read-only; no code/DB/template/deploy changes; not committed) —
