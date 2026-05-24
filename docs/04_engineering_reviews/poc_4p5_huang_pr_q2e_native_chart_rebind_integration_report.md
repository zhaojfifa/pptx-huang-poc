# PR-Q2E — Native Chart Rebind Integration (T6 P7)

Date: 2026-05-24 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Scope: integrate native PowerPoint chart `replace_data` rebind for **T6 P7 only**. No
matplotlib/SVG/PNG skill, no cloner redesign, T5 untouched.

## Implementation

- New module **`core/native_chart_rebind.py`** → `rebind_native_charts(pptx_path,
  categories, series, only_slide_numbers)`:
  - iterates slides/charts of an already-rendered .pptx; for each native chart calls
    `chart.replace_data(CategoryChartData)` (preserves style / axes / legend / colors /
    position).
  - charts whose data is an **external link** raise `ValueError(... external)` and are
    **safely skipped** → effectively "apply only when an embedded workbook exists".
  - returns stats: `charts_total / rebound / skipped_external / errors / slides`.
- Wired into **`web/app.py` `_run_generation`** right after `step_generate_final`:
  - **gated to T6**: only runs when `template.name == "科技蓝风格"`.
  - restricted to **P7** (`only_slide_numbers=[7]`).
  - deterministic dataset: categories `Q1..Q4`; series `营业收入 (728.8,784.9,810.6,850.7)`,
    `归母净利润 (24.3,24.5,30.8,23.9)`.
  - writes `logs/job_xx/native_chart_rebind_report.json`; result added to status response.

## Validation — T6 generation (job 83)

| Check | Result |
|---|---|
| final PPTX opens | ✅ `output/job_83_final.pptx`, 14 slides |
| P7 charts native | ✅ 6 native `COLUMN_CLUSTERED` charts |
| P7 data = deterministic test values | ✅ cats `['Q1','Q2','Q3','Q4']`; series `营业收入 [728.8,784.9,810.6,850.7]`, `归母净利润 [24.3,24.5,30.8,23.9]` |
| rebind stats | `charts_total 6, rebound 6, skipped_external 0, errors 0, slides [7]` |
| style/axes/legend/colors/position preserved | ✅ (`replace_data` mutates data only) |
| agenda consistency still pass | ✅ `mapping_method=section_id, status=pass, unmatched 0` |
| contamination remains 0 | ✅ `contamination_clean=true, hits={}` |
| T5 unaffected | ✅ T5 (job 78) wrote no rebind report; T5 has 0 native charts; gate is tech_blue-only |

## Notes / limitations

- The rebind currently uses a **fixed deterministic dataset** (the integration milestone).
  Wiring Kimi-provided per-chart series is a follow-up; the mechanism is in place.
- All 6 P7 charts receive the same 2-series dataset (the master's 6 small charts originally
  had 3 series each / 1 category); `replace_data` rebuilds series/categories cleanly.
- External-link charts (the 2 leftover package chart parts outside P7) are never touched
  (P7-restricted + external-skip).
- Safe-by-construction for T5: name gate + T5 has no native charts (no-op regardless).

## Recommendation

Native chart rebind for T6 is integrated and validated. Next follow-ups (separate PRs):
feed Kimi-generated series into the rebind (per-chart real data), and the t5 master
de-branding pass. Defer prompt polish.

— End PR-Q2E —
