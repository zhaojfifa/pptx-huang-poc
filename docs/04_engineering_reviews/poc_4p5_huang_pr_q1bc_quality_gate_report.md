# PR-Q1b/Q1c — Quality Gate + Contamination Guard Report

Date: 2026-05-23 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Status: **complete, uncommitted** (awaiting commit per instruction).
Scope: t5/business POC path only. No line chart, no t6 deep work, no DB refactor, no
deployment, no old-repo, no template marketplace.

## What was added

Three **advisory** gates (log + persist warnings, never block — except a clearly empty
outline). No secrets are ever recorded (term hit *counts* only).

### Scope A · Outline quality gate (`_outline_quality_gate`)
Runs after outline generation (in `/api/poc/outline`) and again in `/api/poc/generate`
(persisted under the final job). Detects: duplicate/near-duplicate titles; empty/generic
titles; empty key_points on narrative slides; excessive generic phrasing; page-count /
template-page mismatch; and "grounding available but outline has no numbers/metrics".
Output → `logs/job_<id>/outline_quality_report.json` + `quality_warnings` in the API
response.

### Scope B · Slot fragmentation warning (`_slot_fragmentation_report`)
Reads the per-page blueprint (`TemplateStyleEngine`) and flags: very high slot count
(≥20), label-dominated pages (labels ≥ 2× content), small average content capacity (<30
chars), and narrative slides mapped onto dense-label pages. Advisory only — mapping logic
unchanged. Output → `logs/job_<id>/slot_fragmentation_report.json` +
`slot_fragmentation_flagged` in the generate response.

### Scope C · Final PPTX contamination scan (`_final_contamination_scan`)
After final render, scans visible text + table cells + speaker notes + docProps for the
forbidden/suspicious term list (穿透监管/VPN/SD-WAN/集团专线/是否模型/指标规则/模型场景/
1模型/多个规则/CMCC/OneCity/template_id/Huang/Kimi/localhost/sk-). Records **counts only**
(never the matched secret). Output → `logs/job_<id>/final_contamination_report.json`;
`contamination_clean` + `contamination_hits` surfaced in the status response.

Files changed (code): `web/app.py` only (3 helper functions + wiring in `poc_outline`,
`poc_generate`, `_run_generation`). No other code touched.

## Scope D · Validation (t5/business, grounded, example doc → job_64)

| Requirement | Result |
|---|---|
| `outline_quality_report.json` exists | ✅ `logs/job_64/` |
| `slot_fragmentation_report.json` exists | ✅ `logs/job_64/` |
| `final_contamination_report.json` exists | ✅ `logs/job_64/` |
| final PPTX opens | ✅ |
| page count = 12 | ✅ |
| no secrets / local artifacts committed | ✅ (reports stay in gitignored `logs/`) |

### Gate outputs (job_64)
- **Outline quality:** 2 warnings — `generic_title: slide 12 '谢谢'`,
  `empty_key_points: slide 8 (chart)`. Both expected/benign (ending slide; chart slide).
  `unusable=false`.
- **Slot fragmentation:** flagged pages `[3,4,5,6,9,10]`. Matches O1/O2 findings: slide 6
  (25 content / 37 label, avg cap 18 → very_high + small_capacity), slide 10 (2 content /
  42 label → very_high + label_dominated + small_capacity), slides 3/4/5/9 label_dominated.
- **Contamination:** 8 hits — `VPN×1, SD-WAN×1, 是否模型×2, 指标规则×1, 模型场景×1, 1模型×1,
  多个规则×1`. Located in slide 6 textboxes (VPN/SD-WAN) and table cells (the rest).

### Suspicious-term comparison vs job_56 / job_62 (Requirement #7)

| Job | total contamination hits |
|---|---|
| job_56 (pre-grounding) | 8 |
| job_62 (grounded) | 8 |
| job_64 (this PR, grounded + gated) | 8 |

**Honest result: the count did NOT decrease (8 → 8).** This is expected and important:
the contamination is **identical across all three runs**, proving it is **baked into the
t5 master template** — these terms live in template shapes/table cells that the cloner
never maps or overwrites (dense-label / table regions), so they pass through unchanged
every generation. **This PR adds detection/measurement, not removal.** Removal requires
**template de-branding / cleaning of the t5 master** (an explicitly deferred, separate
task), or extending mapping to overwrite those regions. The value delivered here: the
contamination is now visible, counted, root-caused (= template master), and surfaced in
the status response as a baseline (8 hits) to drive that next fix.

## Acceptance (中文验收口径)

1. t5 商务蓝 12 页 PPT 仍能正常生成 — ✅ job_64, 12 slides, opens OK.
2. 日志含三份报告（大纲质量 / slot 碎片化 / 污染扫描）— ✅ all in `logs/job_64/`.
3. 最终 PPT 是否减少旧模板污染词 — ⚠️ **未减少（8→8）**：污染来自 t5 母版本身，本轮只做"检测"，
   "清除"需后续模板去品牌化 PR（属本轮 out-of-scope）。现已可量化并定位根因。
4. 内容是否比 job_56/job_62 更适合经营汇报 — ✅ grounding retained (job_64 carries the
   same source-backed figures as job_62: 3,612 / 198 / 5,180 / 2,340 / 45亿 / 42%), and the
   gates now flag the weak structural pages (6/10) for targeted polish.

## Recommended next step

Given root-cause = template master, the highest-ROI follow-up is a **t5 master
de-branding / template-cleaning pass** (remove VPN/SD-WAN/是否模型/指标规则… from the
master's residual shapes and table cells), after which the contamination scan should drop
to 0. This is the natural PR-Q1d, separate from PR-Q2 (line chart) / t5 final polish.

## Working-tree state (uncommitted)
- Modified: `web/app.py`.
- New: `docs/04_engineering_reviews/poc_4p5_huang_pr_q1bc_quality_gate_report.md`.
- Reports under `logs/job_64/` are gitignored (not committed). HEAD `438fe9a`.

— End PR-Q1b/Q1c —
