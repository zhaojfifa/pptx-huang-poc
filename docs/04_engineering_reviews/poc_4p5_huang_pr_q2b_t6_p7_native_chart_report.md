# PR-Q2B — T6 P7 Native Chart Mode Verification

Date: 2026-05-24 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Scope: T6 / P7 only. No external chart skill, no matplotlib/PNG, no old-mainline code, no t5
change, no prompt work, no DB pruning, no deploy, nothing committed.

## Verdict (core feasibility): **GO — native chart clone + replace_data rebind works**

The updated T6 master (`data/t6.pptx`, 14 slides, today) has P7 as **6 native
COLUMN_CLUSTERED charts with embedded workbooks**. They clone 1:1 and `replace_data()`
updates all 6 cleanly while keeping them native and styled. Two operational follow-ups
remain before t6 is live (re-index timed out; rebind not yet wired into the pipeline).

## Task 1–2 · Adopt + re-index T6 — ⚠️ BLOCKED by LLM API timeouts

- Latest master = `data/t6.pptx` (1,737,559 bytes, 14 slides, 6 embedded workbooks).
- The analyzer **copied it into `templates_storage/t6.pptx`** (file adopted ✓, now 14 slides).
- The analyzer then **stalled and failed on LLM API timeouts** (vision OK pages 1–6, then
  `generation_hints page 6: Request timed out`; multi-hour stalls overnight). Run aborted.
- It left a **partial junk row id 22 (6/14 pages)**. Per instruction, DB rows were NOT pruned.
- **Resolution mismatch:** `_resolve_template("科技蓝风格")` still picks **id 20 (13 pages,
  built from the previous 13-slide master)**, while `templates_storage/t6.pptx` is now the
  new 14-slide file. So t6 is currently inconsistent (file ≠ index) — **t6 generation should
  not be run until the re-index completes.** (t5 untouched; t6 is not the live POC path.)
- New template_id / page count / screenshots / vision / resolution: **not confirmable** —
  re-index did not complete. This is an **infra (LLM API) blocker**, not a chart-feasibility
  blocker.

## Task 3 · P7 chart inspection (on the new master, direct)

- **Native chart?** Yes — **6 chart objects**, all `COLUMN_CLUSTERED`, **3 series** each,
  single category each (覆盖企业 / 派发任务 / 设计表单 / 采集数据 / 生成指标 / 主题大屏).
- **python-pptx detection?** Yes (`shape.has_chart`, `shape.chart.chart_type`).
- **Embedded workbook?** **Yes** — `ppt/embeddings/Microsoft_Excel____*.xlsx` (6 workbooks)
  back the P7 charts. (Package has 8 chart parts total; the 2 extras `chart7/8` elsewhere
  still carry the OLD external link `file:///D:\…\优秀智能体、模型清单.xlsx` → residue to clean.)
- **External links on P7 charts?** No — P7's 6 charts use embedded workbooks. (External link
  remains only on the 2 leftover non-P7 chart parts.)
- **Inside a group?** No — the 6 charts are top-level shapes on the slide.

## Task 4 · Clone preservation — ✅

- Cloned the master (cloner step = file copy; charts are graphicFrames the cloner never
  mutates). Output P7 retains **all 6 charts**, type `COLUMN_CLUSTERED`. Style/colors chart
  parts unchanged. Position/axes/legend preserved (charts untouched by text/table fill).
- Evidence: `/tmp/q2b_clone.pptx`.

## Task 5 · Native rebind — ✅ replace_data works

Test dataset: Q1–Q4; 营业收入 728.8/784.9/810.6/850.7; 归母净利润 24.3/24.5/30.8/23.9.

- `chart.replace_data(CategoryChartData)` on each P7 chart → **ok=6, fail=0** (embedded
  workbooks present, so the external-link failure seen in PR-Q2A is gone).
- Re-open verification: categories `['Q1','Q2','Q3','Q4']`, series `营业收入`+`归母净利润`
  with correct values, `chart_type` still `COLUMN_CLUSTERED` (**remains native/editable**).
- **Style/colors parts preserved** (unchanged); **embeddings still 6** after rebind.
- Evidence: `/tmp/q2b_rebind.pptx`. (Cache-XML fallback NOT needed here.)

## Task 6 · Generation smoke — ⚠️ NOT run

- Depends on a completed t6 index (Task 2) and per-slide LLM content generation — both gated
  by the same LLM API instability. Deferred until the API is stable and the re-index lands.
- Note: even when run, the current `TemplateCloner` **clones** P7 charts (preserved with the
  master's embedded data) but does **not rebind** chart data — native rebind is not yet wired
  into the generation pipeline (that is the implementation PR, not this verification).

## Evidence summary

- `/tmp/q2b_clone.pptx` — 6 P7 charts preserved (native, COLUMN_CLUSTERED).
- `/tmp/q2b_rebind.pptx` — 6 P7 charts rebound via `replace_data` (Q1–Q4, 2 series, native,
  styles preserved). Real-PowerPoint render not verified on this machine — **Jackie should
  open `/tmp/q2b_rebind.pptx` in PowerPoint to confirm the bars display the new values.**

## Final answers

- **Is P7 a native chart?** Yes — 6 native COLUMN_CLUSTERED charts (3 series each).
- **Embedded workbook or external link?** **Embedded** for all 6 P7 charts (external link
  remains only on 2 leftover non-P7 chart parts → de-brand later).
- **Can it be cloned 1:1?** Yes — fully preserved, styles/axes/legend/position intact.
- **Can data be replaced natively?** **Yes** — `replace_data` succeeds on all 6, chart stays
  native and styled. (No cache-XML hack required.)
- **Ready for POC path?** Chart mechanism: **yes (GO)**. Not yet end-to-end because (a) the
  t6 re-index timed out (LLM API), leaving file≠index, and (b) rebind isn't wired into
  generation.
- **Next minimal fixes:**
  1. **Re-run the T6 analyzer when the LLM API is stable** to finish indexing the 14-slide
     master (then resolution points at a 14-page clean index). Retry-on-timeout would help.
  2. **Minimal `native_chart_rebind` in the clone/generation path** using `replace_data`
     (embedded-workbook charts); single-series and multi-series both supported by the API.
  3. **De-brand the 2 leftover external-link chart parts** (`chart7/8`, the `D:\…xlsx` ref).

## State note (uncommitted, no artifacts committed)
- `templates_storage/t6.pptx` now = new 14-slide master (file adopted); index incomplete →
  t6 generation paused until re-index completes. Partial row id 22 (6 pages) left in DB
  (not pruned, per instruction). Resolution still = id 20 (old 13-page index).
- Nothing committed; no PPTX/log/output committed; t5 untouched.

— End PR-Q2B —
