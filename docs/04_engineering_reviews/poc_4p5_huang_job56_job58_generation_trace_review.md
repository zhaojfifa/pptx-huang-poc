# Huang POC — job_56 / job_58 Generation Trace Review (O2)

Date: 2026-05-23 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Evidence: `logs/job_55..58`, `output/job_56_final.pptx`, `output/job_58_final.pptx` (read-only).

## 0. Pipeline (prompt → PPT)

`/api/poc/outline` → `_compose_requirements` → `ContentGenerator.generate_outline`
(Kimi, 1 call, JSON) → editable cards → user confirm → `/api/poc/generate` →
`_run_generation` thread → per slide: `generate_slide_content` (Kimi: 1 content call +
optional correction + label batches) → `ContentNormalizer` (slot-count/capacity) →
`step_normalize_layouts` (blueprint) → `TemplateCloner` render → preview + final.

**Critical input fact:** both runs used `input_mode="manual"`, and `_source_markdown`
returns `""` for manual mode. So **document_markdown was EMPTY**; `_extract_relevant_doc`
and `summarize_document` returned empty. **Kimi had no source material** — every slide was
written from the prompt + key_points + template slot specs only. This caps factual depth
and is the single biggest lever for quality (see Q1).

## 1. job_56 (t5/business) Trace

- Original user prompt: 《2025年度宝钢股份钢铁主业生产经营情况汇报》… 经营概览/产量与效率/成本控制/重点项目/风险挑战/下一步；正式、稳重、经营分析会。
- Outline request payload (key fields): template_name=商务风格, template_key=business,
  page_count=12, audience=management, scenario=business_review, tone=formal, language=zh-CN,
  input_mode=manual.
- Outline prompt → Kimi: `logs/job_55/llm_prompt_outline.txt` (6.8 KB) — includes style
  block + **per-page slot specs** + strict rules (exactly 12 slides, key_points == content
  slots). Response: `llm_output_outline.json`, 12 slides, source=kimi, 77 s.
- selected_template.json: business / 商务风格 / old-repo t5.pptx / 12 pages /
  style "SOE Digital Governance Professional".
- Per slide prompts/outputs: `logs/job_56/llm_prompt_slide_1..12.txt` +
  `llm_output_slide_*` + label batches (slides 1,3,4,5,6,7,9,10 had label batches).

### job_56 per-slide table

| idx | page_type | src tpl slide | Kimi prompt intent | generated title | content summary | quality issue | optimization |
|---|---|---|---|---|---|---|---|
| 1 | cover | 1 | 1 title + 1 subtitle, no bullets | 2025年度生产经营情况汇报 | cover only | none | keep |
| 2 | agenda | 2 | short parallel chapter names (3 content/4 label) | 汇报提纲 | 52 ch, 4 sections | a touch generic | tie agenda to actual sections |
| 3 | content | 3 |结论先行 metrics (4 content/10 label) | 经营概览：年度核心指标 | 252 ch | strong | keep |
| 4 | chart | 4 | dual-driver analysis (4 content/8 label) | 产量与效率：双轮驱动分析 | 322 ch | strong, but "chart" page has no real chart | O3 trend page |
| 5 | content | 5 | cost system (4 content/21 label) | 成本控制：全流程降本体系 | 322 ch | strong | keep |
| 6 | content | 6 | 25 content + 37 label grid | 重点项目：年度工程进展 | 322 ch but 25 slots → many 1-line tags | over-fragmented; many micro-modules ("产能释放","三高炉") | cap slot count / merge micro-labels |
| 7 | content | 7 | risk research (12 content/3 label) | 风险挑战：内外部形势研判 | 332 ch | strong | keep |
| 8 | table | 8 | table_data only | 风险矩阵：分级管控方案 | table (md 0) | depends on table quality; no prose context | ensure rich table rows |
| 9 | table+content | 9 | table + 1 content (3 label) | 重点项目效益评估 | 192 ch + table | good | keep |
| 10 | content | 10 | 2 content + **42 labels** | 下一步工作建议 | 44 ch prose, label-dominated | prose starved by 42 micro-labels | reduce label slots in master |
| 11 | content | 11 | 16 content slots | 2026年重点工作部署 | 730 ch (densest) | strong, near-overflow risk | watch capacity |
| 12 | closing | 12 | short closing | 谢谢 | 0 | none | keep |

Already ~4.5 pages: 1, 3, 4, 5, 7, 9, 11, 12. Score-pullers: **6** (over-fragmented micro
modules) and **10** (prose crowded out by 42 label slots); 2/8 mildly generic.

## 2. job_58 (t6/tech_blue) Trace — why below target

- Prompt: 《宝钢智能制造与数字化转型建设进展汇报》… 建设背景/平台架构/关键能力/应用场景/阶段成果/风险/下一步；科技感、清晰。
- Outline: `logs/job_57` (Kimi, 62 s, 8 slides, source=kimi). 12-page request was correctly
  rejected by the page guard (template only has 8 analyzed pages).
- Per slide: `logs/job_58/llm_prompt_slide_1..8.txt` + outputs. No label batches (≈0 labels).

### job_58 per-slide table

| idx | page_type | src tpl slide | Kimi prompt intent (tech_blue overlay) | generated title | content summary | quality issue | optimization |
|---|---|---|---|---|---|---|---|
| 1 | cover | 1 | title+subtitle | 宝钢智能制造与数字化转型建设进展汇报 | 47 ch | ok | keep |
| 2 | content | 2 | **0 content slots / 8 labels** | 建设背景与总体目标 | md 0 (labels only) | page has nowhere to put prose → empty narrative | master needs real content slots |
| 3 | content | 3 | 2 content slots | 平台架构与技术底座 | 114 ch | thin (2 slots) | add content slots |
| 4 | content | 4 | 1 content slot | 关键能力与核心组件 | 362 ch in 1 slot | all text crammed into one box | split into 3–4 slots |
| 5 | content | 5 | 1 content slot | 典型应用场景与价值闭环 | 199 ch | thin/single-block | split slots |
| 6 | chart+table | 6 | 1 content + table | 阶段成果与效能评估 | 57 ch + table | "chart" but no real chart; sparse | O3 trend page |
| 7 | content | 7 | 1 content slot | 风险挑战与应对策略 | 63 ch | very thin | add slots |
| 8 | closing | 8 | 6 content slots | 下一步计划与演进路线 | 432 ch | over-full for a closing | rebalance |

Root cause: **template slot starvation**, not LLM quality. t6 pages expose 0–2 editable
content regions; the engine and Kimi behave correctly but have almost nowhere to write, so
the deck is under-filled and structurally uneven (one page empty, one page over-stuffed).
The tech_blue style overlay is applied (architecture/platform/capability vocabulary is
present in slide 3), so wording is on-style; the deficiency is structural capacity.

## 3. Answers

1. **Does Kimi receive enough source material?** **No.** Manual mode → empty document.
   Content is generated from the prompt + key_points only; no facts/figures to ground it.
   The biggest single quality lever is feeding a real source doc (example/upload mode).
2. **Page-type-specific instructions per slide?** **Yes.** `page_type_prompt.classify()` +
   `content_guidance(type, template_key)` inject cover/agenda/summary/content/table/
   dense_labels/closing guidance plus a business/tech_blue overlay into each slide prompt.
3. **Are cover/agenda/content/table/closing prompts different enough?** Yes — distinct
   guidance blocks; cover bans bullets, agenda demands short parallel names, table forces
   `table_data`, closing forbids prose. Adequate for POC; the weak spot is intra-"content"
   uniformity (all content pages share one block) and over-reliance on slot specs.
4. **Is Kimi copying template semantics too much?** Low risk on wording (labels are
   semantically remapped; numerics preserved). The real "copying" risk is **unmapped slots
   keeping original template text** (mechanical, §O1.8), not Kimi imitation.
5. **Business terms vs generic drift?** Mostly grounded in the *prompt's* domain (宝钢/钢铁/
   湛江三高炉 appear), but with no source doc some figures are plausibly fabricated
   ("铁水成本2,340元/吨") — fine for a demo, risky for accuracy.
6. **Which job_56 pages are already 4.5?** 1, 3, 4, 5, 7, 9, 11, 12.
7. **Which pull the score down?** 6 (25-slot fragmentation) and 10 (42 labels crowd out
   prose); 2 and 8 mildly generic.
8. **Prompt / content-planning rules that would help:**
   - Feed a real source document (manual mode starves Kimi).
   - Cap effective content modules per page (merge micro-labels; ~3–6 prose blocks max).
   - For "chart" pages, plan an actual data series (enables O3 trend page).
   - Add an outline quality gate (reject empty/duplicate/over-fragmented plans before spend).
   - Differentiate "content" guidance by sub-role (metrics vs narrative vs roadmap).

## 4. Failure / warning / weak-content signals observed

- No hard failures; both jobs reached `state=done`.
- Weak-content signals: job_56 slide 10 (44 ch prose vs 42 labels), job_58 slides 2/7
  (md 0 / 63 ch). Module-count corrections may have fired on high-slot pages (t5 p6 25
  slots) — `_normalize_modules` truncates/pads to exact count, which can yield filler
  modules. No secrets/old-term leakage in final text (scanned clean).

— End O2 —
