# POC 4.5+ Huang — t5 / t6 Stepwise Diagnostic Report

Date: 2026-05-23
Repo: /Users/tylerzhao/Code/pptx-huang-poc
Mode: read-only diagnostic (no code changed, nothing committed)

> NOTE: This run created a local, gitignored `.env` (copied from `.env.example`) so the
> runtime could load LLM + MySQL config. No secrets are reproduced in this report.

## 1. Executive Summary

| Path | Outline (Kimi) | Generation | Output | Status |
|---|---|---|---|---|
| **t5 / business / 商务风格** | OK (77s, 12 pages) | OK (~3 min) | `output/job_56_final.pptx` (2.69 MB, 12 slides) | ✅ PASS end-to-end |
| **t6 / tech_blue / 科技蓝风格** | OK (62s, 8 pages) | OK (~1.5 min) | `output/job_58_final.pptx` (1.46 MB, 8 slides) | ✅ PASS end-to-end |
| **Manual (non-browser) generation** | via curl → localhost API | OK for both | both PPTX open & valid | ✅ PASS |

- **Primary blocker: NONE for runtime generation.** Both built-in templates generate complete, valid, leak-free PPTX through the real Kimi pipeline.
- **Secondary issues (non-blocking, data hygiene):** DB template `file_path` values point at the **old repo** (`ppt-agent-poc`), not this repo; duplicate `商务风格` rows (ids 13/14/15); `data/t5.pptx` in this repo is a 920-byte stub (the real 2.7 MB t5 lives in `templates_storage/` and the old repo). See §8.

## 2. Runtime Config Status

- Runtime loads config from `BASE_DIR/.env` only if it exists (`config/settings.py`).
- Env vars **read by code**: `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_TEMPERATURE`, `MYSQL_HOST/PORT/USER/PASSWORD/DB`, `MERMAID_BIN`. (`KIMI_API_KEY` is present in `.env.example` but **not** read by code — only `LLM_API_KEY` is.)
- On entry `.env` was **missing** → without it `LLM_API_KEY` defaults to empty and all LLM calls fail. Created local gitignored `.env` from `.env.example` to proceed.
- `.env.example` matches runtime needs (superset; extra `KIMI_API_KEY` is harmless/unused).
- DB: **connects OK**, database `pptx_agent`, tables `templates`, `template_pages`, `generation_jobs`.
- Template assets: real t5 (2.7 MB) + t6 (1.48 MB) present in `templates_storage/` and in the old repo path the DB records point to (both exist on disk).

## 3. Template DB / Asset Mapping

`_resolve_template(name)` picks the same-name row with the MOST analyzed pages (tie-break newest id). Relevant rows:

| id | name | pages | file_path |
|---|---|---|---|
| 13 | 商务风格 | 0 | …/ppt-agent-poc/data/pptx_agent_20260521/templates_storage/t5.pptx |
| 14 | 商务风格 | 3 | (same) |
| **15** | **商务风格** | **12** | (same) ← selected for business |
| **16** | **科技蓝风格** | **8** | …/ppt-agent-poc/…/t6.pptx ← selected for tech_blue |

- business → id 15 (12 pages). tech_blue → id 16 (8 pages).
- t5 path (DB): `/Users/tylerzhao/Code/ppt-agent-poc/data/pptx_agent_20260521/templates_storage/t5.pptx` — **exists** (2.69 MB).
- t6 path (DB): same dir `/t6.pptx` — **exists** (1.48 MB).
- Slide counts: t5 = 12 analyzed pages; t6 = 8 analyzed pages.
- 16 template rows total; 12 legacy rows also point at old-repo paths.

## 4. t5 Stepwise Trace (business)

- Outline: `POST /api/poc/outline` → HTTP 200, `source=kimi`, `job_id=55`, 12 cards. 77.0s.
  - Checkpoints: `logs/job_55/{llm_prompt_outline.txt, llm_output_outline.json, selected_template.json}`.
- selected_template: business / 商务风格, file_path → old-repo t5.pptx, page_count 12.
- Generate: `POST /api/poc/generate` → `job_id=56`, `ready=true`, background thread.
- Per-slide generation: prompts + outputs `llm_prompt_slide_1..12.txt` / `llm_output_slide_1..12.json` (+ label batches) all written.
- Layout/normalize: `blueprints.json`, `layouts.json` written (TemplateLayoutMapper + clone path).
- Cloner/render: `render_from_template` used the real template file (path exists) → preview + final.
- Output: `output/job_56_final.pptx` (2.69 MB). Opens OK, **12 slides**. Text scan: 0 hits for Huang/Kimi/job_/template_id/soffice/pypdfium2/sk-/moonshot/localhost.
- Failure point: **none**.

## 5. t6 Stepwise Trace (tech_blue)

- Page guard: `page_count=12` → HTTP 200 `{error, page_count_exceeded, "该模板风格为 8 页"}` (correct; t6 has 8 analyzed pages).
- Outline: `page_count=8` → HTTP 200, `source=kimi`, `job_id=57`, 8 cards. 61.9s.
- selected_template: tech_blue / 科技蓝风格, file_path → old-repo t6.pptx, page_count 8.
- Generate: `job_id=58`, `ready=true`. Per-slide prompts `llm_prompt_slide_1..8.txt` (8) all written.
- Cloner/render: real template file used → preview + final.
- Output: `output/job_58_final.pptx` (1.46 MB). Opens OK, **8 slides**. Text scan: 0 internal-term/secret hits.
- Failure point: **none**.

## 6. Manual Generation Trace (non-browser)

No standalone documented "manual generate" script forces a specific built-in template:
- `main.py` is a CLI (`--auto-confirm`) but uses LLM `step_select_template` (auto-pick), so it is not deterministic for business/tech_blue.
- `core/template_cloner.py` (`TemplateCloner`) and `core/ppt_renderer.py` (`render_from_template`) are the render primitives.

Used path = **curl against localhost API** (Phase 5 "if only API exists" branch):
- Commands: `POST /api/poc/outline` then `POST /api/poc/generate` then poll `GET /api/poc/status/{job_id}` (see §4/§5 payloads). Confirmed-outline-verbatim flow.
- Output: both `job_56_final.pptx` and `job_58_final.pptx` produced and open in python-pptx.
- Failure: none.

## 7. Logs Evidence (local only — not committed)

- Job ids: outline-only 55 (t5), 57 (t6); full generation 56 (t5), 58 (t6).
- Log paths: `logs/job_55/`, `logs/job_56/` (per-slide), `logs/job_57/`, `logs/job_58/` (per-slide).
- Outputs: `output/job_56_final.pptx`, `output/job_56_preview.pptx`, `output/job_58_final.pptx`.
- Key excerpts: outline HTTP 200 `source=kimi`; status terminal `{"state":"done","final_path":...}` for 56 & 58.
- No error excerpts (no failures). No secrets present in outputs (scanned).

## 8. Root-Cause Hypothesis

Generation pipeline itself: **healthy** (env + LLM + DB + template asset + cloner all work). The only real-world fragility classes:

- **env issue (latent):** runtime needs `.env`; a fresh clone has none → LLM calls would fail until `.env` is created. Class: *env issue*.
- **template asset path issue (latent / portability):** all DB `file_path`s point to the **old repo** `ppt-agent-poc`. It works today only because that repo still exists on disk. On a clean machine (or after old-repo removal) render falls back to a non-template build. Class: *template asset path issue*.
- **DB data hygiene (minor):** duplicate `商务风格` rows (13/14/15). Mitigated by `_resolve_template` choosing the 12-page row, so not currently harmful.
- **repo asset mismatch (minor):** `data/t5.pptx` here is a 920-byte stub; real t5 is in `templates_storage/` + old repo. The DB does not use `data/`, so no functional impact now, but it contradicts the "data/t5.pptx" assumption.

Not implicated: LLM issue, selected_template mismatch, TemplateCloner issue, frontend polling, output-opening — all verified OK.

## 9. Recommended Next Action (single minimal fix)

**Re-point the t5/t6 DB `file_path` values to in-repo assets and remove the old-repo dependency** — minimal, surgical:

1. Place the real masters in this repo (they already exist in `templates_storage/t5.pptx` and `t6.pptx`).
2. `UPDATE templates SET file_path = '<repo>/templates_storage/t5.pptx' WHERE id = 15;` and `… t6.pptx WHERE id = 16;` (one-time data fix, with backup; not a code change).

This removes the only deployment-blocking dependency (old-repo absolute paths) without touching code, schema, or the generation pipeline. Defer duplicate-row cleanup, `data/` stub reconciliation, and a template re-import/seed script as separate follow-ups.

— End of report —
