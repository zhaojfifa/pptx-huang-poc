# PR-Q2G — Default Typography & Slot Hierarchy Polish

Date: 2026-05-24 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
CodexL: GO WITH CONDITIONS. Conservative **post-render** layer only — no global font rewrite,
no master-style changes, no native-chart-object changes, no re-index. Validated on T6 job 87
and T5 job 89.

## Implementation (`core/typography_polish.py`, post-render)

- **A · `normalize_table_typography`** — per table:
  - header band = min explicit run size across header cells; any **body run larger than the
    header band is capped down to it** (header font ≥ body font).
  - **confidently-numeric columns** (every body cell matches a number/%/decimal) are
    **center-aligned** consistently.
  - header-row alignment is **reported**; fills/borders/colors untouched. Acts only on
    explicit run sizes (inherited `None` left alone).
- **B · `audit_and_fix_text_hierarchy`** — per slide: audit font-size bands by role
  (title vs body; tables/charts skipped; role/size-uncertain skipped). Only correction is
  **capping body text whose explicit size exceeds the slide title** (clear inversion).
  Reports changed-shape count.
- **C · chart restraint** — charts are **not touched** (style/axes/legend/colors/type/geometry
  preserved). P7 rebind from Q2F unchanged; surrounding placeholder text already cleared.

Runs after deck_polish, for all decks. Writes `logs/job_xx/typography_audit_report.json`.

## Scope D · Validation

### T6 (tech_blue) — job 87
| Check | Result |
|---|---|
| final PPTX opens | ✅ 14 slides |
| agenda consistency | ✅ `pass`, unmatched 0 |
| contamination | ✅ clean (0) |
| placeholder cleanup | ✅ 13 cleared, agenda_filled 3, numbering_stripped 2 |
| table typography audit | ✅ 3 tables — slide4 (hdr_min 12pt, numeric cols [2,3,9]), slide5 (hdr 14pt), slide11 (hdr_min 10pt, **1 body run capped**, numeric cols [1-6]) |
| text hierarchy audit | ✅ text_changed 0 (no inversions) |
| chart audit unchanged | ✅ `charts_total 6, rebound 6, errors 0` (P7 native, untouched) |
| no external chart skill | ✅ |
| no re-index | ✅ (master unchanged) |

### T5 (business) — job 89
| Check | Result |
|---|---|
| final PPTX opens | ✅ 12 slides |
| agenda consistency | ✅ `pass`, unmatched 0 |
| contamination | ⚠️ **not clean — 7 hits** (VPN/SD-WAN/是否模型/指标规则/模型场景/1模型/多个规则) = **t5 master residue**, a known, separately-scoped de-brand task (out of Q2G) |
| placeholder cleanup | clean (0 to clear this run; agenda_filled 0 — no mis-filled generic item slots detected) |
| table typography audit | ✅ 2 tables (slides 8,9; hdr_min 16pt; bodies already ≤ header) |
| text hierarchy audit | ✅ **text_changed 2** (two body shapes larger than title → capped) |
| native charts | ✅ 0 (T5 has none); no rebind report written → chart logic correctly skipped T5 |

## Acceptance summary

- Table: header font ≥ body font enforced (T6 slide11 capped 1; others already compliant);
  numeric columns centered; header alignment reported; fills/borders/colors preserved; no
  global cell-style rewrite. ✅
- Text hierarchy: audit produced per slide with font-size bands; only clear title<body
  inversions capped (T5: 2, T6: 0); role-uncertain/inherited-size shapes skipped; no broad
  rewrite; agenda/chart/table pages not visibly regressed. ✅
- Chart: T6 native chart rebind unchanged (6/6/0); no chart-object style touched. ✅
- Both decks open; both agenda pass; audits exist; no external chart skill; no re-index. ✅

## Notes / honest gaps

- **T5 contamination (7 hits) persists** — it originates in the t5 master (unmapped shapes /
  table headers), not the engine; clearing it is the deferred **t5 master de-branding** PR,
  intentionally out of Q2G scope (CodexL: don't break master style).
- Typography corrections are intentionally minimal (cap-only) to avoid master-style damage;
  many shapes inherit size (`None`) and are left untouched by design.
- T6 agenda page still exposes only 3 item slots (template limit) → 3 sections shown.

## Recommendation

Typography/slot hierarchy is normalized conservatively; T6 is structurally ~4.5 and
rendering control improved without master-style risk. Remaining before public deployment:
(1) **t5 master de-branding** (clears the 7 residue hits), (2) optional per-chart Kimi data,
(3) more agenda slots in the T6 master. Then proceed to deployment prep.

— End PR-Q2G —
