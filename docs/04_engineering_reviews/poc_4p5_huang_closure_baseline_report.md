# POC 4.5 Huang — Closure Baseline & Custom Template Validation (PR-Q2J)

Date: 2026-05-25 · Repo: /Users/tylerzhao/Code/pptx-huang-poc
Closure verification — no new capability added. One bug fix (custom index decode).

## Scope A · Closure baseline

### Main route — T5 / business
- Baseline output: **`output/job_96_final.pptx`** (12 slides), template id **24** (de-branded).
- Status: **official POC main baseline**. Clean: contamination 0, agenda consistency pass,
  table header + first-column centered.
- Known remaining (iteration items, not blockers): agenda page shows only 3 item slots
  (template limit); P5 header L-R overflow and P6/P9/P10 overflow/overlap are render-time
  layout issues → template-level tuning.

### Backup route — T6 / tech_blue
- Baseline output: **`output/job_97_final.pptx`** (14 slides), template id **23**.
- Status: **backup / chart-capability + complex-structure demo**. Native P7 charts
  (rebind 6/6), agenda pass, contamination clean.
- Known remaining: reaching 4.5 needs major template/structure rework → not current main.

### Current decision
- Stop broad optimization. Proceed to custom-template validation (below) and deployment prep.

## Scope B · Custom PPTX template upload flow validation

Validated the full `/custom` chain end-to-end (frontend endpoints + real pipeline).

A small 3-page template first exposed and let us **fix a real bug**: `_build_template_index`
called `json.loads()` on `layout_json`/`visual_json`, but `TemplatePageDAO.get_by_template`
already decodes them → `TypeError` → status 500. Fixed to tolerate dict-or-str. Then a clean
12-page custom template (uploaded copy of the de-branded T5 master) ran the full real path:

| Step | Result |
|---|---|
| 1. Upload PPTX | ✅ token `83570a7e59`, page_count 12 |
| 2. Analyze | ✅ subprocess analyzer; **no SameFileError** (guard fired) |
| 3. Screenshots | ✅ 12 PNGs (`logs/template_screenshots_26/`) |
| 4. Template index | ✅ template_id **26**, 12 pages indexed |
| 5. Frontend page info | ✅ index returns page_type/slots/thumbnails/warnings; thumbnail endpoint HTTP 200 |
| 6. Generate outline | ✅ **source=kimi**, job 98, 12 pages (real path, ≥6 pages) |
| 7. Generate final PPTX | ✅ job 99, state=done |
| 8. Final PPTX opens | ✅ `output/job_99_final.pptx`, 12 slides, 3.36 MB |
| 9. No SameFileError | ✅ |
| 10. No old-repo path | ✅ file = `templates_storage/custom_83570a7e59.pptx`, in-repo |

Recorded: template_upload_id `83570a7e59`; analyzed page count 12; screenshot count 12;
new template_id 26; output `output/job_99_final.pptx`; **frontend chain completed** (agenda
pass, contamination clean on this de-branded source).

Note: a template with **< 6 analyzed pages** falls back to a mock outline (job=None) — small
uploads won't trigger real generation (`_MIN_USABLE_PAGES = 6`). Advisory index warning on a
dense page flagged a residual term (`集团专网`) for cleanup — index hint only, not an output
contamination hit.

## Scope C · Deployment readiness snapshot

- **Main baseline:** T5 `output/job_96_final.pptx` (id 24).
- **Backup baseline:** T6 `output/job_97_final.pptx` (id 23).
- **Custom-upload chain:** validated (id 26, `output/job_99_final.pptx`).

### Runtime dependencies (verified on dev host)
| Dependency | Status |
|---|---|
| Python | `.venv_huang` Python 3.13.5 (pyenv) |
| MySQL | 9.6.0 (Homebrew), DB `pptx_agent` |
| templates_storage | t5/t6 masters + custom_* (local-only, gitignored) |
| template index / seed | DB rows id 24 (T5), 23 (T6), 26 (custom demo) — local |
| LibreOffice / soffice | `/opt/homebrew/bin/soffice` |
| pypdfium2 | 5.8.0 (in requirements.txt) |
| CJK fonts | macOS PingFang present; **deploy host must install CJK fonts** |
| Kimi key | gitignored `.env`; **must rotate (previously exposed)** |
| output storage | `output/` (gitignored) |

### Deployment blockers
1. **Rotate the Kimi/Moonshot key** (previously exposed in chat).
2. **Push local commits** (this machine has no outbound SSH key; HEAD is local-only).
3. **Carry the de-branded T5 master + template index** to the deploy host (templates_storage
   + MySQL `pptx_agent` are local; re-seed/re-analyze on host, install CJK fonts).
4. **Confirm the upload-template flow on the deploy host** (LibreOffice + pypdfium2 + fonts
   present; the SameFileError fix + index-decode fix are in code).

### Recommended deployment path
- **Prepare Alibaba Cloud first** (primary).
- **Keep Render / R2 as fast backup.**
- Do not deploy yet — gated on the four blockers above + human visual sign-off of T5.

## Out-of-scope confirmation
No new chart skill, no further prompt optimization, no T5/T6 template changes; the only
re-index performed was for the **custom upload validation** (id 26), as permitted. No
deployment executed. `.zshrc` untouched.

— End closure baseline (PR-Q2J) —
