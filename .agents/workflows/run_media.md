---
description: ReviewLens Visual Media — /broll → /gen
---

# Visual Media: B-roll Mapping & AI Media Generation

> **This is the final stage of the pipeline.** The output `data/script_with_media.json` is a complete media package that will be handed off to an external Remotion rendering project.

This workflow maps B-roll assets to the finalized narration script and generates missing media using AI generation tools.

## Prerequisite Check

Verify the existence of the following files:

- `data/final_script_with_narration.json`
- `data/narration_audio/manifest.json`
- `data/word_timestamps.json`
- `data/category_analysis.json`

> [!WARNING]
> If any of the above are missing, output a **warning message** to the user: "Audio Production is not complete. Please run `/run_audio` first." and **STOP** the workflow execution immediately.

## Execution Procedure (Showrunner Action)

### 3-0. Media Indexing (Pre-flight)

> **Skip condition**: If `data/movies_meta/movie_metadata_extracted.json` or `data/photos_meta/photos_metadata_extracted.json` already exist, skip this step.

```bash
python tools/media_indexer.py \
    --input-dir products/ \
    --output-dir data/ \
    --themes data/category_analysis.json \
    --script data/final_script_with_narration.json
```

Output: `data/movies_meta/movie_metadata_extracted.json`, `data/photos_meta/photos_metadata_extracted.json`
— Tags each media asset with `related_themes[]` + `matching_block_ids[]`

### 3-1A. Media Candidate Pre-filtering

Generate per-block media candidate lists prioritized by `related_themes` and keyword relevance:

```bash
python tools/filter_media.py \
    --script       data/final_script_with_narration.json \
    --movies-meta  data/movies_meta/movie_metadata_extracted.json \
    --photos-meta  data/photos_meta/photos_metadata_extracted.json \
    --output       data/media_candidates.json
```

Output: `data/media_candidates.json` — theme-aware ranked candidates.

### 3-1B. Showrunner Contextual Selection

> [!IMPORTANT]
> **Action**: Read `data/media_candidates.json` and `data/final_script_with_narration.json`. For each block, perform a contextual judgment to select the best asset(s). **The only output of this step is `data/block_visual_mapping.json`.**

1. **Theme Alignment**: Prioritize candidates where `related_themes` match the block's `scene_id`.
2. **Sentiment Check**: Align narration sentiment with media sentiment (Positive/Negative).
3. **Visual Proof**: Read `visual_evidence` to ensure the content directly proves the script's claim.
4. **No Reuse**: Maintain a `used_assets` list to prevent duplicate media across blocks.

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
    "ai_generation_hint": null      // set if NO candidates are suitable
  }
}
```

> [!IMPORTANT]
> Blocks where NO candidate captures the required context must have `"media": []` and `"ai_generation_hint": "<prompt description>"`.

### 3-1C. Asset Injection

Inject the showrunner's selection into the script:

```bash
python tools/broll_mapper.py \
    --script       data/final_script_with_narration.json \
    --media-dir    data/ \
    --mapping      data/block_visual_mapping.json \
    --output       data/script_with_media.json
```

### 3-2. AI Media Generation (For Gaps)

> ⚠️ **Policy**: Every script block must be filled; do not leave empty B-roll slots.

For blocks identified as AI generation targets (missing `broll_asset` after 3-1C):

```bash
# Image Generation
python tools/gen_media.py \
    --type         image \
    --prompt-file  ./tmp/gen_prompt_block_XX.txt \
    --output       data/generated_media/images/block_XX.png \
    --aspect-ratio 16:9 \
    --model        gemini-3.1-flash-image-preview

# Video Generation
python tools/gen_media.py \
    --type         video \
    --prompt-file  ./tmp/gen_prompt_block_XX.txt \
    --output       data/generated_media/videos/block_XX.mp4 \
    --aspect-ratio 16:9 \
    --model        veo-3 \
    --timeout      300
```

## Completion Criteria

- `data/script_with_media.json` successfully saved.
- All blocks have a `broll_asset` path — no empty slots remain.
- **Pipeline complete.** Hand off the `data/` directory to the external Remotion rendering project.
