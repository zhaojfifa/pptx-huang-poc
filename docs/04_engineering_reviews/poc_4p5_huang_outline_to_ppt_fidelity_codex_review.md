# P1.5 · Outline-to-PPT Fidelity Codex Review

Date: 2026-05-26  
Reviewer: Codex independent review  
Object: `docs/04_engineering_reviews/poc_4p5_huang_outline_to_ppt_fidelity_trace.md`  
Scope: review only. No code implementation, no commit, no push, no deploy, no reindex.

## 1. Overall verdict

**GO WITH CONDITIONS** for the trace's recommended direction.

The trace is materially credible: the current pipeline treats most outline fields as generation hints, then asks the LLM to produce final slide content and maps that content into template shapes. The only user-visible special-page deterministic fill currently present at HEAD is the P1 agenda-slot fill. Cover has no equivalent targeted fill, and the current generated decks show the cover-visible title/subtitle can remain template residue even when `confirmed_outline.json` is correct.

One correction: the trace says local template 28 maps the cover title slot to visible `标题 3`. Current evidence from `logs/job_121/blueprints.json`, `logs/job_123/blueprints.json`, and final deck inspection shows the blueprint title slot is `shape_id=2`, `name=文本框 1`, while final slide 1 only exposes visible text shapes `标题 3`, `副标题 5`, and slide number. The visible `标题 3` remains `央国企穿透式监管解决方案介绍` in job_121/job_123. This is not fatal to the trace; it strengthens the cover root-cause claim.

## 2. Trace accuracy review

**Mostly accurate.**

- `template_page_number` is hard in practice: outline generation is instructed to set it, `agent._select_template_page()` prefers it, and `template_cloner.clone_and_fill()` uses `_template_page_number` to select source slides.
- Body `section_title` / `_agenda_section` is a hard prompt-level topic constraint, not a deterministic rendered-text contract. The injection is explicit (`目录归属（必须遵守）`), but no post-render verifier proves every sentence stayed in-section.
- P1 agenda item slots are deterministic for the slot refs passed from `blueprints.json`: `fill_agenda_deterministic()` overwrites only those agenda content slots.
- There are other hard mechanics outside the outline semantic contract: first/second/last slide structural validation, page-count checks, and normalizer capacity/table row caps. These do not make cover/body titles or points hard contracts.
- `confirmed_outline.json` is faithful: `_cards_to_slides()` copies the edited cards, and `poc_generate()` saves it before `_agenda_consistency()` mutates the in-memory outline with `_agenda_section`.
- `effective_outline.json` is not produced at current HEAD; existing `logs/job_117/job_119` files are Q3d-era artifacts.

Verdict on the user's specific question: **yes, "outline is a hint" is accurate for cover title/subtitle, body title, body points, and table data.** For the hard constraints list, **yes with nuance**: the listed three are the relevant outline-to-render hard constraints, but body section binding is prompt-hard rather than programmatically enforced in final text.

## 3. Cover root cause review

**Root cause is valid. Cover-only deterministic fill is needed.**

Findings:

- Frontend sends cover data correctly. `generatePayload()` sends `outline: currentOutline`; the editor writes cover `title` and `points` into that same state.
- Backend saves cover data faithfully. `_cards_to_slides()` maps card `title` to slide `title` and card `points` to `key_points`; `confirmed_outline.json` is saved from that result.
- `content_generator.generate_slide_content()` includes the whole `slide_outline` in the prompt, but asks the LLM to return a new `"title"` and optional `"subtitle"`. It does not copy the confirmed outline title/subtitle through deterministically.
- `template_cloner._fill_with_blueprint()` writes title/subtitle only through the blueprint's detected slots. If those slots are absent, stale, hidden, or not the visible cover title/subtitle shapes, the visible template residue remains.
- Current job evidence confirms this failure mode: job_123 `confirmed_outline` cover title is `宝钢2025经营复盘`, but final slide 1 visible title remains `央国企穿透式监管解决方案介绍`; Q3d job_119, which had targeted `fix_cover_slide`, shows the visible cover title/subtitle correctly overwritten.

Conclusion: this is not a frontend or save-path bug. It is the combination of LLM regeneration plus unreliable cover slot mapping plus missing post-render cover fill.

## 4. Agenda root cause review

**Trace is accurate. P1 fixed the LLM agenda rewrite for the content slots it owns.**

- Before P1, agenda slide content could contain LLM-numbered/rephrased text such as `1 经营质效与财务表现`.
- At HEAD, `web/app.py` loads agenda `slot_mappings` / content slots from `blueprints.json` and passes them into `polish_deck()`.
- `fill_agenda_deterministic()` writes exact deduped body `section_title`s into those slot refs. Job_123 logs show `agenda_filled=3`, `agenda_overflow={sections:5, slots:3}`.
- Final job_123 slide 2 content slots contain exact section titles without LLM numbering: `经营质效与财务表现`, `产能效率与智能制造`, `成本控制与精益运营`.

Remaining agenda mismatch is mainly template-side:

- T5 agenda exposes only 3 agenda content slots while the deck has 5 sections.
- Extra agenda shapes such as `国资委穿透式监管解读`, `中国移动穿透式监管解决方案`, `落地路径及相关保障`, and `案例实践` are outside P1 agenda slot refs and intentionally remain untouched.
- P1 does not materially risk body content because it writes only agenda slide slot refs. Existing deck-wide `strip_unsafe_numbering()` and `clear_placeholder_residue()` remain pre-existing behavior, not new P1 risk.

Minor correction: the trace's "visual order follows template geometry, not section order" should be read cautiously. In job_123, the agenda content slots are visually top-to-bottom in section order; the broader risk is that geometry controls the fill order if a future template orders slots unexpectedly.

## 5. Q3d regression risk review

**Regression analysis is directionally sound.**

Q3d bundled several changes: targeted cover fill, deterministic agenda fill, global `clear_known_residue`, `effective_outline.json`, error handling, and `chat_structured` JSON-fence handling. The strongest code-level regression mechanism is the global residue cleaner: it blanked any shape or table cell containing residue tokens across the whole deck. Existing Q3d job_119 logs show 20 cleared items, including body text and P8 table cells.

The evidence does not prove that global cleaning was the only possible contributor, because Q3d also changed LLM JSON parsing and web generation behavior. But the targeted agenda fill was reintroduced in P1 with P0 passing, and Q3d's cover fill only touched slide 1 title/subtitle shapes. So the practical risk ruling is:

- **Ban deck-wide residue blanking.**
- **Do not change `chat_structured`, `content_generator`, `content_normalizer`, or `template_cloner` for the cover fix.**
- **Do not enforce body title/points verbatim.**
- **Keep residue handling, if any, targeted to explicit special-page shapes or table header cells in a separate change.**

## 6. Recommended next step

Recommended sequence: **Option 1 minimal read-only gate first, then Option 2 cover-only deterministic fill immediately after.**

Reason: Option 1 makes the current gap measurable and gives Option 2 an objective pass/fail target. It should stay small; do not turn it into a broad visual-quality framework before fixing the user-visible cover issue.

If time pressure is high, going directly to Option 2 is acceptable **only if** the PR includes equivalent read-only before/after checks for `cover_title_match`, `agenda_items_match`, and P0 body metrics. The current root cause is already proven well enough to avoid waiting on a large gate implementation.

Option rulings:

| Option | Verdict | Conditions |
|---|---|---|
| Option 1: read-only fidelity gate | **GO** | Keep read-only; no generation behavior, no cleanup, no LLM/DB imports. |
| Option 2: cover-only deterministic fill | **GO WITH CONDITIONS** | Only slide 1 title/subtitle shapes; pass confirmed cover title + first cover key point; do not use blueprint title slot as the only locator. |
| Option 3: outline contract enforcement | **GO WITH CONDITIONS** | Cover/agenda only. Do not enforce body title/points verbatim. Do not revive broad Q3d behavior. |

## 7. Allowed files

For Option 1:

- `scripts/poc_content_baseline_smoke.py`, if extending the existing smoke narrowly.
- Or a new read-only script such as `scripts/poc_outline_fidelity_gate.py`.
- Review/validation docs under `docs/04_engineering_reviews/`.

For Option 2:

- `core/deck_polish.py`: add a cover-slide-only deterministic fill.
- `web/app.py`: minimal wiring to pass confirmed cover title/subtitle into `polish_deck()`.
- Optional read-only validation script under `scripts/`.
- Review/validation docs under `docs/04_engineering_reviews/`.

Implementation condition for Option 2: the cover fill should operate on final slide 1 shapes by visible/name heuristic (`标题`/`title`, `副标题`/`subtitle`, then conservative topmost fallback). It should not rely solely on `blueprints[0].slots.title`, because current evidence shows that blueprint is part of the cover mismatch.

## 8. Forbidden files / behaviors

Forbidden files for the next cover fix:

- `core/content_generator.py`
- `core/content_normalizer.py`
- `core/template_cloner.py`
- `core/typography_polish.py`
- `skills/skill_llm/llm_skill.py`
- `template_analyzer/*`
- DB migrations / schema / template records
- template PPTX assets
- frontend files, unless a new frontend payload bug is proven

Forbidden behaviors:

- No deck-wide residue cleaning or token-based blanking.
- No `clear_known_residue`-style pass.
- No body title/points deterministic overwrite.
- No table fill, row cap, truncation, or font changes.
- No generation prompt changes.
- No reindex, deploy, push, or unrelated refactor.
- Do not commit `logs/` or `output/` artifacts.

## 9. Required validation gates

Minimum gates before accepting Option 2:

1. **Diff scope gate**: changed files are restricted to the allowed list.
2. **Cover title match**: final visible slide-1 title shape equals `confirmed_outline.json` slide 1 `title`.
3. **Cover subtitle match**: if a visible subtitle shape exists, it equals confirmed slide 1 first `key_points` item, or the expected empty value is explicitly logged.
4. **Agenda items match**: agenda filled content slots equal the first N deduped body `section_title`s; closing is excluded.
5. **P0 body smoke**: P4 text chars and P8/P9 table-cell counts do not fall below the accepted baseline thresholds.
6. **No global cleanup evidence**: polish log has no `residue_cleared` / equivalent deck-wide cleaner output.
7. **Artifact check**: final deck opens and slide count matches expected 12-page T5 profile.

Note: the current `scripts/poc_content_baseline_smoke.py` uses Python 3.10+ type syntax. Run it with a Python 3.10+ environment that has `python-pptx`; do not use macOS system Python 3.9 for that script.

## 10. Final GO / NO-GO

**Final ruling: GO WITH CONDITIONS.**

Proceed with a small read-only gate first if it can be done quickly, then implement cover-only deterministic fill. Direct Option 2 is also acceptable if the same read-only checks are run and recorded in the PR/report.

Do **not** implement body outline enforcement, table cleanup, prompt changes, normalizer/cloner changes, global residue blanking, reindex, deploy, push, or template changes as part of this next step.

