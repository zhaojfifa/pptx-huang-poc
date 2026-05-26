# P0 · Content Baseline Smoke Check — Implementation & Validation Report

Date: 2026-05-26 · Repo: `/Users/tylerzhao/Code/pptx-huang-poc` · Baseline tag
`poc-4.5-q3c-content-baseline-job28` (`155b760`).
**P0 only. Read-only script. No generation/behavior change, no residue cleaning, no deploy, no reindex.**

## 0. Purpose
Guard the accepted job_28 content-quality baseline before any agenda/table/custom fix, so a future
change that thins body content (as Q3d did) is caught immediately. The script is a **read-only gate** —
it inspects a generated `.pptx` and asserts body-content volume has not collapsed; it reports template
residue as an advisory **WARN** but **never cleans it** (global residue cleaning caused the Q3d
regression and is explicitly out of scope).

## 1. Deliverable
- `scripts/poc_content_baseline_smoke.py` — read-only checker (python-pptx only; no LLM/DB/web import).
- This report.

Do-not-touch honored: no change to `content_generator`, `content_normalizer`, `template_cloner`,
`deck_polish`, `typography_polish`, or any generation behavior. The script opens the file read-only and
prints a summary; it never writes the pptx or any state.

## 2. What it checks
1. **opens** — `Presentation(path)` succeeds.
2. **slide_count == expected** (default 12).
3. **P4 text chars ≥ floor** (default 150) — body text not collapsed.
4. **P8 non-empty table cells ≥ floor** (default 12).
5. **P9 non-empty table cells ≥ floor** (default 12).
6. **contamination** — scans all slides for known residue tokens (穿透式监管, VPN, SD-WAN, 是否模型,
   模型场景, 分析场景, 全级次, 全链条, 全要素, 国资委, 中国移动/中移, CMCC, OneCity) and **reports counts
   as WARN only**. Never fails on residue, never modifies the file.
7. **PASS / WARN / FAIL** summary; exit 0 for PASS/WARN, exit 1 for any FAIL (CI-gateable).

No visual-quality scoring is claimed — only structural volume thresholds.

## 3. Thresholds & derivation
Conservative floors set **below** the accepted baselines so a healthy deck passes and only a real
collapse fails (baselines: cloud job_28 ≈ local job_121 → P4 ≈ 367 chars, P8 ≈ 30 cells, P9 ≈ 24 cells):
`expected_slides=12, p4_min_chars=150, p8_min_cells=12, p9_min_cells=12`. All overridable via flags
(`--expected-slides/--p4-min-chars/--p8-min-cells/--p9-min-cells`). The P4/P8/P9 page-number checks
target the **12-page T5 layout**; an 8-page quick-mode deck has a different page profile (its table
pages are not at positions 8/9), so run it with the 12-page profile only, or adjust expectations.

## 4. Read-only guarantees
- Imports only `pptx` (+ stdlib). Does NOT import `web.app`/agent/LLM/DB.
- Opens the pptx, reads text frames + table cells; **no `.save()`, no edits, no residue cleaning,
  no network, no DB**. Safe to run anytime, locally or on cloud, against any generated deck.

## 5. Local validation results
| Deck | slides | P4 chars | P8 cells | P9 cells | residue | OVERALL | exit |
|---|---|---|---|---|---|---|---|
| **job_121** (post-revert / Q3c baseline) | 12 ✅ | 367 ✅ | 30 ✅ | 24 ✅ | WARN (穿透式监管×11 …) | **WARN** | 0 |
| job_119 (Q3d-era, residue-cleaned) | 12 ✅ | 300 ✅ | 27 ✅ | 24 ✅ | none | PASS | 0 |
| job_113 (Q3d-era) | 12 ✅ | 353 ✅ | 30 ✅ | 24 ✅ | WARN | WARN | 0 |
| job_112 (8-page) @ expected=12 | 8 ❌ | 290 | 0 ❌ | 0 ❌ | WARN | **FAIL** | 1 |
| job_112 (8-page) @ `--expected-slides 8` | 8 ✅ | 290 ✅ | 0 ❌ | 0 ❌ | WARN | FAIL | 1 |

Reading:
- **job_121 (the baseline) passes all body thresholds and only WARNs on residue** — exactly the accepted
  job_28 tradeoff (healthy body content + known template residue that we deliberately do NOT auto-clean).
- The **FAIL path works** (exit 1): wrong slide count and empty P8/P9 are flagged. The 8-page deck FAILs
  the table-cell checks because its layout has no table pages at positions 8/9 — confirming the 12-page
  profile is the right gate for the baseline (use a separate profile for 8-page).
- **Honest caveat:** the local Q3d outputs (job_119/113) did **not** collapse P8/P9 below the floor
  (local template 28's tables had few residue-token cells to blank), so the local runs do not reproduce
  the cloud P8/P9-missing regression. The cloud regression is template-data-specific; the gate would
  still catch a real collapse (cells → ~0 < 12). **Recommend running this script on the cloud against
  job_28 to lock the real baseline thresholds.**

## 6. Usage
```bash
# newest local output:
python -m scripts.poc_content_baseline_smoke
# explicit deck:
python -m scripts.poc_content_baseline_smoke output/job_121_final.pptx
# custom thresholds (e.g. after cloud job_28 baselining):
python -m scripts.poc_content_baseline_smoke <pptx> --p4-min-chars 200 --p8-min-cells 20 --p9-min-cells 18
```
Recommended workflow for P1/P2/P3: run the smoke **before and after** each change against a freshly
generated 12-page T5; require body checks stay PASS (residue WARN is acceptable). Block the change if
any body metric drops to FAIL.

## 7. Status / next
P0 implemented + validated locally (read-only; no behavior change). Recommend committing
`scripts/poc_content_baseline_smoke.py` + this report (explicit paths), then — after review — proceed to
P1 (agenda-slide-only fix), running this smoke as the regression gate. No push/deploy in this round.

— End P0 report (read-only; no code-behavior/DB/template/deploy change) —
