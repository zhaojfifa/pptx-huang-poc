# PR-Q3a Local Validation Report — `page_type` calibration & analyzer robustness

Date: 2026-05-25 · Repo: `/Users/tylerzhao/Code/pptx-huang-poc` · Branch: `main`
**Local validation only.** No commit, no push, no Alibaba Cloud deploy. Live cloud service untouched.
Scope = validate the 4 uncommitted WIP files in place. Companion to
[`poc_4p5_huang_q3a_discovery_plan.md`](poc_4p5_huang_q3a_discovery_plan.md).

## 0. Verdict (TL;DR)
**Q3a passes local validation. RECOMMEND COMMIT of all 4 WIP files, including
`core/content_generator.py`.** Migration is safe/idempotent; analyzer writes correct `page_type`;
T5 generation opens with agenda **pass**; the page_type injection caused **no contamination
regression** (the injected run was *cleaner* than the no-injection control); T6 NULL-fallback and
`/custom` index both work. One **pre-existing, non-Q3a** issue noted: template table-header residue
(`是否模型`) appears in *both* injected and control runs → separate cleanup, not a Q3a blocker.

---

## 1. Current WIP file classification

| File | Change | Class | Validated |
|---|---|---|---|
| `database/db.py` | `page_type VARCHAR(50) NULL` DDL + duplicate-tolerant `ALTER` migration + `TemplatePageDAO.create(page_type=)` | Low-risk additive | ✅ §2 |
| `template_analyzer/analyze_template.py` | robust `split_markdown_by_slide` (prefix + dup-append) · `enable_thinking=False` on vision/style/hints · classify+persist `page_type` via project's own `page_type_prompt` | Low-risk additive | ✅ §3 |
| `web/app.py` | `_build_template_index`: prefer persisted `page_type`, runtime fallback when NULL | Low-risk read-path | ✅ §6 |
| `core/content_generator.py` | `generate_slide_content`: prefer persisted `page_type` for the page-type guidance prompt block; runtime fallback when NULL (`isinstance(template_page, dict)` guarded) | **Gated** (touches generation prompt path) | ✅ §4, §7 |

> `core/content_generator.py` also carries the already-committed `_safe_text` hotfix (5efc575); only the
> page-type routing block is uncommitted here.

---

## 2. DB migration result

Local DB `pptx_agent` @ 127.0.0.1. Validated both paths, then restored test data:

- **Idempotent no-op:** column already present → `init_db()` re-run = `Database initialized.`, **no
  duplicate-column error** (duplicate-tolerant `except` path works).
- **Auto-create:** dropped the column → `init_db()` → log `Added page_type column to template_pages.`
  → column present again. ✅
- **Lossless:** the 3 pre-existing non-NULL test rows (cover/agenda/closing) were backed up and
  restored. Final distribution unchanged: 296 NULL + 1 cover + 1 agenda + 1 closing.

**Backward compatible:** existing rows keep NULL and remain valid; no wipe/reseed/re-index needed.

---

## 3. page_type write result (analyzer)

Ran `analyze_template --input templates_storage/t5.pptx --name q3a_t5_validate` → **template id 28**,
12 pages, all 3 LLM calls/page with `enable_thinking=False`, screenshots via LibreOffice OK.

**page_type written for all 12 pages:**

| page | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| page_type | cover | agenda | content | content | content | content | content | **table** | **table** | content | content | closing |

- Structural roles {cover, agenda, content, table, closing} all detected. **No `chart`** — expected
  (chart is an outline-time distinction, not derivable from a static template page; the canon map
  intentionally omits it).
- **Old NULL rows unaffected:** template id 24 (prior T5) still all-NULL, `get_by_template(24)` reads
  fine; read path uses persisted when present, runtime classify when NULL. ✅

---

## 4. T5 generation result

Driven end-to-end (outline→content→layout→render→final) on the **page_type-populated** template 28
(`_resolve_template` tie-breaks to newest id among equal page counts → 28), doc = baosteel 2025 example.

- **job_id = 101** · output `output/job_101_final.pptx`
- **Opens:** ✅ 12 slides (python-pptx load OK).
- **Agenda consistency:** `overall_status = "pass"` — 5 agenda items, all slides mapped via
  `section_id`, **0 unmatched, 0 drifted, 0 unsupported items**. No degradation.
- **page_type injection exercised + correct:** all 12 slide prompts carry the `=== 页面类型指引 ===`
  block, differentiated by persisted type — e.g. slide 1 →「封面」, slide 2 →「目录/章节」, slide 8 →
  「表格」(forces `table_data`), slide 12 →「尾页」. Confirms the persisted value drives guidance.
- **Contamination:** `clean=false`, total_hits=2 — both `是否模型` in **table header cells** (slides
  8 & 9, `表格占位符 5` / `表格 12`). All text frames clean. See §4.1.

### 4.1 Is the contamination caused by the page_type injection? — Control proves NO
Ran an identical generation against the **old** template 24 (NULL page_type → runtime classify, **no
persisted injection**) as a control:

| Run | template | page_type path | Opens | Agenda | Contamination |
|---|---|---|---|---|---|
| **job 101** (D) | 28 | persisted injection | ✅ 12 | **pass** | **2** (`是否模型`×2, table headers only) |
| **job 102** (control) | 24 | runtime, no injection | ✅ 12 | **pass** | **14** (`穿透式监管`×11, VPN, SD-WAN, `是否模型`×1) |

- The page_type-injected run is **cleaner**, not worse → the injection introduces **no contamination
  regression**.
- `是否模型` appears in the control too (whose stored markdown does *not* contain it) → it is
  **cloned-template-file table-header residue** from `t5.pptx`, **independent of page_type / the
  analyzer change**. The control's extra `穿透式监管/VPN/SD-WAN` hits sit in uncleaned title/subtitle/
  rectangle/textbox shapes (template label residue), dominated by the *older* analysis metadata +
  LLM sampling — not by anything Q3a touches.

**Caveat (honest):** neither T5 run reached contamination=0 in this fresh local reproduction. The
residual `是否模型` table-header residue is a **pre-existing** cleanup gap (table de-brand on header
cells), **out of Q3a scope** — log as a separate follow-up; it does not block Q3a.

---

## 5. T6 smoke result

`templates_storage/t6.pptx` is **missing locally**, so a full T6 generation (which clones the source
pptx) is not possible here → did the API/resolve/index smoke (allowed fallback).

- `_resolve_template("科技蓝风格")` → **id 23**, 14 pages, all `page_type = NULL`.
- **page_type read path on all 14 NULL T6 pages:** no error; every page resolves a type via runtime
  classify fallback. ✅ (This is the key Q3a guarantee for T6 — NULL never breaks read.)
- `_build_template_index("科技蓝风格")` → 14 pages, badges rendered via fallback (封面/目录/章节/正文/表格). ✅
- **Not validated locally:** full T6 PPTX render (no source pptx). Recommend a T6 end-to-end run on an
  environment that has `t6.pptx` before relying on T6 in production with Q3a.

---

## 6. /custom index result

- Direct `_build_template_index(...)`:
  - Populated template (id 28): badges from **persisted** page_type → 封面/目录/章节/正文/表格.
  - NULL custom template (`客户母版-custom_cleanT5-8357`): badges from **runtime fallback**, no error.
- HTTP (uvicorn on :8077): `GET /` → **200**, `GET /custom` → **200**, `/custom` HTML contains the
  `page_type` badge markup, **no server startup errors**. Page loads and the read-only badge does not
  break rendering. (Edit UI intentionally out of scope — Q3c, not this round.)

---

## 7. Should `core/content_generator.py` ship with Q3a?

**Yes — recommend including it.** Evidence:
1. Injection path verified active and **faithful** to persisted page_type (per-type guidance, §4).
2. **No agenda regression** (pass) and **no contamination regression** (cleaner than the no-injection
   control, §4.1).
3. NULL→runtime fallback preserved and guarded (`isinstance(template_page, dict)`), so any
   not-yet-classified template behaves exactly as today.

Residual risk is low and bounded: persisted page_type only changes *which guidance text* is injected;
it cannot fabricate output strings. The classifier being heuristic means a wrong persisted value
yields slightly-off guidance, not a crash — and is correctable later via a manual-edit path (Q3c).

---

## 8. Commit recommendation

**RECOMMEND COMMIT** — all 4 files as one isolated PR-Q3a commit, **explicit paths only**:
```
git add core/content_generator.py database/db.py \
        template_analyzer/analyze_template.py web/app.py
```
Also commit the two review docs (`poc_4p5_huang_20260525_delta_review.md`,
`poc_4p5_huang_q3a_discovery_plan.md`, and this report) as docs, separately.

**Do NOT** `git add -A` / `git add .` (see §9). **Hold** as separate non-Q3a follow-ups: (a) table
header de-brand for `是否模型`; (b) a T6 end-to-end run once `t6.pptx` is available.

*Awaiting human go/no-go before any commit — no commit performed in this round.*

---

## 9. Pre-commit safety scan

- `git status` before commit: 4 modified tracked files + untracked `.zshrc`,
  `data/pptx_agent_20260525/`, and the docs. **Staging area empty.**
- **`.gitignore` already covers:** `.env`/`.env.*`, `logs/`, `output/`, `output/*.pptx|*.png`,
  `templates_storage/`, `static/previews/`, `__pycache__/`, `data/*.pptx`, `data/**/*.pptx`,
  `*.sqlite*`. The nested `data/pptx_agent_20260525/.env` **is** ignored; its `*.pptx` are ignored.
- ⚠️ **NOT ignored:** `data/pptx_agent_20260525/` source tree (43 non-ignored files, e.g.
  `web/app.py`, `config/settings.py`, `*.py`) **and** `.zshrc`. A `git add -A` **would stage all 43 +
  `.zshrc`** → use explicit paths only. **Recommend** adding `/.zshrc` and
  `/data/pptx_agent_20260525/` to `.gitignore` before any broad add (optional, not done this round).
- Generated validation artifacts (template id 28 row; jobs 101/102; `output/job_10{1,2}_final.pptx`;
  `logs/template_screenshots_28/`, `logs/job_101`, `logs/job_102`) are **local-only and gitignored**
  (`output/`, `logs/`). They will **not** be committed. Note: template id 28 now exists in the local
  DB and is the newest `商务风格`, so local generations resolve to it; harmless locally, drop the row
  if you want local T5 to resolve back to id 24.

---

## 10. Recommended next command / next task
1. Human **go/no-go** on the §8 commit (incl. whether `content_generator` ships now — recommended yes).
2. On GO: explicit-path commit of the 4 files + docs; optionally tighten `.gitignore` first.
3. Separate backlog (not Q3a): table-header de-brand for `是否模型`; T6 end-to-end with `t6.pptx`.

— End local validation report (no commit / push / deploy performed) —
