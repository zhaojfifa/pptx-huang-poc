# POC 4.5 Huang — Deployment Readiness Checklist

Date: 2026-05-25 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Preparation only — **no deployment executed, no generation logic changed, no templates
touched, .zshrc untouched.**

## 1. Git state

- **HEAD:** `13bd8b0` — `fix(poc): custom template index decode and closure baseline`.
- **Tracking:** `main` is **ahead of `origin/main` by 14 commits** (origin/main = `1ec8a9f`).
- **Working tree:** clean except one untracked, unrelated `.zshrc` (intentionally left alone;
  never staged).
- **Staged forbidden artifacts:** none. No `.env`, logs, output, PPTX, PNG,
  templates_storage, DB dump, or `.zshrc` is tracked or staged.
- `.env.example` is tracked but is the **sanitized placeholder** (verified: no `sk-` key).

## 2. Push checklist (14 local commits, oldest → newest)

| # | Commit | Message |
|---|---|---|
| 1 | f7a4440 | feat(poc): add source grounding and runtime portability preflight |
| 2 | 438fe9a | docs(poc): record huang quality sprint reviews |
| 3 | f54bf08 | feat(poc): add quality gates and contamination scan |
| 4 | 7f22623 | fix(poc): handle same-file custom template analysis |
| 5 | f1e4ba9 | feat(poc): add agenda consistency guard |
| 6 | 3dfb605 | feat(poc): enforce agenda-to-slide outline structure |
| 7 | 550e990 | chore(poc): add pypdfium2 for template screenshots |
| 8 | e0d204d | docs(poc): record chart and template validation reviews |
| 9 | 2bce837 | feat(poc): integrate native chart rebind for t6 |
| 10 | ff5d4b1 | feat(poc): polish agenda and template slot filling |
| 11 | d9fbbc3 | feat(poc): add default typography hierarchy polish |
| 12 | f0d8e9e | docs(poc): record final t5 t6 baseline reproduction |
| 13 | 48769b7 | feat(poc): clean t5 residue and align tables |
| 14 | 13bd8b0 | fix(poc): custom template index decode and closure baseline |

- **Secret scan over the full unpushed diff (`1ec8a9f..HEAD`): no live key.**
- **No forbidden/local artifacts** in the unpushed file set (code + docs + `requirements.txt`
  + `.env.example` placeholder + `data/samples/*.md` + `scripts/`). Confirmed binaries/logs
  excluded by `.gitignore`.
- **Push command (when a key is available):** `git push origin main`
  (this machine has **no outbound SSH key** → push must run from Jackie's authenticated host).

## 3. Runtime carry checklist (templates + DB are local-only)

| Item | Action on deploy host |
|---|---|
| `templates_storage/t5.pptx` (de-branded master) | **carry** (gitignored; not in repo). Required for T5 main route. |
| `templates_storage/t6.pptx` | carry (backup/chart demo). |
| custom uploads (`templates_storage/custom_*.pptx`) | **do not carry** — these are per-upload runtime artifacts; the host generates its own on upload. Seed policy = none. |
| MySQL template rows | **T5 id 24** (required), **T6 id 23** (backup), custom id 26 (optional/demo only). |
| DB import vs re-analyze | **Recommended: re-run the analyzer on the carried masters on the host** (`python -m template_analyzer.analyze_template --input templates_storage/t5.pptx --name 商务风格`, then t6) → rebuilds template_pages + screenshots cleanly and avoids a cross-host DB dump. Alternative: `mysqldump` the `templates`/`template_pages` rows for id 23/24 and import (faster, but carries absolute `file_path`s — re-run `scripts/migrate_template_paths.py` after import to repoint to host paths). |
| Verify after seed | `_resolve_template("商务风格")→` clean id with 12 pages, residue 0; `("科技蓝风格")→` 14 pages. |

## 4. Environment checklist

| Dependency | Required | Dev-host status |
|---|---|---|
| Python | 3.10+ (markitdown needs ≥3.10); dev uses **3.13.5** | ✅ |
| `requirements.txt` | fastapi, uvicorn[standard], python-pptx, mysql-connector-python, openai, markitdown, **pypdfium2**, python-docx, PyPDF2, pydantic, jinja2, python-multipart | ✅ pinned |
| LibreOffice / soffice | required for template screenshots (PPTX→PDF) | ✅ `/opt/homebrew/bin/soffice` |
| pypdfium2 | required (PDF→PNG rasterize) | ✅ 5.8.0 |
| CJK fonts | **required on host** for correct CJK render + screenshots (PingFang / Microsoft YaHei / Noto Sans CJK / Source Han) | dev has PingFang; **install on Linux host** |
| MySQL | server reachable; DB `pptx_agent` | ✅ 9.6.0 (Homebrew) |
| Kimi/Moonshot env | `.env`: `LLM_API_KEY`, `LLM_BASE_URL=https://api.moonshot.cn/v1`, `LLM_MODEL=kimi-k2.6`, `MYSQL_*` | ⚠️ **rotate key** (previously exposed); never commit `.env` |
| output storage | `output/` (generated PPTX) — ensure writable + retention policy | ✅ gitignored |
| logs path | `logs/` (job checkpoints + `template_screenshots_*`) — writable; size growth to monitor | ✅ gitignored |
| upload size limits | set a reverse-proxy / FastAPI body limit for `/api/custom-template/upload` & source upload (e.g. cap PPTX ~50 MB); custom analyze can take minutes (vision per page) → set generous request/worker timeouts | **configure on host** |

## 5. Deployment route recommendation

- **Start with Alibaba Cloud (primary).** Reasons: target users / data are domestic; the
  Kimi/Moonshot API (`api.moonshot.cn`) and any later 阿里云 services have low-latency,
  compliant access from within-region; easier to provision a Linux host with LibreOffice +
  CJK fonts + MySQL; avoids cross-border latency/blocking for the LLM calls that dominate
  generation time.
- **Keep Render / R2 as fast backup.** Reasons: quick to stand up for a demo URL / file
  hosting (R2 for output PPTX), useful if Alibaba provisioning is delayed; but cross-border
  latency to `api.moonshot.cn` and CJK-font/LibreOffice setup make it secondary.
- **First action:** provision an Alibaba Linux host, install Python 3.10+ / MySQL /
  LibreOffice / CJK fonts, `pip install -r requirements.txt`, carry the de-branded masters,
  re-run the analyzer to seed the index, set a rotated `.env`, then smoke-test `/`, `/custom`
  upload→analyze→generate.

## Pre-deploy gate (all must pass before deploy)
1. Rotate the Kimi key. 2. Push the 14 commits (from an authenticated host). 3. Carry masters
+ seed DB (re-analyze) + install CJK fonts on host. 4. Confirm `/custom` upload flow on host.
5. Human visual sign-off of T5 (P5/P6 render-level overflow).

— End deployment readiness checklist (no deployment executed) —
