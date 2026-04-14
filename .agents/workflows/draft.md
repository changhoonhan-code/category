---
description: Script Writing Step 3 — Writer. Draft script creation (3-Pass & Veto Loop)
---

# /draft

> **Agent Skill**: The Writer Agent (`reviewlens_writer_agent`) owns this step.

// turbo
1. Run `python tools/filter_category.py --profile writer` to generate the filtered `data/category_writer.json`.
2. Read and absorb the rules in `reviewlens_writer_agent/SKILL.md`.
3. Read `data/comparison_outline.json` (structural blueprint) and `data/category_writer.json` (filtered data reference).
4. Execute the 3-Pass Generation (Skeleton -> Muscle -> Skin) and save the output as `data/draft_script.json`.
5. **[VETO LOOP]** If evidence is critically insufficient or the structure is logically disjointed, declare a Veto directly within the JSON and immediately halt writing.
   - If `veto_scope: "block_count"`, prompt the user to restart `/structure`.
   - If `veto_scope: "theme_selection"`, prompt the user to restart `/blueprint`.
6. Upon successful completion, instruct the user to initiate the Review Relay in a new session starting with `/run_review` or `/check`.
