# Huang POC — Line Chart / Trend Page Route Decision (O3)

Date: 2026-05-23 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Scope: how to add ONE trend/line-chart page for POC 4.5 with minimal risk.
No chart code is implemented in this review.

## Context (from O1/O2)

- Render is **clone + text replace**. The cloner mutates only text frames and tables;
  images / native charts are copied as-is and **not re-databound**.
- The only existing image-generation path is `MermaidSkill` (flow/diagram oriented), used
  by the non-template `render()` fallback — **not** wired into clone mode, and not a
  quantitative line-chart tool.
- "chart"-typed pages today (job_56 p4, job_58 p6) are just regular text/table pages — there
  is no actual chart being produced. So a trend page is genuinely missing.

## Option A — 1:1 template clone of a native chart page

Designer adds a slide with a **native PowerPoint line chart**; engine clones the slide and
only replaces labels / a backing data table's text.

- Pros: perfect on-style visual; fully native & editable; zero new rendering code; lowest
  visual-quality risk; consistent with the 1:1 philosophy.
- Cons: the engine does **not** currently rewrite native chart series data — so the line
  would show the designer's placeholder numbers unless we (a) also drive the chart's
  embedded data, or (b) accept static demo numbers. Driving native chart XML/embedded
  workbook is non-trivial.
- Risk: medium — either we ship designer-fixed data (looks real, isn't data-driven) or we
  build chart-data injection (more work, more breakage surface).

## Option B — Skill-based chart image (concept borrowed from old mainline)

A `chart_generator` skill renders a line chart to PNG/SVG (e.g. matplotlib) and inserts it
into a reserved placeholder region.

- Pros: fully data-driven; decoupled from PowerPoint internals; reuses old-mainline
  *concepts* (not code); flexible chart types later.
- Cons: introduces a new rendering dependency + image-styling work to match template look;
  output is a **static image** (not natively editable); placeholder-region detection must
  be reliable; risk of off-style charts breaking the 1:1 feel.
- Risk: medium — new dependency + visual-consistency tuning; but isolated to one page.

## Option C — Hybrid (template frame + skill image into fixed region)

Template provides the chart **frame/style/axis/title area** as a clearly-named picture
placeholder; the skill generates only the chart image; the cloner inserts that image into
the fixed region; surrounding text is Kimi-generated and slot-filled as usual.

- Pros: best balance — on-style frame from designer + data-driven series from skill;
  contained to one named region; text stays native-editable; doesn't touch native-chart
  internals; aligns with existing slot/blueprint mechanics (add an "image slot" type).
- Cons: needs a small new capability (insert picture into a named region by shape_id) and a
  minimal chart-image skill; designer must reserve a clean placeholder.
- Risk: low–medium — small, well-scoped engine addition; image still static but framed to
  look native.

## Evaluation matrix

| Criterion | A (native clone) | B (skill image) | C (hybrid) |
|---|---|---|---|
| POC speed | fast IF static data ok | medium | medium |
| Visual quality | highest | variable | high |
| Stability | high (static) / low (data-inject) | medium | medium-high |
| Designer workload | high (native chart) | low | medium |
| Data requirements | low (static) | needs series data | needs series data |
| Editability | native | static image | native text + static image |
| Risk to 1:1 style | low | medium | low |
| Helps t5 reach 4.5+ | yes (cosmetic) | yes (data-driven) | yes (both) |

## Recommendation

- **Recommended: Option C (Hybrid).** Reserve a named picture placeholder in the t5 master
  for one trend page; add a minimal `chart_generator` skill (line chart → PNG styled to the
  palette) plus a cloner "insert picture into named region" path. This gives a data-driven,
  on-style trend page contained to a single page and a single new slot type — the smallest
  change that yields a believable 4.5 trend slide. Data can come from the source doc (once
  manual-mode doc grounding is fixed, per O2) or from Kimi-proposed series for the demo.
- **Fallback: Option A with designer-fixed data.** If we must demo this week, have the
  designer ship a native line-chart slide with representative numbers; the engine clones it
  and only swaps the title/labels. Zero new code, fully native, accept non-dynamic data.

Defer Option B unless we later need many chart types or fully dynamic charts beyond one
trend page.

**Do not implement chart code yet** — await Jackie/arbitrator approval of the route.

— End O3 —
