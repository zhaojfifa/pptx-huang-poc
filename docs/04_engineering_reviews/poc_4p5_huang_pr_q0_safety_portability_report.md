# PR-Q0 — Safety & Runtime Portability Preflight Report

Date: 2026-05-23 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Status: **complete, uncommitted** (commit pending Jackie/arbitrator diff confirmation).

## 1. Sanitize `.env.example`

- Replaced the live-looking keys with placeholders (`your-kimi-api-key-here`,
  `your-llm-api-key-here`); kept non-secret config keys (LLM_BASE_URL, LLM_MODEL, MySQL).
- Verification: `git grep "sk-…"` over tracked files → **no API key in any tracked file**.
- The live key was only ever in the working tree, **never committed** (HEAD `.env.example`
  had an empty placeholder). No secret appears in `git diff`.
- Local `.env` (gitignored) retains real values → runtime unaffected. Secrets not printed.
- ⚠️ Jackie should still **rotate** the exposed key manually (it was visible in chat).

## 2. Prevent accidental staging of local binaries

- Added to `.gitignore`: `data/*.pptx` and `data/**/*.pptx` (the `data/t5.pptx` 920-byte
  stub and `data/t6.pptx` are now ignored; not deleted). Non-binary `data/` content
  (`README.md`, `samples/`, `templates/`) stays trackable.
- `templates_storage/` and `static/previews/` were already ignored (confirmed).
- `git ls-files '*.pptx'` → **no PPTX tracked**. Real masters remain local-only under the
  approved `templates_storage/` location.

## 3. Fix runtime template source of truth

- Blocker: DB `templates` rows for the built-in styles pointed at OLD-repo absolute paths
  (`…/ppt-agent-poc/…/{t5,t6}.pptx`).
- Fix: added a minimal, **idempotent, repeatable** migration
  `scripts/migrate_template_paths.py` that repoints any t5/t6 row whose `file_path` is not
  already an in-repo master to `<repo>/templates_storage/{t5,t6}.pptx` (path recomputed
  from repo root each run → portable by re-running). No schema redesign; no row deletion.
- Applied: 4 rows repointed — ids 13/14/15 (商务风格→t5) and 16 (科技蓝风格→t6). Re-run is a
  no-op (idempotent confirmed).
- In-repo masters validated: `templates_storage/t5.pptx` (12 slides), `t6.pptx` (8 slides).
- Resolution check: `_resolve_template("商务风格")`→id15 (12p), `("科技蓝风格")`→id16 (8p),
  both `exists=True`, `old_repo=False`.

## 4. Acceptance

| Criterion | Result |
|---|---|
| git diff shows no secrets | ✅ (only placeholders in `.env.example`) |
| `.env.example` placeholders only | ✅ |
| no PPTX/log/output/db artifacts staged | ✅ (all gitignored; nothing staged) |
| active t5/t6 runtime independent of old ppt-agent-poc paths | ✅ (repointed) |
| one t5 smoke generation succeeds OR resolution passes | ✅ both — job_60: 12 slides, 2.69 MB, opens OK, reads in-repo master |

## 5. Working-tree state (uncommitted)

- Modified (tracked): `.env.example` (sanitized), `.gitignore` (data PPTX ignore).
- New (untracked): `scripts/migrate_template_paths.py`, `docs/04_engineering_reviews/*` docs.
- Ignored / not staged: `.env`, `data/*.pptx`, `logs/`, `output/`, `templates_storage/`.
- HEAD unchanged: `1ec8a9f`. No commit made (awaiting diff confirmation).

## 6. Notes / follow-ups (out of Q0 scope)

- Old-template contamination is real: the t5 smoke (job_60) still surfaced `穿透式监管` once
  (an unmapped slot retaining original template text — O1 §8). A final integrity gate +
  master de-branding is a later PR, not Q0.
- DB has duplicate `商务风格` rows (13/14/15); left intact per instructions
  (`_resolve_template` selects the 12-page id 15).

— End PR-Q0 —
