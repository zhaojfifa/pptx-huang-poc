# PR-Q2F — Template Slot Fill Polish + Agenda Rendering Fix

Date: 2026-05-24 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Scope: small conservative post-render polish to push T6 from 4.4+ toward 4.5+. No index
rebuild, no big features. Validated on T6 job 85.

## Root causes (from job 83)

1. **Agenda renders generic** — `_cards_to_slides` dropped the top-level `agenda`; the
   agenda slide's item slots were label-filled with the generic page title「汇报提纲」.
2. **Unsafe numbering** — body titles like「2. 技术推广路径」carried section numbering with
   no reliable section index (note:「表2-1」is a legit table caption, must be preserved).
3. **Placeholder residue** — P5「环形饼图（模式&场景占比）」, P6/P13「配图」, etc. left unfilled.
4. **P7 crowding** — six tiny ~1.9″ charts each rebound to 4 cats × 2 series = 8 bars.
5. **P8 right slots** — boxes 文本框 15/61–64 hold literal「XX」(ungrounded placeholders;
   not grouped, detected as shapes, but never mapped to content slots).

## Changes (new `core/deck_polish.py`, post-render, conservative)

- **A · `fix_agenda_slide`** — on the agenda slide, the mis-filled item slots (the repeated
  generic value, excluding the title placeholder) are replaced **in order with the real
  section titles**; unused item slots are cleared. Title and numeric labels (01/02/03)
  preserved.
- **B · `strip_unsafe_numbering`** — strips leading「2.1 」/「2. 」from short title-like
  shapes only; **never** from 表/图/Table/Fig captions.
- **C · `clear_placeholder_residue`** — clears shapes containing markers (环形饼图,
  类别&对应数量, 配图, 图例, 数据对应部门名称, xxxx) or bare「XX」fragments; strips trailing
  「：XX」. All clears logged to `logs/job_xx/template_placeholder_cleanup_report.json`.
- **D · chart restraint** (`web/app.py`) — P7 rebind now uses a **single 4-point series**
  (`营收(亿元)`) instead of 2 series, so each mini-chart shows 4 bars (less crowded). Still
  native, P7-only, embedded-workbook-only.
- **E · P8 diagnosis** — the right-side「XX」boxes are ungrouped, analyzer-detected text
  boxes that were not mapped to content slots (small label slots), so the label step left
  the template「XX」. Safe fix applied = cleared via pass C. Recommended template-side fix:
  give these boxes meaningful default labels or expose them as fillable label slots.

Polish A/B/C run for **all** decks; chart restraint (D) is T6-only (name-gated; T5 has no
charts).

## Validation — T6 job 85

| # | Check | Result |
|---|---|---|
| 1 | final PPTX opens | ✅ 14 slides |
| 2 | agenda shows real item titles | ✅ P2 = 总体架构与平台能力建设 / 智能场景应用与技术路径 / 数据驱动与运营效能提升 (01/02/03 + 目录 title kept); `agenda_filled=3` |
| 3 | no unsafe N.N numbering | ✅ stripped「2. 技术推广路径与模式」→「技术推广路径与模式」(`numbering_stripped=1`) |
| 4 | P5 no「环形饼图…」 | ✅ no placeholder markers remain |
| 5 | P7 native + less crowded | ✅ 6 native COLUMN_CLUSTERED, single 4-point series (`charts_total 6, rebound 6`) |
| 6 | P8 right slot filled or root-caused | ✅ root-caused (ungrounded「XX」) + cleared (6 XX boxes among 12) |
| 7 | agenda consistency pass | ✅ `status=pass, unmatched 0` |
| 8 | contamination 0 | ✅ `contamination_clean=true` |

Cleanup report (job 85): `placeholders_cleared=12` (P6×3「配图」, P8×6「XX」, P13×3「配图」),
`numbering_stripped=1`, `agenda_filled=3`.

## Notes / limitations

- The T6 agenda template page exposes only **3 item slots** while the outline yields 4–6
  sections → the first 3 sections are shown (template-side limit; add more agenda slots to
  show all). Not a blocker for 4.5+.
- P7 mini-charts all carry the same single series (POC milestone); per-chart Kimi data is a
  later follow-up.
- All passes are conservative and log every change; no broad deletion of generated content.

— End PR-Q2F —
