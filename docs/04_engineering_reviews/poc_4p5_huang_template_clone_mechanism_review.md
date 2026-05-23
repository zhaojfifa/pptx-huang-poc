# Huang POC — Template 1:1 Clone Mechanism Review (O1)

Date: 2026-05-23 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Evidence: job_56 (t5/business, 12p) and job_58 (t6/tech_blue, 8p), read-only.

## 1. Executive Summary

Huang does **true slide cloning + in-place text replacement**, not slide reconstruction.
For each output slide it `shutil.copy`s the master `.pptx`, then for slide *i* it uses
template slide `i % total_template` (cycling/duplicating when needed) and **mutates only
text frames and tables** — every other visual element (backgrounds, shapes, images,
groups, gradients, charts, SmartArt) is preserved byte-for-byte via XML deepcopy.

- Text mapping is **blueprint-driven**: each editable shape is a "slot" with a capacity
  (`chars_per_line`, `max_lines`, `total_chars`) derived from the template's own text/box.
- Kimi produces the *words*; code does the *placement* and *capacity enforcement*.
- t5 clones cleanly with rich slots; t6 clones cleanly but its pages expose **very few
  editable slots**, so the visual is faithful but the content is thin (see O2).

## 2. Template Asset and DB Mapping

- DB `templates` row → `file_path` (absolute) + `overall_style` (JSON). `template_pages`
  rows hold per-page `markdown_content`, `layout_json`, `visual_json`, `generation_hints`.
- business → id 15 (12 analyzed pages); tech_blue → id 16 (8 analyzed pages).
- **Both `file_path`s point at the OLD repo** `…/ppt-agent-poc/data/pptx_agent_20260521/templates_storage/{t5,t6}.pptx` (exist on disk; the render reads from there, not this repo's `templates_storage/` or `data/`).
- `selected_template.json` (per job) snapshots `template_key`, `template_name`, `file_path`,
  `page_count`, `overall_style` so outline/content/render share one source of truth.

## 3. Analyzer Outputs and What They Mean

`template_analyzer/analyze_template.py` (offline, not run this session) populates per page:
- `overall_style`: style_name, description, color_palette, font_recommendations, design
  keywords, target audience → fed into the **outline prompt** (tone/keywords).
- `layout_json` / `visual_json`: shape inventory & geometry → consumed by
  `TemplateStyleEngine` to build the **blueprint** (slots/rows/capacities).
- `generation_hints`: optional `layout_description`, `content_relevance`,
  `capacity_constraints`, `module_title_rule` → injected into the **per-slide prompt**
  (with code defaults when absent).
- `markdown_content`: the page's original text (reference / capacity basis).

The **blueprint** (`TemplateStyleEngine(template_page, pptx_path).blueprint`) is the
runtime contract. Per page it yields `slots = {title, subtitle, content[], labels[],
tables[], _rows, _row_order}`; each slot carries `shape_id`, `name`, `_text` (original),
`_capacity`. Slots are grouped into **visual rows** so the prompt can describe "第N行 has K
text areas". Observed example (t5 p4): a content slot `shape_id=52`, capacity
`{chars_per_line:14, max_lines:13, total_chars:182}`.

## 4. TemplateCloner Flow (`core/template_cloner.py`)

1. `clone_and_fill(template_path, slides_data, output_path, blueprints)`:
   copy master → open → for each content slide pick template slide `i % total_template`;
   `_duplicate_slide` (deepcopy every shape) when output pages > template pages.
2. `_fill_slide` → `_fill_with_blueprint` (preferred) or `_fill_with_heuristics` (fallback
   when no blueprint: classify shapes by position/size).
3. Blueprint fill order: title slot → subtitle slot → **`slot_mappings`** (shape_id→text,
   the precise path) or fallback `content` slots → **tables** (`_fill_table`) → **labels**
   (`label_mappings` shape_id→text; numeric labels always preserved).
4. Text write = `_set_shape_text`: preserves paragraph `pPr` and run `rPr` (font, size,
   bold, color) by cloning existing paragraphs/runs; strips stray bullet markers; clamps
   abnormal line-spacing; **overflow guard** = drop one font point once if text exceeds
   `total_chars`. Tables: add/delete rows & cols to fit, truncate cells to
   `max_total_chars` with "…", preserve cell font size.
5. `render_from_template` (ppt_renderer) is a thin delegate to the cloner; the non-template
   `render()` path is fallback only (textbox rebuild + mermaid charts).

## 5. Job 56 (t5/business) Page-by-Page Clone Map

Mapping is strict 1:1 (slide N → template page N). Slot counts (content/label/table) and
generated content density:

| slide | type | tpl pg | content slots | label slots | table | md chars | title |
|---|---|---|---|---|---|---|---|
| 1 | title | 1 | 0 | 1 | – | 0 | 2025年度生产经营情况汇报 |
| 2 | content(agenda) | 2 | 3 | 4 | – | 52 | 汇报提纲 |
| 3 | content | 3 | 4 | 10 | – | 252 | 经营概览：年度核心指标 |
| 4 | chart | 4 | 4 | 8 | – | 322 | 产量与效率：双轮驱动分析 |
| 5 | content | 5 | 4 | 21 | – | 322 | 成本控制：全流程降本体系 |
| 6 | content | 6 | 25 | 37 | – | 322 | 重点项目：年度工程进展 |
| 7 | content | 7 | 12 | 3 | – | 332 | 风险挑战：内外部形势研判 |
| 8 | content(table) | 8 | 0 | 0 | ✅ | 0 | 风险矩阵：分级管控方案 |
| 9 | content(table) | 9 | 1 | 3 | ✅ | 192 | 重点项目效益评估 |
| 10 | content | 10 | 2 | 42 | – | 44 | 下一步工作建议 |
| 11 | content | 11 | 16 | 0 | – | 730 | 2026年重点工作部署 |
| 12 | ending | 12 | 0 | 0 | – | 0 | 谢谢 |

Observations: t5 exposes well-structured, high-capacity slots (esp. p6/p7/p11) and 2 real
tables (p8/p9). Final text scan = clean (no template/author leakage, no secrets).

## 6. Job 58 (t6/tech_blue) Page-by-Page Clone Map

| slide | type | tpl pg | content slots | label slots | table | md chars | title |
|---|---|---|---|---|---|---|---|
| 1 | title | 1 | 1 | 0 | – | 47 | 宝钢智能制造与数字化转型建设进展汇报 |
| 2 | content | 2 | 0 | 8 | – | 0 | 建设背景与总体目标 |
| 3 | content | 3 | 2 | 0 | – | 114 | 平台架构与技术底座 |
| 4 | content | 4 | 1 | 0 | – | 362 | 关键能力与核心组件 |
| 5 | content | 5 | 1 | 0 | – | 199 | 典型应用场景与价值闭环 |
| 6 | chart | 6 | 1 | 0 | ✅ | 57 | 阶段成果与效能评估 |
| 7 | content | 7 | 1 | 0 | – | 63 | 风险挑战与应对策略 |
| 8 | ending | 8 | 6 | 0 | – | 432 | 下一步计划与演进路线 |

Observations: t6 pages are **slot-starved** — most pages expose only 0–2 content slots and
0 labels. The clone is visually faithful, but there are simply **few editable regions to
inject content into**, so the deck reads thin/under-filled. Slide 2 has zero content slots
(8 labels only) → effectively a graphic with swapped tags. This is the dominant reason t6
is below target (mechanical, not LLM quality).

## 7. Editable vs Visual Preservation Grade

| Element | Behavior | Grade |
|---|---|---|
| Backgrounds / decorative shapes / gradients / shadows | deepcopy, untouched | 1:1 ✅ |
| Images / pictures / groups / SmartArt / native charts | deepcopy, untouched | 1:1 ✅ (visual/static; not re-databound) |
| Text frames (title/subtitle/content/labels) | text replaced, formatting preserved | native-editable ✅ |
| Tables | cell text replaced, rows/cols resized, styling kept | native-editable ✅ |
| Native PowerPoint charts | preserved as visual; **data NOT updated** by engine | static ⚠️ (key gap for trend pages → see O3) |

Native-editable after generation: all text + tables. Copied-as-visual (not regenerated):
images, native charts, SmartArt, decorative geometry.

## 8. Risks

1. **Old-template text contamination.** A slot that isn't mapped/overwritten keeps its
   original template words. Evidence: blueprint `_text="什么是穿透式监管？"` and a content
   shape literally named `@紫荆的职场Point17` (a social handle from the source template).
   Label fallback also re-writes the *original* label when no mapping is produced.
   → Need a final integrity scan + a curated, de-branded master.
2. **Speaker notes / docProps / comments.** Cloner copies slides only; notes/comments on
   copied slides and presentation docProps are NOT scrubbed → can leak source identity.
3. **Hidden / off-canvas shapes.** deepcopy preserves hidden shapes; if they contain old
   text they ride along invisibly.
4. **Content overflow.** Only a one-point font reduction + hard truncation guard; long
   Kimi bullets in small slots either shrink once or get "…"-cut → can clip.
5. **Bad slot capacity / starvation.** If analysis under-detects editable slots (t6), pages
   are under-filled; if it over-detects tiny label slots (t5 p10 has 42 labels), label
   mapping dominates and prose is sparse.
6. **Page-count cycling.** If requested slides > template pages, `i % total` reuses earlier
   pages — fine within page guard, but a silent duplicate-look risk if guard is bypassed.

## 9. Template Designer Requirements (to keep 1:1 clean and content-rich)

1. **De-brand the master**: remove author handles in shape names, sample text, speaker
   notes, comments, docProps (title/author/company). No "穿透式监管"-style leftovers.
2. **Right-size editable text regions**: every content page should expose 3–6 real content
   text boxes with **meaningful capacity** (≥2 lines, ≥80 chars) — this is exactly what t6
   lacks. Avoid pages that are pure imagery with one tiny title.
3. **Name slots semantically** (e.g. `title`, `content_1`, `metric_label_1`) so the engine
   maps deterministically and the integrity scan can assert coverage.
4. **Tables**: provide a clean header row + representative rows; keep column widths able to
   hold ~the longest expected value.
5. **Charts/trend pages**: provide either a clearly-bounded image placeholder OR a native
   chart with an obvious data table (see O3) — do not bury data inside a flattened picture.
6. **One layout per role**: cover / agenda / 2–3 content variants / table / closing, each
   with consistent, capacity-balanced slots.
7. **Avoid extreme slot counts** (e.g. 37–42 micro-labels) unless the design truly needs
   them; they dilute prose generation.

## 10. Engineering Optimization Points

- **Integrity gate (high value, low risk):** after `clone_and_fill`, scan final PPTX text
  (slides + notes + docProps + comments) for a forbidden/original-term set and fail loudly.
- **Slot-coverage assertion:** warn when a page has < N usable content slots (catches t6
  starvation at analyze time, not at demo time).
- **Capacity-aware overflow:** allow the font auto-shrink to iterate (not just −1pt once),
  or reflow bullets, before truncating.
- **De-brand on import:** strip shape-name handles / notes / docProps during analysis so the
  DB master is clean regardless of the source file.
- **Re-point file_path into this repo** (remove old-repo dependency) — see prior diagnostic.

— End O1 —
