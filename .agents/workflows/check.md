---
description: Review Step 1 — Check. Data Validator agent for numbers & quotes verification.
---

# Data Validator — Number & Quote Verification

> **Relay Position**: Step 1 of 4 in the review relay. This is the first agent to touch the draft script.
>
> **Output rules**: The `critique_log` array must be appended to the root of `data/draft_script.json`. It is printed to conversation only at completion, and MUST NEVER be embedded in the final `script_output.json`.

## Prerequisites

1. Verify `data/draft_script.json` exists. If missing → instruct the user to run `/run_write` first.
2. Verify `data/category_analysis.json` exists. If missing → instruct the user to run `/run_data` first.
3. If `data/draft_script.json` does not have a root-level `critique_log` array, **initialize one**: add `"critique_log": []` to the root of the JSON object.

## Critique Log Schema

Each fix appends an entry to the `critique_log` array at the root level of `data/draft_script.json`:

```jsonc
{
  "editor": "Data Validator",          // Always "Data Validator" for this step
  "block_id": "hook_cold_open",        // target block_id, or "All blocks" for global fixes
  "fix_type": "Numerical Correction",  // free-text category (see SKILL.md log taxonomy)
  "original": "...",                   // before text/value
  "corrected": "...",                  // after text/value
  "reason": "..."                      // why the change was made
}
```

## Execution

1. Read `reviewlens_data_validator/SKILL.md` and absorb all rules.
2. Generate the token-optimized data file by running: `python tools/filter_category.py --profile validator`
3. Read `data/category_validator.json` — this is the source of truth for all quantitative claims and evidence quotes.
4. Cross-reference every number in `data/draft_script.json` narration against the `category_validator.json` file.
5. Fix errors and append `critique_log` entries to the document's root array. Save the updated script back to `data/draft_script.json`.
   - **May modify**: numbers within narration, evidence_quotes metadata (star_rating, review_date, review_id, highlight_phrase)
   - **Must NOT touch**: tone, bgm_mood, scene order

## Completion

1. Print a summary of Data Validator fixes to conversation (count by fix_type).
2. Inform the user: **"Data Validator complete. Next: `/tone`"**

