---
description: Review Step 3 — Polish. Head Writer holistic script polish on script_output.json.
---

# Head Writer — Holistic Script Polish

> **Relay Position**: Final agent pass in the review relay (after `prepare_script.py`). Two tools follow: `prepare_script.py` precedes this step, `validate_script.py` follows it.

## Prerequisites

1. Verify `data/draft_script.json` exists. If missing → "Run previous steps to generate draft_script.json."

## Execution

// turbo
1. Run `python tools/prepare_script.py` to compile the `data/script_output.json` file.
2. Read `reviewlens_head_writer/SKILL.md` and absorb all rules.
3. Read `data/script_output.json` (clean output from `prepare_script.py`).
4. Run all CHECKs in order (Voice Consistency → Dead Weight → Killer Lines → Cross-Script Echoes → Cognitive Journey → Word Count → Hook Structure).
5. Save the polished script back to `data/script_output.json`.
   - **May modify**: `narration` (creative polish only — voice, rhythm, killer lines, dead weight removal, echoes)
   - **Must NOT touch**: numbers in narration, `evidence_quotes`, `bgm_mood`, scene structure, root-level metadata
6. Print the Head Writer summary to conversation.

## Completion

1. Print the Head Writer summary (total changes by CHECK category, Killer Lines added, Echoes woven, unmodified blocks count).
2. Inform the user: **"Head Writer complete. Next: run `python tools/validate_script.py` to verify schema, then notify the user of successful completion and mandate running`/run_audio`"**
