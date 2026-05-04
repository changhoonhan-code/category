---
description: Evidence quote selection and visual copy.
---

# Evidence quote selection and visual copy.

Mandatory Supplementary Step. The Orchestrator generates a curation brief, then an automated pipeline selects evidence quotes and extracts on-screen highlights. Must be run before /tone.

## Purpose

The Quote Curator exists to build **a rich pool of on-screen evidence quotes** for the video editor. These quotes appear as visual proof on screen while the narrator speaks — they are NOT consumed by the narration itself (the Writer already used the upstream data to craft the monologue).

The more high-quality candidates the Curator supplies per block, the more flexibility the editor has during post-production to select the most impactful quote for each moment's pacing, timing, and visual flow. A block with only 1 quote forces the editor's hand; a block with 5–7 candidates lets the editor match evidence to the exact editorial beat.

## Prerequisites

- `data/draft_script.json` must exist (Writer's output, decomposed into scenes/blocks).
- `data/category_analysis.json` must exist (source for product mapping).

## Phase 1 — Curation Brief (Orchestrator)

> The Orchestrator produces a lightweight brief. This is the ONLY step requiring agent judgment.

// turbo
1. Run `python tools/product_map.py` — outputs the product ID ↔ name mapping to stdout. Read the output to learn the mapping.
2. Read `data/draft_script.json`.
3. For each **scene** with `assigned_themes`:
   - Write a `headline`: a concise editorial heading for this scene (2-5 words).
4. For each **block** within those scenes:
   - Identify `focal_products`: which product(s) this block's narration is primarily ABOUT (not merely mentioned). Use the product IDs from step 1.
   - Identify `theme`: the canonical theme from the parent scene's `assigned_themes`.
   - Write a `title`: a concise 2-5 word editorial title for this block. Titles must be unique across the entire script — no two blocks share the same title.
4. For scenes WITHOUT `assigned_themes` (hook, intro, verdict), include them with empty blocks or skip them.
5. Save the result as `data/curation_brief.json` in this exact schema:

```json
{
  "scenes": [
    {
      "scene_id": "scene_04_active",
      "headline": "Active Noise Cancellation",
      "blocks": [
        {
          "block_id": "active_showdown",
          "title": "The 45-Point Gap",
          "focal_products": ["product_a", "product_b", "product_c"],
          "theme": "Active Noise Cancellation"
        },
        {
          "block_id": "active_fallout",
          "title": "The Gym Test",
          "focal_products": ["product_a"],
          "theme": "Active Noise Cancellation"
        }
      ]
    }
  ]
}
```

> [!IMPORTANT]
> Only include blocks that should receive evidence quotes. Hook, intro_credibility, and verdict blocks that don't need on-screen review quotes should be omitted from the brief.

---

## Phase 2 — Quote Search & Selection (Automated)

> Fully automated. No agent judgment needed.

// turbo
1. Run the curation pipeline:
   ```
   python tools/curate_quotes.py
   ```
   This script:
   - Reads `data/curation_brief.json` (from Phase 1)
   - Reads `data/draft_script.json` (for narration text)
   - Searches `data/products/*/theme_analysis.json` for matching review quotes
   - Calls Gemini API per block for quote selection and highlight phrase extraction
   - Outputs `data/curate_patch.json`

---

## Phase 3 — Merge

// turbo
1. Merge the curated patch into the draft:
   ```
   python tools/merge_curate.py
   ```
2. Upon completion, inform the user they can proceed to `/7_tone`.
