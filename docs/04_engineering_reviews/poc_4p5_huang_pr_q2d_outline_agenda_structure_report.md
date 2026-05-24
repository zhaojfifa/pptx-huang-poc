# PR-Q2D — Outline Agenda Structure Fix

Date: 2026-05-24 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Scope: make the outline generator produce a real agenda and bind body slides to sections
(top-down 总分). No HITL editor, no multi-level outline, no unrelated prompt polish, no chart
rebind, no t5 template cleanup, no deploy.

## Problem (from the agenda-guard validation)

The agenda/body disconnect was **not** body slides drifting — the **outline generator never
produced a real table of contents**:
- T5 (job 74): agenda slide was a **KPI/metrics page** (`营收3,612亿 / 利润198亿 …`) →
  guard `fail`, 0 mappings, 9 unmatched.
- T6 (job 76): agenda was a **single vague item** (`六大板块`) → guard `fail`, 11 unmatched.

## Changes

1. **Outline prompt (`core/content_generator.generate_outline`)** — added an
   **AGENDA STRUCTURE (REQUIRED)** rule block + schema:
   - top-level `"agenda"`: 3–6 sections `{section_id, section_title}`, parallel,
     business-meaningful; **forbidden**: metric cards, vague single buckets, conclusions.
   - the agenda/目录 slide must display the section titles (a real TOC), not KPIs.
   - every body slide must carry `section_id`, `section_title`, `slide_role_under_section`,
     and stay within its section.
2. **Carry-through (`web/app.py`)** — `_outline_to_cards` and `_cards_to_slides` now preserve
   `section_id` / `section_title` / `slide_role_under_section` end-to-end.
3. **Guard integration (`_agenda_consistency`)** — when explicit binding exists, build agenda
   items from the distinct `section_title`s (ordered by `section_id`) and map body slides by
   `section_id` (`mapping_method="section_id"`); **fall back to similarity** only when no
   binding is present. Report adds `mapping_method` + `agenda_items_count`.
4. **Per-slide prompt injection (`generate_slide_content`)** — now injects both the
   `section_title` and the `slide_role_under_section` ("本页在该章节中的作用：…") plus the
   "support this section, don't introduce unrelated themes" instruction. Injects only on
   confident/explicit matches.

## Validation (Step 6) — one T5 + one T6 run after the fix

| | before (similarity era) | after (PR-Q2D) |
|---|---|---|
| **T5** | job 74: `fail`, agenda = KPI metrics, mappings 0, unmatched 9 | **job 78: `pass`**, method `section_id`, **6 agenda items**, all 9 body slides mapped (3,4→A 5,6→B 7,8→C 9→D 10→E 11→F), **unmatched 0, orphans 0**, 9 prompts injected, PPTX opens (12 slides) |
| **T6** | job 76: `fail`, agenda = 「六大板块」, unmatched 11 | **job 81: `pass`**, method `section_id`, **5 agenda items**, all 11 body slides mapped (A,A,B,B,C,C,D,D,D,E,E), **unmatched 0, orphans 0**, PPTX opens (14 slides), contamination clean |

- agenda_consistency_report.json exists for both jobs ✅
- agenda_items count 3–6 ✅ (T5=6, T6=5)
- body slides mapped by `section_id` ✅ (mapping_method=section_id)
- unmatched_slides decreased ✅ (T5 9→0, T6 11→0)
- agenda page is now a real parallel section list ✅
  - T5 sections: 经营质效与财务表现 / 产能效率与智能制造 / 成本控制与精益运营 / 重点项目与技术突破 / 风险挑战与应对策略 / 2026年战略重点与目标
  - T6 sections: 数字化转型总体架构与平台能力 / 智能制造场景建设与推广路径 / 数据驱动与智能化应用成效 / 技术成熟度评估与标杆认定 / 下一步重点建设与保障措施
- final PPTX opens ✅ (T5 job 78, T6 job 81)

## Notes / limitations

- T6's first generation (job 80) failed at slide 9 on a transient Kimi **429
  engine_overloaded** (API hiccup, not logic); a retry (job 81) completed cleanly.
- Backward compatible: outlines without explicit binding still work via the similarity
  fallback.
- Out of scope and unchanged: t5 template residue (still surfaces in t5 output), chart
  rebind, HITL editor.

## Recommendation

Agenda/body top-down structure is now solid for both paths. Next candidates (separate PRs):
`native_chart_rebind` integration (T6 demo) and t5 master de-branding. Defer further prompt
polish.

— End PR-Q2D —
