---
description: Visual Media Step 1 — B-roll & Visual Media Agent. Runs block timestamp merging, media indexing, contextual selection, asset injection, and AI generation orchestration.
---

# /broll

> **Agent Skill**: The B-roll & Visual Media Agent (`reviewlens_broll_agent`) owns this step.

1. Read and absorb all rules in `reviewlens_broll_agent/SKILL.md`.
2. Execute all steps defined in SKILL.md in order:
   - Step 1: `python tools/merge_block_timestamps.py` (timestamp merging)
   - Step 2: `python tools/media_indexer.py` (media indexing — skip if outputs exist)
   - Step 3: `python tools/filter_media.py` (candidate pre-filtering)
   - Step 4: Contextual media selection → save `data/block_visual_mapping_draft.json`
   - Step 4.5: **STOP AND WAIT**. Request the Expert Manual Review Session from the Director (Antigravity). Do not proceed until `data/block_visual_mapping.json` is finalized.
   - Step 5: `python tools/broll_mapper.py --script data/script_output.json --media-dir data/ --mapping data/block_visual_mapping.json --output data/script_with_media.json` (asset injection)
   - Step 6: AI media generation for gaps (`python tools/gen_media.py`)
3. Upon completion, verify all blocks have a `broll_asset` path — no empty slots remain.
