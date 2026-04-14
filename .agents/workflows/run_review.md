---
description: Script Review session — 3-agent + 2-tool review relay orchestrator (Data Validator + Tone Editor + prepare_script.py + Head Writer + validate_script.py). Must run in a separate session from Script Writing.
---

# Script Review Session (Orchestrator)

> **Core Principle**: This command MUST run in a **separate conversation** from `/run_write`. Reviewing the draft without the writer's context prevents confirmation bias.
>
> Three specialist agents run sequentially, each modifying only its owned fields. Two Python tools handle mechanical transformation and schema validation.
>
> **Output rules**: The `critique_log` array must be appended to the root of `data/draft_script.json` during steps 1-2. `prepare_script.py` prints the summary and strips it when creating `script_output.json`. The final `script_output.json` MUST NEVER contain `critique_log`.

## Individual Commands

Each step can also be run independently for debugging, re-running a specific agent, or SKILL tuning:

| Step | Command | Agent / Tool |
| ---- | ------- | ------------ |
| 1 | `/check` | Data Validator |
| 2 | `/tone` | Tone & Balance Editor |
| 3 | `/polish` | Head Writer |
| 4 | `python tools/validate_script.py` | Tool: Schema validation gate |

## Prerequisites

1. Verify both `data/draft_script.json` and `data/category_analysis.json` exist. If missing, instruct the user to run `/run_write` and `/run_data` first.
2. **Veto Intercept**: Read the root keys of `data/draft_script.json`. If it contains a `"structural_rejection"` key, the Writer triggered a Veto. Do NOT proceed to the Data Validator. Instead, alert the user that the `/run_write` Veto Loop must be resolved first and immediately halt execution.

## Critique Log Schema

Each editor appends entries to the `critique_log` array located at the root level of the working `data/draft_script.json` file using this structure:

```jsonc
{
  "editor": "Data Validator",          // Data Validator | Tone Editor
  "block_id": "hook_cold_open",        // target block_id, or "All blocks" for global fixes
  "fix_type": "Numerical Correction",  // free-text category (see each SKILL's log taxonomy)
  "original": "...",                    // before text/value
  "corrected": "...",                   // after text/value
  "reason": "..."                      // why the change was made
}
```

> This array lives **inside data/draft_script.json** throughout steps 1-2. Each editor reads the file, appends their logs, and overwrites the file. `prepare_script.py` extracts and prints the summary, then strips it before saving `script_output.json`.

---

## Data Validator — Number & Quote Verification (`/check`)

1. Read `reviewlens_data_validator/SKILL.md` and absorb all rules.
2. Generate the token-optimized data file by running: `python tools/filter_category.py --profile validator`
3. Read `data/category_validator.json` — (source of truth for all product data and theme statistics).
4. Cross-reference every number in `data/draft_script.json` narration against `category_validator.json` 1:1.
5. Fix errors and append `critique_log` entries to the document's root array. Save the updated script back to `data/draft_script.json`.
   - **May modify**: numbers within narration, evidence_quotes metadata (star_rating, review_date, review_id, highlight_phrase)
   - **Must NOT touch**: tone, bgm_mood, scene order

## Tone & Balance Editor — BGM Assignment + Tone / Humor / Balance (`/tone`)

1. Read `reviewlens_tone_editor/SKILL.md` and absorb all rules.
2. Generate the token-optimized data file by running: `python tools/filter_category.py --profile tone_editor`
3. Read `data/category_tone_editor.json` for tone/humor/pattern context (filtered for Tone Editor fields).
3. Take over the script from Data Validator and run in this order:
   - **Run CHECK 0 first (BGM Assignment)**: The incoming script has no `bgm_mood` fields — the Writer intentionally omitted them. Assign `bgm_mood` to every block before any other work. This is a primary first-time assignment, not a revision.
   - Then run CHECK 1–9 (flow, tension, banned words, humor, balance, trending tone, drama, story density).
4. Append fixes to the `critique_log` array. Save the updated script back to `data/draft_script.json`.
   - **May modify**: `bgm_mood` (primary assignment — no prior value exists), `directing_hint` (primary assignment), narration (tone/phrasing only — not numbers), `is_humorous`
   - **Must NOT touch**: `evidence_quotes` content (highlight_phrase, star_rating, review_id, review_date, has_media) — exception: `is_humorous` may be modified at quote level. Scene order (if reordering is needed, log justification)

## Script Preparation (Tool)

Run the preparation script to transform `draft_script.json` into a clean `script_output.json`:

```bash
python tools/prepare_script.py
```

This tool:

- Extracts and prints the `critique_log` summary (grouped by editor with fix counts)
- Strips `critique_log` and all temporary fields
- Saves the clean script to `data/script_output.json`

## Head Writer — Holistic Script Polish (`/polish`)

1. Read `reviewlens_head_writer/SKILL.md` and absorb all rules.
2. Read `data/script_output.json` (clean output from `prepare_script.py`).
3. Run all CHECKs in order (Voice Consistency → Dead Weight → Killer Lines → Cross-Script Echoes → Cognitive Journey → Word Count → Hook Structure).
4. Save the polished script back to `data/script_output.json`.
   - **May modify**: `narration` (creative polish only — voice, rhythm, killer lines, dead weight removal, echoes)
   - **Must NOT touch**: numbers in narration, `evidence_quotes`, `bgm_mood`, scene structure, root-level metadata
5. Print the Head Writer summary to conversation.

## Schema Validation (Tool)

Run the validation script as the final gate before Audio Production:

```bash
python tools/validate_script.py
```

This tool performs deterministic schema validation:

- Root field completeness
- Block field completeness (block_id, narration, bgm_mood, pacing_profile, evidence_quotes)
- EvidenceQuote field completeness + product_id referential integrity
- Block ID uniqueness
- bgm_mood / pacing_profile value validation

**If PASS**: Proceed to `/run_audio`.
**If FAIL**: Review the error output, fix the issues in `data/script_output.json`, and re-run validation.

## Completion

1. Print the Head Writer summary.
2. Report `validate_script.py` result (PASS/FAIL).
3. If PASS, inform the user the next step is `/run_audio`.
