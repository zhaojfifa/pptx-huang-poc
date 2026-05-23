# Huang POC — 4.5+ Quality Improvement Options (O4)

Date: 2026-05-23 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Goal: push **t5/business** from 4.4–4.5 to a stable 4.5+. POC-practical wins, not
architecture purity. Grounded in O1 (clone mechanism) and O2 (job_56/58 trace).

## Ranked options

Legend — Impact: how much it moves 4.5+. Cost: build effort. Risk: chance of regressions.

### 1. Source-document grounding (fix manual-mode empty doc) — **DO FIRST**
- What: ensure a real source doc reaches Kimi. Today `input_mode=manual` →
  `_source_markdown` returns "" → Kimi writes from the prompt alone (O2 §0). Use example/
  upload mode for demos, or let manual mode accept pasted text.
- Impact: **Very High** (factual depth, credible numbers across all pages).
- Cost: Low (wire existing example/upload text into the outline+slide calls).
- Risk: Low. Dependency: a curated example doc per demo. Timing: **now**.

### 2. Outline quality gate before generation — **DO FIRST**
- What: validate the outline before spending per-slide calls — reject empty/duplicate
  titles, over-fragmented pages (e.g. 25 micro-slots), page-count mismatches; allow a
  cheap regenerate. Catches O2 score-pullers (job_56 p6/p10) early.
- Impact: High. Cost: Low–Med. Risk: Low. Timing: **now**.

### 3. Slot-count sanity / micro-label capping
- What: cap effective content modules per page (~3–6 prose blocks); merge/limit micro-label
  grids (t5 p6=37, p10=42 labels) so prose isn't crowded out. Tune at analyze or normalize.
- Impact: High (directly fixes the two t5 score-pullers). Cost: Med. Risk: Med (changes
  layout density — verify visually). Timing: **soon**.

### 4. Per-page prompt specialization (sub-roles within "content")
- What: split the single CONTENT guidance into metrics / narrative / roadmap variants;
  agenda ties to real sections. Page-type router already exists (O2 Q2) — extend it.
- Impact: Med–High. Cost: Med. Risk: Low. Timing: **soon**.

### 5. Strict integrity gate (final PPTX scan) — quality + safety
- What: after clone, scan slides + speaker notes + docProps + comments for forbidden /
  original-template terms (e.g. "穿透式监管", author handles like "@紫荆…") and fail loudly.
  Addresses contamination risks in O1 §8.
- Impact: Med (protects perceived quality / prevents embarrassing leakage). Cost: Med.
  Risk: Low. Timing: **soon** (also a pre-deploy must).

### 6. Template cleaning / de-branding at import
- What: strip shape-name handles, sample text, notes, comments, docProps when analyzing the
  master, so the DB template is clean regardless of source. Pairs with #5.
- Impact: Med. Cost: Med. Risk: Low. Dependency: analyzer change. Timing: **soon**.

### 7. Stronger table/data pages
- What: require richer `table_data` (denser rows, indicator/value/meaning/action columns
  per the TABLE guidance); validate non-empty tables (job_56 p8 had md 0 + table only).
- Impact: Med. Cost: Low–Med. Risk: Low. Timing: **soon**.

### 8. One trend / line-chart page (see O3)
- What: add a single data-driven trend page (recommended Hybrid / fallback native-clone).
- Impact: Med–High (visible "wow", fills the missing chart story). Cost: Med (Hybrid) /
  Low (native fallback). Risk: Med. Dependency: designer master + small engine add.
  Timing: **after #1–#3**, on approval.

### 9. Page-role grammar (designer ↔ engine contract)
- What: formalize semantic slot names + page roles so mapping is deterministic and the gate
  can assert coverage. Underpins #3/#5/#6.
- Impact: Med (compounding). Cost: Med. Risk: Low. Timing: **medium-term**.

### 10. Manual HITL edits before final generation
- What: let a human edit the confirmed outline / slot text before the (expensive) final
  render. The outline-confirm step already exists; extend to slot-level for demos.
- Impact: Med (guarantees demo quality). Cost: Med (UI). Risk: Low. Timing: **medium-term**.

### Also: source-document extraction / md quality
- What: improve doc→markdown extraction so grounding (#1) is high-fidelity (tables/figures).
- Impact: Med (multiplies #1). Cost: Med. Risk: Low. Timing: with/after #1.

### Also: business vocabulary + forbidden-term guard
- What: enforce business lexicon and ban internal/old terms in generated text (complements
  #5 on the generation side).
- Impact: Low–Med. Cost: Low. Risk: Low. Timing: with #5.

## Ranked summary

| # | Option | Impact | Cost | Risk | Timing |
|---|---|---|---|---|---|
| 1 | Source-doc grounding | Very High | Low | Low | now |
| 2 | Outline quality gate | High | Low–Med | Low | now |
| 3 | Slot-count / micro-label cap | High | Med | Med | soon |
| 4 | Per-page prompt sub-roles | Med–High | Med | Low | soon |
| 5 | Integrity gate (final scan) | Med | Med | Low | soon |
| 6 | Template de-branding | Med | Med | Low | soon |
| 7 | Stronger tables | Med | Low–Med | Low | soon |
| 8 | One trend page (O3) | Med–High | Low–Med | Med | after 1–3 |
| 9 | Page-role grammar | Med | Med | Low | medium |
| 10 | HITL slot edits | Med | Med | Low | medium |

## Top 3 actions (highest ROI)

1. **Feed a real source document to Kimi** (fix manual-mode empty doc). Biggest depth gain,
   lowest cost — every page benefits.
2. **Add an outline quality gate** to kill empty/duplicate/over-fragmented plans before
   per-slide spend (fixes job_56 p6/p10 class of problems cheaply).
3. **Cap slot fragmentation / micro-labels** so prose pages stay rich and balanced.

t6 is **not** the path to 4.5+ via prompts — its ceiling is set by template slot starvation
(O1/O2); treat t6 as second-style validation only and keep t5 as the POC display route.

— End O4 —
