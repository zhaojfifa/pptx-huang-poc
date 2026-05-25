# Q3d · Outline Fidelity & Stability Fix — Validation Report

Date: 2026-05-25 · Repo: `/Users/tylerzhao/Code/pptx-huang-poc` · Branch: `main`
**Local validation only. No push, no deploy, no t5_new reindex.** Built on Q3c (`6bcfa20`). No new
features, no UI restructure, no Q3c-3 visual optimization. 3 code files changed (+report).

## 0. Verdict
Cover and agenda now render from the confirmed outline (single source of truth); the cover shows the
edited title, the agenda shows the **exact** body section_titles; known template residue is
hard-cleaned (12-page contamination went to **0 hits**); failures surface as clear job errors.
One documented template-side limitation remains (agenda has fewer item slots than sections). **Ready
for review.**

## 1. Files changed
| File | Scope | Change |
|---|---|---|
| `web/app.py` | A,B,C,D,E | effective_outline.json + agenda key_points ← deduped section_titles; cover/agenda fidelity wiring into `polish_deck`; `_safe_str` coercion in `_cards_to_slides`; job error on failure; residue terms added to `_FORBIDDEN_TERMS`/`_POLLUTION_KW` |
| `core/deck_polish.py` | B,C,E | `fix_cover_slide` (targeted cover fill); `fill_agenda_deterministic` (overwrite agenda item slots with exact section_titles); `clear_known_residue` (hard-clean) |
| `skills/skill_llm/llm_skill.py` | D | `_strip_json_fences` + fenced/prose-tolerant `chat_structured` with one bounded re-ask and a clear `ValueError` |

## 2. Scope A — outline single source of truth
- `/api/poc/generate` saves **both** `logs/job_xx/confirmed_outline.json` (verbatim from the editor)
  and `logs/job_xx/effective_outline.json` (what generation actually used), with an `_derivation`
  note. Verified: 12-page no-edit → `_derivation = ["identical to confirmed_outline"]`; 8-page edited
  → `_derivation = ["agenda slide 2 key_points ← deduped body section_titles (5 items)"]`.
- Generate consumes the confirmed cards verbatim (`_cards_to_slides`); the only derivation is the
  agenda items (from body section_titles), which is recorded. No re-construction of cover/title.

## 3. Scope B — cover fidelity ✅
- `fix_cover_slide` writes the confirmed page-1 `title` into the title-like shape (标题/title name,
  else topmost) and `points[0]` into the subtitle shape — independent of (mis-)detected blueprint slots.
- **Validated:** 8-page edited cover title `Q3D封面标题验证` → **present on final slide 1** (PASS).
  12-page default → slide 1 shows real title `宝钢2025年度经营复盘` + subtitle (cover_set wrote 标题3 + 副标题5).

## 4. Scope C — agenda fidelity ✅ (with documented capacity caveat)
- Agenda items are derived from the deduped body `section_titles` (ordered by section_id), set as the
  agenda slide key_points (effective_outline), AND **`fill_agenda_deterministic` overwrites the agenda
  content-slot shapes with the exact section_titles** (replacing the LLM's rephrased/numbered items).
  closing/ending never enter the agenda; agenda add/delete already removed in Q3c-1 (edit-only + sync).
- **Validated:** 8-page edited → agenda shows `Q3D目录验证甲` + exact section_titles (PASS); 12-page →
  agenda shows `经营质效与财务表现 / 产能效率与智能制造 / 成本精益与运营优化` (exact section_titles).
- **Caveat (template-side, not a Q3d defect):** template 28's agenda page has only **3 item slots**,
  while decks produced 5–6 distinct sections, so only the first 3 are shown (logged as
  `agenda_overflow`). The shown items are exact section_titles. Closing the slot-vs-section gap
  (fewer sections, or a richer agenda layout) is **template-side / Q3e**, not stability.

## 5. Scope D — runtime stability
- `chat_structured` now tolerates ```json fences / prose-wrapped JSON, retries once with a stricter
  instruction, and raises a clear `ValueError("LLM 返回的不是合法 JSON…")` instead of a bare decode
  error. `chat()` keeps its bounded retry (SDK `max_retries=2` + connection backoff) — no infinite retry.
- `_cards_to_slides` coerces `title/section_title/slide_role/points` via `_safe_str` (list/dict/None →
  string), so a stray LLM type never breaks agenda matching / prompt injection / polish.
- Generation failures now write `logs/job_xx/generation_error.json` (error + type + traceback tail)
  and set `_GEN_STATUS[failed]` with a user `message` — the frontend `pollStatus`/`confirmGenerate`
  already render failed state + message (no silent fail, no stuck UI). Unit-tested fence/`_safe_str`
  behavior; outline/reanalyze error paths return clear 4xx (from Q3b/Q3c).

## 6. Scope E — residue & overflow stopgap
- Added `分析场景 / 全级次 / 全链条 / 全要素` to `_FORBIDDEN_TERMS` (scan) and `_POLLUTION_KW`
  (custom-index warnings); VPN / SD-WAN / 是否模型 already present.
- `clear_known_residue` (runs last) hard-cleans any shape/table-cell containing a known residue token
  (穿透式监管, VPN, SD-WAN, 是否模型, 分析场景, 全级次, 全链条, 全要素, 国资委, 中国移动, CMCC…).
- **Validated contamination:** 12-page (job 119) **clean=true, 0 hits** (20 residue shapes cleaned);
  8-page (job 117) **clean=true, 0 hits**. (Q3a/Q3b had 14/2 hits — now zero.)
- Conservative caps unchanged (normalizer enforces slot capacity; table headers self-designed; **no
  global font shrink**). P4/P6 visual overflow, if any, remains **template-side / Q3e** — not blocking.

## 7. Validation summary
| Check | Result |
|---|---|
| 8-page T5: edit cover title → shown on final slide 1 | ✅ PASS |
| 8-page T5: edit agenda item → agenda shows it (exact) | ✅ PASS |
| 8-page T5: agenda items == body section_titles | ✅ exact for shown (3/5; template has 3 slots) |
| 8-page T5: closing not in agenda; opens | ✅ |
| 8-page T5: contamination | ✅ clean (0) |
| 12-page T5 (no edit): opens; cover/agenda/body consistent | ✅ |
| 12-page T5: contamination | ✅ clean (0); 20 residue shapes cleaned |
| Single source of truth: confirmed + effective outline saved | ✅ with `_derivation` |
| Stability: failure → job error file + clear message; no silent fail | ✅ mechanism in place; JSON retry + type tolerance unit-tested |
| T6 route smoke | ✅ resolve + index, no error |

## 8. Known template-side items (deferred to Q3e visual polish — NOT this round)
- Agenda item-slot count (3) < section count (5–6) → only first N sections shown. Needs fewer
  sections or a richer agenda layout (template/outline-planning), not stability.
- Residual non-keyword template labels on some pages (e.g. `落地路径及相关保障`, `案例实践`) are not in
  the residue list and remain; add to the list later if confirmed unwanted.
- Any P4/P6 visual overflow is template-side.

## 9. Git / next
3 code files + this report; explicit-path commit only; **no push, no deploy, t5_new not reindexed
locally.** Recommend review, then push, then run the Q3c §8 cloud t5_new reindex on Alibaba Cloud.

— End Q3d report (no push / deploy; local validation only) —
