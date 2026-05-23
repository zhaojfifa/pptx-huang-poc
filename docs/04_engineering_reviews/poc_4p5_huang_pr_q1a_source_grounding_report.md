# PR-Q1a — Source Document Grounding Report

Date: 2026-05-23 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Status: **complete, uncommitted** (commit pending Jackie/arbitrator diff confirmation).
Scope kept tight: source grounding only — no line chart, no t6 work, no forbidden-term hard
fail, no slot-fragmentation gate, no DB cleanup beyond Q0, no deployment.

## Problem (from O2)

The biggest quality gap: in practice the source document never reached Kimi.
- **upload mode**: the frontend sent only the *filename*; file content was discarded.
- **example mode**: `_source_markdown` read `logs/job_62/document_markdown.md`, which did
  **not exist** → empty.
- **generate step**: didn't pass `input_mode` at all → empty even when outline had a doc.

Result: outline + per-slide content were written from the prompt + key_points alone.

## Changes

1. **Bundled example doc** — `data/samples/baosteel_2025_example.md` (real, structured
   content; figures are clearly-labelled sample data). `_EXAMPLE_DOC` now points here
   (legacy checkpoint kept as fallback). The *default* flow is now grounded out of the box.
2. **Real upload path** — new `POST /api/poc/source/upload`: saves the file, parses it to
   markdown via `DocumentProcessor` (markitdown), caches it by `source_token`, returns
   `{source_token, markdown_chars, key_facts}`. Frontend `pickUpload` now actually uploads
   the file, stores the token, and shows parse status; `source_token` is sent in both the
   outline and generate payloads.
3. **Compact source blocks** — `_ground_doc()` prepends an auto-extracted
   `关键事实/数据` block (`_extract_key_facts`, no-LLM regex over numbers/%/¥/同比) to the
   document. This distilled-metrics block + the full doc feed the existing
   `summarize_document` (doc_summary) and `_extract_relevant_doc` (per-slide relevant doc).
4. **Injection** — `doc_md` already flows into `generate_outline` and, via
   `_run_generation`, into `step_generate_content_and_layout` → per-slide prompts. Added
   `input_mode` to the generate payload so the generate step grounds too.
5. **Logging** — outline/generate log `input_mode / token / raw_chars / grounded_chars /
   key_facts`; `content_generator` logs per slide `doc_present / relevant_chars /
   summary_chars`.

Files: `web/app.py`, `static/templates/index.html`, `core/content_generator.py`,
`data/samples/baosteel_2025_example.md`.

## Verification (live, example mode, t5/business)

- Outline grounding log: `Job 61: source grounding — input_mode='example' token=no
  raw_chars=899 grounded_chars=1361 key_facts=12`.
- Per-slide log (all 12): `Slide N source context — doc_present=True relevant_chars=1361
  summary_chars=1361`.
- Generation: job_62 → `state=done`, `output/job_62_final.pptx`, 12 slides, opens OK.
- Upload endpoint smoke: `POST /api/poc/source/upload` (sample md) →
  `{status: ok, markdown_chars: 970, key_facts: 12}`, token returned.

### Grounded (job_62) vs ungrounded (job_56)

Source-doc-specific facts present in the final PPTX:

| Fact set (10 markers: 3,612 / 198 / 5,180 / 2,340 / 湛江 / 硅钢 / 梅山 / 45亿 / 42% / 降本) | job_62 (grounded) | job_56 (ungrounded) |
|---|---|---|
| hits | **10 / 10** | 7 / 10 |

job_62's figures are now traceable to the provided document (e.g. 营收 3,612 亿、净利 198
亿、产量 5,180 万吨、铁水成本 2,340 元/吨、硅钢二期 45 亿). job_56's overlapping numbers were
the model's own priors (some coincide, some fabricated), not sourced.

## Acceptance

| Criterion | Result |
|---|---|
| uploaded/selected source parsed into markdown | ✅ (upload endpoint + bundled example) |
| compact source blocks: markdown / summary / key_facts / metrics | ✅ (`document_markdown.md` checkpoint, summarize_document, `关键事实/数据` block) |
| injected into outline prompt | ✅ (grounding log; outline reflects doc structure) |
| injected into per-slide prompts | ✅ (per-slide `doc_present=True` logs) |
| logs show source present / md non-empty / summary non-empty / per-slide context | ✅ |
| rerun business/t5 | ✅ job_62 |
| less generic / more business-specific | ✅ 10/10 vs 7/10 source facts, real figures |
| old-template contamination not worse | ✅ job_62 clean (no `穿透式监管`, no Kimi/Huang/sk-/old-path leakage) |
| PPTX opens | ✅ 12 slides |

## Out of scope (unchanged, by instruction)

Line chart, t6 quality, forbidden-term hard fail, slot-fragmentation gate, DB cleanup
beyond Q0, deployment. The unmapped-slot contamination class (O1 §8) remains a later
integrity-gate PR (it was clean in job_62 but is non-deterministic).

## Working-tree state (uncommitted)

- Modified: `web/app.py`, `static/templates/index.html`, `core/content_generator.py`,
  `.env.example` (Q0), `.gitignore` (Q0).
- New: `data/samples/baosteel_2025_example.md`, `scripts/migrate_template_paths.py` (Q0),
  `docs/04_engineering_reviews/*`.
- HEAD unchanged `1ec8a9f`; nothing committed.

— End PR-Q1a —
