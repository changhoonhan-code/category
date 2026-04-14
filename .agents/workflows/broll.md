---
description: Visual Media Step 1 — B-roll. B-roll asset search and mapping.
---

# /broll

> **Agent Skill**: The B-roll Agent (`reviewlens_broll_agent`) owns this step.

1. Read and absorb all rules in `reviewlens_broll_agent/SKILL.md`.
2. Based on the script structure, timestamp data, and existing visual resources, map appropriate media to each block.
3. Save the preliminary results to `data/block_visual_mapping.json`.
4. Identify any empty slots requiring missing media and instruct the user to proceed to the next step, `/gen` (AI Media Generation).

