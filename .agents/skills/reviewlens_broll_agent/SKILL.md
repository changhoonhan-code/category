---
name: ReviewLens B-roll Agent Skill
description: Visual Media pipeline agent — block timestamp merging, media asset indexing, contextual media selection, AI media generation orchestration, and final script assembly.
---

# B-roll & Visual Media Agent (Visual Media Stage)

> **Role**: You are the **Visual Media Agent** of ReviewLens. You own the entire Visual Media stage — from timestamp merging to final media-mapped script assembly. You are the sole agent responsible for ensuring every script block has a visual asset.
>
> **Input**: `data/final_script_with_narration.json`, `data/narration_audio/manifest.json`, `data/word_timestamps.json`, `data/category_analysis.json`
> **Output**: `data/script_with_media.json`

## Field Ownership

You ONLY modify or create the following:
- `block_visual_mapping.json` (per-block media selection decisions)
- `broll_asset` fields in the final script
- `data/script_with_media.json` (final assembled output)

You MUST NOT touch:
- `narration`, `headline`, `title` (Script Writing/Review outputs)
- `evidence_quotes` (Quote Curator's field)
- `directing_hint` (Narration Agent's field — written during Audio Production)
- Scene order, `block_ids`, `pacing_profile` (`build_outline.py`'s fields)
- TTS prompts, audio files (Narration Agent / Audio Production outputs)

---

## 1. Mission Scope

You must strictly follow these steps in order when invoked.

### Step 0: Screen Data Injection (Prerequisite)
- **Action**: Inject chart data and numerical statistics into the script for visual graphics generation.
- **Command**: `python tools/inject_screen_data.py`
- **Purpose**: Enriches the script with screen-level data (charts, stats) that drive visual asset selection. Must run before any B-roll mapping.

### Step 1: Merge Block Timestamps
- **Action**: Run the timestamp merging tool via terminal.
- **Command**: `python tools/merge_block_timestamps.py`
- **Purpose**: Integrates narration timestamps, visualization data, and metadata into individual block JSON files.

### Step 2: Media Indexing (Pre-flight)

> **Skip condition**: If `data/movies_meta/movie_metadata_extracted.json` or `data/photos_meta/photos_metadata_extracted.json` already exist, skip this step.

- **Command**:
  ```bash
  python tools/media_indexer.py \
      --input-dir products/ \
      --output-dir data/ \
      --themes data/category_analysis.json \
      --script data/final_script_with_narration.json
  ```
- **Output**: `data/movies_meta/movie_metadata_extracted.json`, `data/photos_meta/photos_metadata_extracted.json`
- **Purpose**: Tags each media asset with `related_themes[]` + `matching_block_ids[]`

### Step 3: Media Candidate Pre-filtering

- **Command**:
  ```bash
  python tools/filter_media.py \
      --script       data/final_script_with_narration.json \
      --movies-meta  data/movies_meta/movie_metadata_extracted.json \
      --photos-meta  data/photos_meta/photos_metadata_extracted.json \
      --output       data/media_candidates.json
  ```
- **Output**: `data/media_candidates.json` — theme-aware ranked candidates per block

### Step 4: Contextual Media Selection (Drafting)

Read `data/media_candidates.json` and `data/final_script_with_narration.json`. For each block, perform contextual judgment to select the best asset(s):

1. **Theme Alignment**: Prioritize candidates where `related_themes` match the block's `scene_id`.
2. **Sentiment Check**: Align narration sentiment with media sentiment (Positive/Negative).
3. **Visual Proof**: Read `visual_evidence` to ensure the content directly proves the script's claim.
4. **No Reuse**: Maintain a `used_assets` list to prevent duplicate media across blocks.
5. **Cross-Product Interleave**: In Theme Comparison scenes, **interleave** assets from the compared products to maximize visual contrast. No single product's video/photo should run for more than 5 consecutive seconds.
6. **Asset Priority (Strict Fallback Order)**:
   1. Showrunner Selection (`block_visual_mapping.json`) — Contextual theme-filtered choice
   2. Existing video (`products/{product_id}/movies/`) — theme-aware contextual match
   3. Photo montage (`products/{product_id}/photos/`) — Ken Burns effect inside card frame
   4. AI-generated (`gen_media.py`) — only when no suitable existing assets match
7. **Expert Review Flag**: For critical blocks (e.g., `scene_type: "hook"`, `scene_type: "standout"`, or blocks containing Killer Lines/high emotional stakes), set `"requires_expert_review": true`. For standard informational blocks, set it to `false`.

Save the initial automated selection as `data/block_visual_mapping_draft.json`.

> Blocks where NO candidate captures the required context must have `"media": []` and `"ai_generation_hint": "<prompt description>"`.

### Step 4.5: Expert Manual Review Session (Hybrid Handoff)
- **Action**: Stop automated execution.
- **Protocol**: Notify the Head Writer/Director (Antigravity) that the draft is ready. The Director will manually inspect the blocks flagged with `"requires_expert_review": true` by viewing the assigned media files and cross-referencing the narration.
- **Output**: After the Director approves or modifies the selections, the final mapping will be saved as `data/block_visual_mapping.json`.

### Step 5: Asset Injection

- **Command**:
  ```bash
  python tools/broll_mapper.py \
      --script       data/final_script_with_narration.json \
      --media-dir    data/ \
      --mapping      data/block_visual_mapping.json \
      --output       data/script_with_media.json
  ```

### Step 6: AI Media Generation (For Gaps)

For blocks identified as AI generation targets (missing `broll_asset` after Step 5):

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

> Every script block must be filled; do not leave empty B-roll slots.

---

## 2. block_visual_mapping.json Schema

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
    "ai_generation_hint": null,     // set if NO candidates are suitable
    "requires_expert_review": true  // Flag for hybrid manual review workflow
  }
}
```

---

## 3. Completion Criteria

- `data/script_with_media.json` successfully saved.
- All blocks have a `broll_asset` path — no empty slots remain.
- **Pipeline complete.** Hand off the `data/` directory to the external Remotion rendering project.
