# Huang POC — Template Update Validation (T5 / T6)

Date: 2026-05-24 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Analysis + controlled regeneration. No external chart skill, no T5 chart logic change, no
prompt optimization, no deploy. Nothing committed.

## 0. T6 index stabilization (Step 1)

The first two re-index attempts failed and left an inconsistent state; both are now resolved:
- attempt v3/v4 partial → junk row **id 22 (6/14 pages) deleted** (necessary for resolution
  correctness).
- v4 crashed fast (47 s) at `analyze_overall_style`: the LLM returned JSON wrapped in
  ```json fences and `LLMSkill.chat_structured` did a raw `json.loads` → `JSONDecodeError`.
  No row was created (crash precedes `TemplateDAO.create`).
- **v5 retry succeeded** (LLM returned clean JSON): **template_id 23, 14 pages**, 14
  screenshots in `logs/template_screenshots_23/`, **14/14 pages vision-analyzed**.
  `_resolve_template("科技蓝风格") → id 23` (14 pages out-ranks old 8/10/13). No partial/old
  row wins. The SameFileError guard (PR-Q1d) also fired correctly in this run
  (`source and destination are same; reuse existing template file`).

Retry strategy note: the only remaining flakiness is the markdown-fenced JSON from Kimi at
`analyze_overall_style`. It is non-deterministic and crashes fast & early (cheap to retry).
A minimal robustness fix (strip ```json fences before `json.loads` in
`chat_structured`) would remove this failure class — recommended but out of this round's scope.

## 1. T5 result (business)

- job_id: **72**  · template_id: **19** · page count: **12** · output: `output/job_72_final.pptx` (3.44 MB)
- opens OK: ✅ · source grounding: example doc (grounded)
- **contamination: NOT clean — ~5–7 hits** (穿透, VPN, SD-WAN, 是否模型, 分析场景 / status
  reported 是否模型/指标规则/模型场景/1模型/多个规则). The t5 master (id 19) is only
  **partially** de-branded (index carried 16 residue occurrences on P6/P9/P10/P11).
- table alignment (headers centered / first column centered): **inconclusive
  programmatically** — paragraph alignment reads `None` (inherits template/style default),
  so centering cannot be asserted from the file; **requires visual review**.
- P7/P8 top-text overflow & auto-fit: **requires visual review** (overflow is a render-time
  property; not determinable from the pptx without rendering).
- agenda/body consistency: outline is grounded and section-faithful; 1 advisory warning
  (`generic_title: slide 12 '谢谢'`). slot fragmentation flagged pages **[3,5,6,10]**.
- subjective quality delta: grounding solid (source figures present); **blocked by residual
  template contamination + micro-slot fragmentation**, not by the engine.

## 2. T6 result (tech_blue)

- template_id: **23** · page count: **14** · 14-page index completed: ✅ (14/14 vision)
- job_id: **70** · output: `output/job_70_final.pptx` (1.46 MB) · opens OK: ✅
- **P7 chart appears: ✅** — generated deck retains **6 native COLUMN_CLUSTERED charts** on
  page 7 (8 native charts deck-wide).
- **P7 chart remains native: ✅** (real chart objects, 3 series each; style/axes preserved
  by clone). Chart **data is the master's embedded demo values** — generation does **not**
  rebind chart data yet (allowed this round).
- surrounding P7 text filled: ✅ (e.g. 「六大业务域智能化闭环」「智能排产…排产周期缩短40%」).
- **contamination: CLEAN (0 hits)** ✅ — the corrected 14-page master is fully de-branded.
- fill rate / structure: 14 pages generated; slot fragmentation flagged **[2,5,10]**.
- remaining group/slot issues: P7 has 6 separate small charts (not grouped); the 2 leftover
  package chart parts (chart7/8) still carry the old external `D:\…xlsx` link but are not on
  P7 and not surfaced in output.

## 3. Chart feasibility status

- **clone preservation: PROVEN** — P7's native charts survive both standalone clone and a
  full T6 generation (job 70), staying native with styles intact.
- **replace_data: PROVEN (PR-Q2A/Q2B)** — with the new master's **embedded workbooks**,
  `chart.replace_data()` updated all 6 P7 charts (Q1–Q4, 2 series) cleanly, native+styled.
- **full generation uses chart rebind yet: NO** — the pipeline clones charts but does not
  call `replace_data`; P7 shows the master's demo data.
- **next minimal implementation step:** a small `native_chart_rebind` step in the generation
  worker that, for slides whose template page has embedded-workbook charts, calls
  `replace_data` with Kimi-provided series (numCache-rewrite fallback for any external-link
  chart). Single-series/2-series first; no chart library, no image stack.

## 4. Recommendation

- **T5 remains the business main path** — but its 4.5+ ceiling is currently gated by
  **template residue (P6/P9/P11)** and **micro-slot fragmentation (P3/P5/P6/P10)**, not the
  engine. Needs one more **t5 master de-branding** pass + a visual review of the claimed
  alignment/overflow fixes.
- **T6 becomes the chart/tech demo path** — clean master (0 contamination), 14-page index,
  native P7 charts that clone-preserve and are rebind-ready.
- **Next PR:** **`native_chart_rebind` integration** (de-risked by Q2A/Q2B; high value for the
  T6 chart demo) — wire `replace_data` into generation for embedded-workbook charts. In
  parallel: a **t5 master de-brand** pass (template-side, designer) to clear the remaining
  5–7 contamination hits. Defer prompt polish.

### Evidence index (gitignored, not committed)
`output/job_70_final.pptx` (T6), `output/job_72_final.pptx` (T5);
`logs/template_screenshots_23/` (14 T6 screenshots); analyzer logs `/tmp/analyze_t6_v5.log`.

### Items needing human (Jackie) visual confirmation
1. T5 P7/P8 top-text overflow & auto-fit. 2. T5 table header + first-column centering.
3. T6 P7 chart visual rendering in real PowerPoint. 4. Whether the remaining T5 residue is in
visible content or hidden/residual shapes.

— End template update validation —
