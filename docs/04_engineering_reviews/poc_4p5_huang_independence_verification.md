# Huang POC — Independence Verification (read-only)

Date: 2026-05-23 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Read-only: no code/DB changes, nothing committed, no secrets printed.

## Check A · Database independence

1. **Runtime DB backend:** external **MySQL** only (`database/db.py` uses `mysql.connector`;
   server reports `Homebrew MySQL 9.6.0`). No SQLite, no repo-internal DB file.
2. **DB config variables actually used:** `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`,
   `MYSQL_PASSWORD`, `MYSQL_DB` (`config/settings.py`). Password not printed.
3. **DB name / path:** database name `pptx_agent` on `127.0.0.1:3306`. No file path (server DB).
4. **`data/*.db|sqlite|sqlite3`:** none exist; no SQLite usage anywhere in the codebase.
5. **Must generation depend on external MySQL?** **Yes.** `init_db()` runs at startup and
   every step uses `GenerationJobDAO/TemplateDAO/TemplatePageDAO` → `get_connection()` →
   MySQL. There is **no non-MySQL fallback** (the only `except Error` blocks log/re-raise).
6. **If MySQL is off, can it still generate?** **No** — startup `init_db()` and all
   job/template/page reads/writes would fail. (Not tested by stopping MySQL; confirmed by
   code path — there is no in-memory/SQLite alternative.)

→ **Independent DB: PARTIAL.** Runtime CODE is in-repo, but it requires an **external MySQL
service** (not bundled, not reproducible from a clone). The shared `pptx_agent` DB also
still holds legacy rows (ids 1–12) pointing at old-repo paths — inactive for t5/t6 but
present.

## Check B · Template asset independence

| | business / t5 | tech_blue / t6 |
|---|---|---|
| active row | id 15 | id 16 |
| file_path | `…/pptx-huang-poc/templates_storage/t5.pptx` | `…/pptx-huang-poc/templates_storage/t6.pptx` |
| in current repo | ✅ | ✅ |
| contains `ppt-agent-poc` | ❌ no | ❌ no |
| real PPTX | ✅ `Microsoft PowerPoint 2007+` | ✅ `Microsoft PowerPoint 2007+` |
| symlink/alias/stub | ❌ regular file | ❌ regular file |
| slide count | 12 | 8 |

→ **Independent template assets: YES.**

## Check C · Template index independence

1. `template_pages` records are in the current runtime DB (`pptx_agent`).
2. t5 (id 15): **12** page records. 3. t6 (id 16): **8** page records.
4. Rebuildable: the analyzer `template_analyzer/analyze_template.py` **is in this repo** and
   the masters are in-repo → the index can be regenerated locally.
5. Old-repo analyzer-output dependency: **none** — 0 page rows for id 15/16 contain any
   `ppt-agent-poc` string (layout_json / visual_json / generation_hints / markdown_content).

→ **Independent template index: PARTIAL.** Content is clean of old-repo refs and rebuildable
from in-repo analyzer+masters, but the **records themselves live only in the external MySQL**
(not in the repo); a fresh clone has no index until re-seeded/re-analyzed.

## Check D · Source grounding independence

1. Example doc path: `data/samples/baosteel_2025_example.md` — **in current repo** ✅.
2. Upload endpoint `/api/poc/source/upload` parses the uploaded file → markdown via
   `DocumentProcessor` (markitdown), cached by token ✅ (smoke: 970 chars, 12 key_facts).
3. Grounding artifacts: `logs/job_62/document_markdown.md` (3,155 chars) exists and begins
   with the auto `关键事实/数据` block; `doc_summary` + per-slide relevant doc are derived
   from it. ✅
4. Per-slide prompt grounding: logs show `doc_present=True` for all 12 slides. ✅
5. External old-repo file needed: **none** (example is in-repo; uploads are user-provided).

→ **Independent source grounding: YES.**

## Check E · Full generation independence (job_62)

1. Generated from current-repo runtime ✅.
2. Template resolved from current-repo path (`…/pptx-huang-poc/templates_storage/t5.pptx`) ✅.
3. Source doc from in-repo sample (example mode) ✅; upload-token path also available.
4. Output under current repo: `output/job_62_final.pptx` ✅.
5. Old-repo paths in selected_template / logs / metadata: **none** — `selected_template.json`
   file_path and screenshots_path are in-repo; scanned all 54 `logs/job_62` artifact files →
   **0** containing `ppt-agent-poc`.

→ **Independent generation (of the old REPO): YES.** Generation no longer touches
`ppt-agent-poc` in any way. (It still requires the external MySQL service — see Check A.)

## Final Answer

- **Independent DB: PARTIAL** — external MySQL service required; no repo-bundled/SQLite DB;
  legacy old-path rows still present (inactive).
- **Independent template assets: YES** — real in-repo PPTX, 12 / 8 slides, no old-repo path.
- **Independent template index: PARTIAL** — clean & rebuildable, but persisted only in the
  external MySQL (not in the repo / not in a fresh clone).
- **Independent source grounding: YES** — in-repo example + working upload-parse path.
- **Independent generation: YES of the old `ppt-agent-poc` repo** (0 references); but
  **dependent on the external MySQL service** to run at all.

### Remaining dependency list
1. **External MySQL service** (`pptx_agent` @ 127.0.0.1:3306) — hard dependency, no fallback;
   generation cannot run without it.
2. **Template masters + page index are local-only** — masters in `templates_storage/`
   (gitignored) and page records in local MySQL; a fresh clone has neither until re-seeded
   (run analyzer on the masters) — a future portability/seed task.
3. (Pre-existing, inactive) legacy DB rows ids 1–12 still reference old-repo paths; harmless
   to t5/t6 resolution.

### Whether safe to commit Q0+Q1a
**YES — safe to commit.** The Q0+Q1a changes (`.env.example` sanitize, `.gitignore`,
`scripts/migrate_template_paths.py`, source-grounding code + bundled example + docs) are
free of secrets and binaries and contain **no old-repo dependency**. The MySQL / index /
template-seed dependencies are **pre-existing infrastructure**, not introduced by these PRs,
and do not block committing the code. Caveats (separate follow-ups, not commit blockers):
fresh-clone runtime still needs MySQL + a template seed step; Jackie should still rotate the
previously-exposed Kimi key.

— End independence verification —
