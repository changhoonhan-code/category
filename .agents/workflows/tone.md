---
description: Review Step 2 — Tone. BGM assignment + tone/humor/balance editing.
---

# Tone & Balance Editor — BGM Assignment + Tone / Humor / Balance

> **Relay Position**: Step 2 of 4 in the review relay. Runs after Data Validator.
>
> **Output rules**: The `critique_log` array must be appended to the root of `data/draft_script.json`. It is printed to conversation only at completion, and MUST NEVER be embedded in the final `script_output.json`.

## Prerequisites

1. Verify `data/draft_script.json` exists. If missing → instruct the user to run `/run_write` first.
2. Verify `data/category_tone_editor.json` exists. If missing → run `python tools/filter_category.py --profile tone_editor` (requires `data/category_analysis.json` from Data framework).
3. **Completion check**: Read `data/draft_script.json` and verify a root-level `critique_log` array exists (key must be present). If the key does not exist at all → warn: "Data Validator has not run. Run `/check` first."
   - An empty `critique_log: []` is valid — it means Data Validator found zero errors.

## Critique Log Schema

Each fix appends an entry to the `critique_log` array at the root level of `data/draft_script.json`:

```jsonc
{
  "editor": "Tone Editor",             // Always "Tone Editor" for this step
  "block_id": "hook_cold_open",        // target block_id, or "All blocks" for global fixes
  "fix_type": "BGM Assign",            // free-text category (see SKILL.md log taxonomy)
  "original": "...",                   // before text/value
  "corrected": "...",                  // after text/value
  "reason": "..."                      // why the change was made
}
```

## Execution

1. Read `reviewlens_tone_editor/SKILL.md` and absorb all rules.
2. Read `data/category_tone_editor.json` for pattern/humor/maturity context (filtered for Tone Editor fields).
3. Take over the script from Data Validator and run in this order:
   - **Run CHECK 0 first (BGM Assignment)**: The incoming script has no `bgm_mood` fields — the Writer intentionally omitted them. Assign `bgm_mood` to every block before any other work. This is a primary first-time assignment, not a revision.
   - Then run CHECK 1–9 (flow, tension, banned words, humor, balance, scene balance, trending tone [v2 inactive], drama patterns, story density).
4. Append fixes to the `critique_log` array. Save the updated script back to `data/draft_script.json`.
   - **May modify**: `bgm_mood` (primary assignment — no prior value exists), narration (tone/phrasing only — not numbers), `is_humorous`
   - **Must NOT touch**: `evidence_quotes` content (highlight_phrase, star_rating, review_id, review_date, has_media, product_id) — exception: `is_humorous` may be modified at quote level. Scene order (if reordering is needed, log justification). Root-level `category_name`, `products` array.

## Completion

1. Print a summary of Tone Editor fixes to conversation (count by fix_type).
2. Inform the user: **"Tone Editor complete. Next: run `python tools/prepare_script.py` then `/polish`"**

