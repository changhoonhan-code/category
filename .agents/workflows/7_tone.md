---
description: Script Auditor (mechanical checks) + Creative Director (structural audit, flag logging, humor tagging, annotations). CD does NOT rewrite narration.
---

# Tone & Balance — Script Auditor + Creative Director

> **Relay Position**: Step 1 of 2 in the review relay. Runs after Quote Curator (`/curate`).
>
> **5-Phase Structure**:
> - Phase 1: Data filtering (Python tool)
> - Phase 2: Mechanical audit (Python tool — `script_auditor.py`)
> - Phase 3: Creative review (LLM — Creative Director)
> - Phase 4: Safe merge (Python tool — `merge_creative.py`)
> - Phase 5: Completion summary
>
> **Output rules**: The `critique_log` array must be appended to the root of `data/draft_script.json`. It is printed to conversation only at completion, and MUST NEVER be embedded in the final `script_output.json`.

## Prerequisites

1. Verify `data/draft_script.json` exists. If missing → instruct the user to run `/run_write` first.
2. Verify `data/category_validator.json` exists. If missing → run `python tools/filter_category.py --profile validator` (requires `data/category_analysis.json`).

## Critique Log Schema

Each flag appends an entry to the `critique_log` array at the root level of `data/draft_script.json`.
`corrected` is always `null` — CD flags issues, it does not rewrite narration.

```jsonc
{
  "editor": "Creative Director",        // Always "Creative Director" for this step
  "block_id": "hook_cold_open",        // target block_id, or "All blocks" for global flags
  "fix_type": "Flow Fix",             // Flow Fix | Humor Injection | Drama Resolution | Flag Resolution | Collision Fix
  "original": "brief description of the structural problem",
  "corrected": null,                   // CD does not rewrite — always null
  "reason": "..."                      // what the Writer Agent must fix
}
```

---

## Phase 1: Data Filtering

// turbo
1. Run `python tools/filter_script.py --profile creative`
2. Verify `data/category_validator.json` exists. If missing, run `python tools/filter_category.py --profile validator`.

---

## Phase 2: Mechanical Audit (Script Auditor)

// turbo
3. Run `python tools/script_auditor.py`
4. Print summary of auditor output (`tmp/auditor_report.json`):
   - Total flags by severity (error / warning / info)
   - Humor count vs minimum
   - Checks executed and skipped

---

## Phase 3: Creative Review (Creative Director)

5. **Read SKILL**: Read `reviewlens_creative_director/SKILL.md` and absorb all rules.
6. **Read authority rules**: Read `.agents/rules/narrative_standards.md` — the definitive voice and constraint rulebook.
7. **Load inputs**:
   - `tmp/script_creative.json` (Lightweight script view)
   - `data/category_validator.json` (Humor quote reference + theme/product data)
   - `tmp/auditor_report.json` (Auditor flags)
8. **Execute Creative Checks** following SKILL.md execution order:
   - Step 1: Process error-severity auditor flags (CHECK 3 banned words) → log, do NOT rewrite
   - Step 2: Collision Rule enforcement (Setup → Collision → Residue) → log missing structure
   - Step 3: Cross-Block Flow scan → log transition problems, do NOT rewrite
   - Step 4: Humor tagging (minimum quota from `pipeline_contracts.json`)
   - Step 5: Warning-severity flag resolution (CHECK 6, CHECK 8, CHECK 9) → log only
   - Step 6: Generate `block_annotations` (collision map + humor markers + flow notes)
9. **Save** output to `tmp/script_creative_edited.json` (patch format).
   - **Must contain**: `critique_log_additions`, `block_annotations`
   - **May contain**: `quote_patches` (for `is_humorous` flag changes)
   - **Must NOT contain**: `block_patches`, narration text, full script, `directing_hint`, `pacing_profile`, `title`, `headline`

> **Output Token Budget Rule**: Save the file BEFORE printing analysis summary to conversation. If a token limit error occurs, the output file must already exist.

---

## Phase 4: Safe Merge

// turbo
10. Run `python tools/merge_creative.py`
11. Print merge summary:
    - Quote flag changes count
    - Block annotations saved
    - Integrity errors

---

## Phase 5: Finalization & Feedback

// turbo
1. Run `python tools/prepare_script.py` to finalize the script into `data/script_output.json` (stripping temporary logs for downstream production).

2. **Print Auditor Summary** — Total flags by severity (error / warning / info), humor count vs minimum.

3. **Print Creative Director Feedback** — For each entry in `critique_log_additions`, print a structured block:

   ```
   ── [fix_type] block_id ──────────────────────
   Problem:  {original}
   Action:   {reason}
   ```

   Group entries by `fix_type`. If `critique_log_additions` is empty, print: **"No structural issues found."**

4. **Print Decision Prompt** to the user:
   - If flags exist: **"Tone step complete. {N} issue(s) flagged. Review the items above — re-run `/4_write` to regenerate narration, or edit `data/raw_draft.md` directly and re-run `/5_decompose`."**
   - If no flags: **"Tone step complete. Script finalized to `script_output.json`. Proceed to production steps (`/run_media` or `/run_audio`)."**
