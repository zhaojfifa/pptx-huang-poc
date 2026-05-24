# PR-Q2I — T5 Final De-brand + Table Alignment + Visual Baseline

Date: 2026-05-24 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
T5 = official POC main route. Out of scope: T6 redesign, new chart skill, Kimi per-chart
data, 1.1/1.2 numbering, deployment execution, mainline fusion, .zshrc.

## Scope A · T5 master de-branding

Residue located in the T5 master (`templates_storage/t5.pptx`) and cleaned with neutral,
layout-preserving replacements (run-level text edits; fills/borders/style untouched):

| Location | was | now |
|---|---|---|
| slide6 rounded-rect shapes | `VPN` / `SD-WAN` | `专网` / `广域网` |
| slide9 table header [0][1]/[0][3] | `分析场景` / `是否模型` | `业务场景` / `指标类型` |
| slide10 textbox | `穿透式监管` | `全流程管理` |
| slide11 speaker notes (dev scratch) | `指标规则、模型场景 / 1模型----多个规则…` | cleared |

- Master re-scan after edit: **residue total = 0** (visible shapes + table cells + notes +
  docProps). Backup saved to `/tmp` before editing.
- Re-ran analyzer (master changed): **new clean T5 `template_id = 24`**, 12 pages, 12
  screenshots, 12/12 vision; **index residue = 0**. `_resolve_template("商务风格") → id 24`.
- T6 not touched.

## Scope B · Table alignment polish (`core/typography_polish.py`)

Extended `normalize_table_typography` (alignment-only; preserves fills/borders/colors; no
global style rewrite):
- **A3:** header row centered horizontally (`PP_ALIGN.CENTER`) + vertically (`MIDDLE`).
- **A4:** first column centered when it is a category/index/key column (short non-numeric
  labels, not a numeric data column).
- Audit records `header_centered` / `first_col_centered` per table.

## Scope C · Final T5 rerun (job 96, id 24)

| # | Check | Result |
|---|---|---|
| 1 | final PPTX opens | ✅ `output/job_96_final.pptx` |
| 2 | 12 slides | ✅ |
| 3 | agenda consistency | ✅ `pass`, unmatched 0 |
| 4 | contamination | ✅ **0 — CLEAN** (all 7 prior hits removed) |
| 5 | table header & first-col alignment | ✅ both tables (slides 8, 9) header + first-col = **CENTER** (was inherit) |
| 6 | P5 title/header overflow | **render-time → needs human visual review** (residue removed; overflow not detectable from .pptx) |
| 7 | P6 overlap/residue | residue **gone** (VPN/SD-WAN→专网/广域网); overlap **render-time → needs visual review** |
| 8 | typography polish still runs | ✅ 2 tables, text hierarchy capped 2 inversions |

## Scope D · T6 regression smoke (job 97)

Shared `typography_polish` was modified, so a cheap T6 smoke confirmed no regression:
- opens 14 slides; P7 6 native charts; rebind **6/6, errors 0**; agenda **pass**;
  contamination **clean**; tables auto-centered too (1 body run capped). **No regression.**
- T6 master/index/logic unchanged (only the shared post-render polish improved alignment).

## Status & deployment note

- **T5 main baseline is clean and aligned:** contamination 0, agenda pass, tables centered,
  opens 12 slides → ready for human visual acceptance.
- **Remaining = visual-only:** P5 header L-R overflow and P6 architecture overlap are
  render-time layout items (template-tuning / light render constraint), to be confirmed by
  human review — not residue or data problems.
- **Portability reminder:** the de-branded `templates_storage/t5.pptx` and the new `id 24`
  index are **local-only** (templates_storage gitignored, DB local). The deploy host must
  receive the cleaned master + rebuilt index (plus CJK fonts, rotated Kimi key) — carried as
  the existing deployment-prep blocker.

## Baselines (gitignored, local)
- T5 main: `output/job_96_final.pptx` + `logs/job_96/*` (agenda/typography/contamination).
- T6 demo: `output/job_97_final.pptx` + `logs/job_97/*`.

## Out-of-scope confirmation
No T6 redesign, no new chart skill, no Kimi per-chart data, no 1.1/1.2 numbering, no
deployment, no mainline fusion, .zshrc untouched.

— End PR-Q2I —
