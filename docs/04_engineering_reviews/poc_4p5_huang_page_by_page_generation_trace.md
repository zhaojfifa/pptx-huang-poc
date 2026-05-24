# Huang POC — Page-by-Page Generation Interaction Trace

Date: 2026-05-23 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Primary evidence: **job_64** (t5/business, grounded, 12 pages); cross-ref job_62/job_56.
Analysis only — no code changed, nothing committed, no long re-generation.

## Part 1 · Whole generation flow

```
[User prompt + product config]                                            (UI)
   │  audience/scenario/tone/page_count/template_key
   ▼
[_compose_requirements] ─────────────────────────────────► requirements string
   │
[_source_markdown → _ground_doc]                                          (CODE)
   │  example/upload → markdown ; prepend 「关键事实/数据」auto-facts block
   ▼  doc_md  (job_64: example → 关键事实 block + full doc)
[generate_outline]  prompt = requirements + doc(summarized) + style       (KIMI)
   │  + per-page SLOT SPECS + CRITICAL rules (EXACTLY 12, key_points==content slots)
   ▼  outline JSON {slides:[type,title,key_points,template_page_number]}
[_outline_quality_gate] ─► outline_quality_report.json  (advisory)        (CODE)
   ▼
[_resolve_template] → business id15 (12 pages, in-repo t5.pptx)           (CODE/DB)
   │
[per slide i]  template page = i % 12  (strict 1:1 here)                  (CODE)
   │  blueprint = TemplateStyleEngine(page_i)  → slots{title,content,labels,tables,_rows}
   ▼
[generate_slide_content]  prompt = slide_outline + relevant_doc + doc_summary  (KIMI)
   │  + page_type guidance (cover/agenda/.../table) + business overlay
   │  + STRICT slot specs (modules count == content slots, per-slot capacity)
   │  + table headers injected verbatim from template analysis
   ▼  {title, subtitle, modules[], table_data?}  (+ separate label remap calls)
[ContentNormalizer + _normalize_modules]  force module count, capacity     (CODE)
   ▼
[TemplateLayoutMapper.generate_content_mapping] → blueprint slot_mappings  (CODE)
   ▼
[TemplateCloner.clone_and_fill]  copy master → per slide:                  (CODE)
   │  title/subtitle/content slot text fill (preserve run/para format)
   │  table fill (resize rows/cols, truncate to capacity)
   │  label remap (numeric preserved); UNMAPPED shapes keep ORIGINAL text ◄── residue
   ▼  output/job_64_final.pptx
[_final_contamination_scan] ─► final_contamination_report.json (advisory) (CODE)
```

Per-step input / constraint / Kimi vs code / loss point:

| Step | Input | Injected constraints | Kimi | Code | Quality-loss point |
|---|---|---|---|---|---|
| compose req | prompt+config | audience/scenario/tone/pages | — | folds to one string | weak prompt → weak plan |
| ground doc | example/upload | auto key-facts block | — | parse+prepend | empty doc (manual mode) = no facts |
| outline | req+doc+slotspec | EXACTLY N, kp==content slots | plan titles/kp | gate/log | over-fragmented plan, generic titles |
| template resolve | style name | most-pages row | — | DB lookup | (clean now; in-repo) |
| page map | i % 12 | strict order | — | pick/duplicate | "chart" type → non-chart page |
| slide content | outline+relevant+summary | slot count+capacity, **table headers verbatim**, page-type | write modules/table/subtitle | normalize count/capacity | residue headers steer Kimi; micro-slots dilute |
| layout map | slots+content | shape_id mapping | — | blueprint slot_mappings | label/index mismatch (mitigated) |
| clone+fill | master+mappings | preserve format, capacity | — | text/table/label fill | **unmapped shapes keep old text** |
| scan | final pptx | forbidden terms | — | count hits | detection only (no removal yet) |

## Part 2 · Outline generation analysis

1. **Injected:** the requirements string (prompt + audience/scenario/tone/pages), the
   grounded `doc_md` (which begins with the auto `关键事实/数据` block: 营收 3,612 亿、净利 198
   亿、产量 5,180 万吨、铁水成本 2,340 元/吨、硅钢 45 亿、高端占比 42% …), the template style
   block, and **per-page slot specifications**.
2. **Constraints to Kimi:** "EXACTLY 12 slides", "slide N → template page N (no reuse)",
   "key_points count == that page's content-slot count", per-key-point length caps, type
   enumeration (title|content|section|chart|ending).
3. **Did outline reflect source facts?** Yes — titles map to the doc's real sections
   (经营成果与财务表现 / 产量效率与智能制造 / 成本控制 / 重点项目 / 风险 / 2026 战略).
4. **Forced 12 pages?** Yes (job_64 outline = 12, matches template).
5. **Avoid duplicate/generic topics?** Mostly. Gate flagged only `slide 12 '谢谢'`
   (generic, but it's the ending) and `slide 8 empty key_points` (chart page). No
   duplicate topics. (Earlier job_56 had a more fragmented plan on p6/p10.)
6. **Outline decisions that hurt later quality:** assigning **"chart" type to template
   pages 6/8/10 that have no real chart** (the trend story has nowhere to render → becomes
   tag-clouds/tables); and accepting page 10's 42-label structure as a content page.

- **Strengths:** grounded, exactly-12, ordered 1:1, section-faithful, low duplication.
- **Weaknesses:** "chart" pages aren't chartable; agenda (slide 2) stays generic; relies on
  template slot specs that encode fragmentation.
- **Opportunities:** outline-time check "chart type but template page has no chart frame";
  tie agenda items to detected source sections; down-rank pages with >20 micro-slots.

## Part 3 · Page-by-page (job_64, template = in-repo t5.pptx)

| # | final title | tpl pg | type | injected constraints | source facts (ex.) | Kimi role | slot structure | rendering | visible issue | root cause | fix |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2025年度经营复盘与战略展望 | 1 | cover | title+subtitle, no bullets | no (cover) | title | normal (c0/l1) | clone+title | none | — | keep |
| 2 | 年度经营概览 | 2 | agenda | short parallel names (c3/l4) | no | chapter names | normal | clone+text+labels | slightly generic agenda | B | tie items to real sections |
| 3 | 经营成果与财务表现 | 3 | content | 4 content + 10 label | **Y** 3,612/198/2,340/142亿/42% | metrics narrative | label-heavy (c4/l10) | clone+text+label remap | minor label noise | C (mild) | trim micro-labels |
| 4 | 产量效率与智能制造 | 4 | content | 4 content + 8 label | **Y** 2,340/45亿/湛江/硅钢 | narrative | label-heavy (c4/l8) | clone+text+labels | good | C (mild) | keep |
| 5 | 成本控制与运营优化 | 5 | content | 4 content + 21 label | **Y** 2,340/86亿/湛江 | narrative | fragmented (c4/l21) | clone+text+labels | prose competes w/ 21 labels | C | reduce labels in master |
| 6 | 重点项目推进矩阵 | 6 | chart | 25 content + 37 label | **Y** 湛江/硅钢/梅山 | many 1-line tags | **fragmented + residue** (c25/l37, cap18) | clone+text+labels | **VPN / SD-WAN residue** + tag-cloud | **A + C** | de-brand + cap slots |
| 7 | 风险挑战与应对策略 | 7 | content | 12 content + 3 label | **Y** 198/42%/硅钢 | narrative | rich (c12/l3) | clone+text | strong | — | keep (model page) |
| 8 | 2026年战略目标体系 | 8 | chart→table | table headers injected | **Y** 5,300/45%/营收 | table rows | table-only (t1) | table fill | **headers = residue** (是否模型/分析场景/模型场景/指标规则/1模型/多个规则) | **A + E** | remap/de-brand headers |
| 9 | 2026年重点工作部署 | 9 | content+table | 1 content + table | **Y** 42%/梅山/硅钢 | narrative+table | table+sparse (c1/l3/t1) | text+table fill | residue 是否模型 in table | A + E | de-brand headers |
| 10 | 战略举措实施路径 | 10 | chart | 2 content + **42 label** | no | starved prose | fragmented (c2/l42, cap20, md37) | clone+text+labels | content starvation, tag-cloud | C (severe) | redesign page / fewer labels |
| 11 | 核心结论与管理建议 | 11 | content | 16 content slots | **Y** all key figures | dense narrative | rich (c16/l0, md804) | clone+text | strongest; near-overflow | — | watch capacity |
| 12 | 谢谢 | 12 | ending | short closing | no | closing | empty | clone | generic title (ok) | — | keep |

Source-fact grounding present on slides 3–9 and 11; absent only on cover/agenda/ending and
the starved slide 10.

## Part 4 · Huang ceiling analysis

1. **What 1:1 clone does very well:** pixel-faithful, on-style, native-editable text and
   tables; strong dense-narrative pages (3,4,7,11 ≈ 4.5+). Visual quality is not the limiter.
2. **Cannot solve if template has old text:** unmapped shapes/headers pass through verbatim
   — slide 6 (VPN/SD-WAN), slide 8/9 table headers (是否模型/分析场景…). The cloner faithfully
   reproduces residue; generation cannot remove what it never maps.
3. **Cannot solve if template has too many micro-slots:** slides 5/6/10 (21–42 labels) read
   as tag-clouds; capacity caps starve prose (slide 10 md=37). Kimi+code fill correctly but
   the page role is wrong.
4. **Cannot solve without a chart/data skill:** slides 6/8/10 are "chart" but there is no
   trend/line visual; data degrades into text/table/labels — the analytical story is missing.
5. **Improvable by prompt/grounding only:** agenda specificity, generic-phrasing trim —
   limited upside since grounding is already strong (facts on 8/12 pages).
6. **Requires designer/template change:** de-brand residue (6/8/9), reduce micro-slots
   (5/6/10), and provide a real chart frame (O3 hybrid).

| Ceiling stage | Expected level | Why |
|---|---|---|
| current t5 | **4.4–4.5** | strong 3/4/7/11; dragged by residue (6/8/9) + fragmentation (5/6/10) + no chart |
| after template de-branding | **~4.5** | removes embarrassing VPN/SD-WAN/是否模型; tables read clean |
| after source/prompt opt | **4.5 stable** | agenda + generic trim; grounding already near-max |
| after line-chart hybrid | **4.5+ → 4.6** | slides 6/8/10 deliver real data viz; "chart" pages finally chart |

## Part 5 · Optimization decision table

| Issue type | Evidence page(s) | Root cause | Fix owner | Fix method | Expected gain | Priority |
|---|---|---|---|---|---|---|
| A. template residue | 6 (VPN/SD-WAN), 8/9 (table headers) | old text in unmapped shapes + headers re-injected to prompt | Designer + Eng | de-brand t5 master; OR semantically remap table headers like labels | removes embarrassing leaks; scan → 0 | **P0** |
| B. generic content | 2 (agenda) | agenda not tied to real sections | Eng (prompt) | derive agenda from detected source sections | small | P2 |
| C. dense slot fragmentation | 5,6,10 | template exposes 21–42 micro-labels | Designer (+ Eng warn) | reduce labels in master; cap effective modules; merge | medium–high (fixes worst pages) | **P1** |
| D. missing trend/data expression | 6,8,10 ("chart") | no chart/data skill | Eng (+ Designer frame) | O3 hybrid: chart image into named region | high (visible wow) | **P1** |
| E. weak table narrative | 8,9 | residue headers constrain rows | Designer + Eng | clean headers; richer row spec | medium | P1 |
| F. page mapping mismatch | 6,8,10 | "chart" type → non-chart page | Eng (outline gate) | flag chart-type on non-chart page | small–medium | P2 |
| G. manual HITL | 6,10 | starved/fragmented pages | Product | slot-level edit before final render | guarantees demo | P2 |

## Deliverable note
Reports referenced live in gitignored `logs/job_64/`
(`outline_quality_report.json` = 2 warnings; `slot_fragmentation_report.json` = flagged
[3,4,5,6,9,10]; `final_contamination_report.json` = 8 hits). Not committed.

— End page-by-page trace —
