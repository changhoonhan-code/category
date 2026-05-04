---
description: ReviewLens Visual Media — /broll → /gen
---

# Visual Media: B-roll Mapping & AI Media Generation

> **This is the final stage of the pipeline.** The output `data/script_with_media.json` is a complete media package that will be handed off to an external Remotion rendering project.
>
> **Agent**: The B-roll & Visual Media Agent (`reviewlens_broll_agent`) owns this entire stage. All steps below are executed by the agent following its SKILL.md.

This workflow maps B-roll assets to the finalized narration script and generates missing media using AI generation tools.

## Prerequisite Check

Verify the existence of the following files:

- `data/final_script_with_narration.json`
- `data/narration_audio/manifest.json`
- `data/word_timestamps.json`
- `data/category_analysis.json`

> [!WARNING]
> If any of the above are missing, output a **warning message** to the user: "Audio Production is not complete. Please run `/run_audio` first." and **STOP** the workflow execution immediately.

## Execution Procedure

### Step 0: Screen Data Injection

Inject chart data and numerical statistics into the script for visual graphics generation. This must run before any B-roll mapping.

```bash
python tools/inject_screen_data.py
```

### Step 1: B-roll Pipeline (`/broll`)

Run the B-roll & Visual Media Agent. The agent executes all 6 steps defined in `reviewlens_broll_agent/SKILL.md`:

1. **Timestamp Merging**: `python tools/merge_block_timestamps.py`
2. **Media Indexing** (skip if outputs exist): `python tools/media_indexer.py`
3. **Candidate Pre-filtering**: `python tools/filter_media.py`
4. **Contextual Media Selection**: Agent reads candidates + script, performs contextual judgment, saves `data/block_visual_mapping.json`
5. **Asset Injection**: `python tools/broll_mapper.py`
6. **AI Media Generation** (for gaps): `python tools/gen_media.py`

**block_visual_mapping.json schema** (per block):

```jsonc
{
  "<block_id>": {
    "media": [
      {
        "type": "video" | "photo",
        "filename": "<filename>",
        "path": "movies/<filename>" | "photos/<filename>",
        "category": "evidence" | "thematic" | "context",
        "reason": "Brief contextual justification",
        "start_time_sec": 0,        // video only
        "end_time_sec": 5           // video only
      }
    ],
    "composition_notes": "Intent for transitions or multi-image flow",
    "ai_generation_hint": null,      // set if NO candidates are suitable
    "requires_expert_review": true   // Flag for hybrid manual review workflow
  }
}
```

> [!IMPORTANT]
> Blocks where NO candidate captures the required context must have `"media": []` and `"ai_generation_hint": "<prompt description>"`.

### Step 2: Gap Fill Verification (`/gen`)

After the agent completes Step 6, verify:
- All blocks have a `broll_asset` path — no empty slots remain.
- If gaps persist, re-run `gen_media.py` with revised prompts.

## Completion Criteria

- `data/script_with_media.json` successfully saved.
- All blocks have a `broll_asset` path — no empty slots remain.
- **Pipeline complete.** Hand off the `data/` directory to the external Remotion rendering project.
