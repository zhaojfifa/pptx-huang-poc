# PR-Q2H — Final T5/T6 Baseline Reproduction & Deployment Readiness

Date: 2026-05-24 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Reproduction + reporting only. No new chart skill, no T6 redesign, no 1.1/1.2 numbering, no
prompt rewrite, no mainline fusion, no deployment execution. No code changed this PR.

Decision recorded: **T5 = official POC main route (~4.5)**; **T6 = backup / chart-capability
demo (~4.3)**.

## Scope A · T5 final rerun (job 92, business, id 19, grounded example)

| # | Check | Result |
|---|---|---|
| 8 | final PPTX opens | ✅ 12 slides (`output/job_92_final.pptx`) |
| 6 | agenda consistency | ✅ `pass`, unmatched 0 (section_id) |
| 7 | typography polish | ✅ 2 tables audited, body never > header, text hierarchy capped 2 inversions |
| 3 | residue P6/P9/P11 | P6 textboxes: **VPN, SD-WAN**; P9: none; P11: none |
| 3b | overall residue (incl. tables) | **7 hits** — P6 (VPN, SD-WAN) + **P8 table headers** (是否模型, 指标规则, 模型场景, 1模型, 多个规则) |
| 4 | table header / first-column alignment | **inherit (NOT centered)** on both tables (slides 8, 9) — Q2G centers only confidently-numeric body columns, not header/first-col |
| 1 | P5 title/header L-R overflow | **render-time — needs visual review** (programmatic shapes look in-range; overflow not detectable from the .pptx) |
| 2 | P6 architecture text overlap | **render-time — needs visual review** (plus VPN/SD-WAN residue noted) |
| 5 | general overflow / overlap | **render-time — needs visual review** |

**Light fixes applied:** only those already in the polish layer ran (typography cap +
placeholder cleanup); no new functionality added (per scope). **Not auto-fixable here:**
the 7 residue hits and table header/first-col centering originate in the **t5 master** /
require a small alignment enhancement — both deferred (see recommendation).

## Scope B · T6 reproduction baseline (job 94, tech_blue, id 23, 14 pages)

| # | Check | Result |
|---|---|---|
| 6 | final PPTX opens | ✅ 14 slides (`output/job_94_final.pptx`) |
| 1 | P7 native chart works | ✅ 6 native COLUMN_CLUSTERED charts |
| 2 | native chart rebind intact | ✅ `charts_total 6, rebound 6, skipped_external 0, errors 0, slides [7]`; series `营收(亿元)` rebound |
| 3 | agenda consistency | ✅ `pass`, unmatched 0 |
| 4 | contamination | ✅ **clean (0 hits)** |
| 5 | complex structure stable | ✅ polish: agenda_filled 3, numbering_stripped 2, placeholders_cleared 13; typography 3 tables, no regressions |

T6 reproduces cleanly and demonstrates native charts + complex structure + agenda
consistency. Not pushed toward 4.5 (out of scope); kept as backup/demo.

## Scope C · Deployment readiness snapshot

- **Main POC route:** **T5 / 商务风格** (DB id 19, 12 pages).
- **Backup / capability-demo route:** **T6 / 科技蓝风格** (DB id 23, 14 pages; native charts).

### Runtime dependencies (verified on this host)
| Dependency | Status on dev host |
|---|---|
| Python env | `.venv_huang` Python **3.13.5** (pyenv) |
| MySQL / template index | **MySQL 9.6.0 (Homebrew)**, DB `pptx_agent`; template_pages indexed for id 19 (12p) & id 23 (14p) |
| templates_storage | `templates_storage/t5.pptx`, `t6.pptx` present (gitignored, local-only) |
| LibreOffice / soffice | `/opt/homebrew/bin/soffice` present (template screenshots) |
| pypdfium2 | installed 5.8.0 (in requirements.txt) |
| Chinese fonts | macOS PingFang present; **deploy host must install CJK fonts** (PingFang/YaHei/Noto Sans CJK/Source Han) for correct render & screenshots |
| Kimi / Moonshot API | via gitignored `.env` (`LLM_API_KEY`, `LLM_BASE_URL=api.moonshot.cn`, `LLM_MODEL=kimi-k2.6`) — **key must be rotated; previously exposed** |
| output storage | `output/` dir (gitignored) |

### Deployment recommendation
- **Proceed to deployment prep IF T5 manual review passes** — i.e., a human confirms P5/P6
  overflow/overlap are acceptable or fixed template-side.
- **T6 kept as fallback / capability demo.**
- **Pre-deployment blockers to clear first (not in this PR):**
  1. **t5 master de-branding** — removes the remaining 7 residue hits (P6 VPN/SD-WAN + P8
     table headers 是否模型/指标规则/模型场景/1模型/多个规则).
  2. **Table header + first-column centering** — small polish-layer enhancement (currently
     only numeric body columns are centered).
  3. **P5/P6 overflow/overlap** — template tuning or a light render constraint.
  4. **Portability**: bundle/seed templates_storage + rebuild template index on the deploy
     host (DB + masters are currently local-only); install CJK fonts; provision a rotated
     Kimi key; confirm SSH/push path.

## Baseline artifacts (gitignored, local)
- T5 main: `output/job_92_final.pptx` + `logs/job_92/*` (agenda/typography/placeholder/contamination reports).
- T6 demo: `output/job_94_final.pptx` + `logs/job_94/*` (incl. native_chart_rebind_report).

## Status
Both baselines reproduce and open; T6 clean; T5 carries known, separately-scoped
template-residue + alignment items. **Hand off to human review of T5; on pass → deployment
prep** (clearing the blockers above first).

— End PR-Q2H —
