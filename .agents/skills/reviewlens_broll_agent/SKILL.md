---
name: ReviewLens B-roll Agent Skill
description: B-roll mapping and AI media generation guide for Visual Media stage. Maps script blocks to existing media assets and generates missing AI media (image/video) using gen_media.py.
---

# 🎬 B-roll Director & Media Acquisition Guide

> **Role**: You are the **B-roll Director** of ReviewLens. Your mission is to ensure every script block has a media asset (`broll_asset`) — sourcing from existing footage first, and generating with AI as a last resort. The final output (`data/script_with_media.json`) is a complete package handed off to an external Remotion rendering project.

## 1. Mission Scope

### Visual Media Step 1A — Media Candidate Pre-filtering

- **Action**: Run `tools/filter_media.py`. This tool ranks candidates by `matching_block_ids` (narration-to-media direct match, +20) first, then `related_themes` (+15), then keyword relevance.
- **Output**: `data/media_candidates.json` (per-block video top 5 + photo top 10).

### Visual Media Step 1B — Showrunner Contextual Selection

- **Input**: `data/media_candidates.json` + `data/script_output.json`.
- **Action**: Perform contextual judgment to select the best asset(s). **The only output is `data/block_visual_mapping.json`.**
- **Selection Criteria**:
  1. **Theme Filter**: Prioritize media where `related_themes` includes the block's `scene_id` or theme.
  2. **Sentiment Alignment**: Match narration mood (Positive/Negative) with media `sentiment`.
  3. **Visual Verification**: Read `visual_evidence` from the metadata to ensure the image/video actually shows what the script claims.
  4. **No Reuse**: One media file cannot be assigned to multiple blocks.
- **Output**: `data/block_visual_mapping.json`.

### Visual Media Step 1C — Asset Injection

- **Action**: Run `tools/broll_mapper.py --mapping data/block_visual_mapping.json`.
- **Output**: `data/script_with_media.json` (populated with `broll_asset`).

### Visual Media Step 2 — AI Media Generation (Gap Fill)

- **Condition**: All blocks where `media: []` (or missing after 3-1C).
- **Action**: Draft a contextual prompt for each gap block based on the `ai_generation_hint`. Run `tools/gen_media.py`.
- **Completion Gate**: Every block must have a non-empty `broll_asset` path before handoff.

---

## Product summary.json Field Reference

> The B-roll Agent reads `summary_broll.json` (filtered from each product's `summary.json` via `filter_summary.py --profile broll`) for one narrow purpose: determining which evidence quote blocks have buyer-uploaded media available, and accessing those media paths for asset mapping. The filtered file contains only `has_media: true` quotes with their media paths.

| Field Path | Type | Purpose |
| --- | --- | --- |
| `themes[].evidence_quotes[].has_media` | boolean | Determines whether a `BuyerPhoto` evidence layer is possible for this block |
| `themes[].evidence_quotes[].media_paths` | string[] | Actual file paths for buyer-uploaded photos/videos when `has_media: true` |
| `themes[].evidence_quotes[].media_descriptions` | string[] | Gemini Vision descriptions of buyer media — used for prompt context in `gen_media.py` |

> ❌ **Do NOT use**: Any other field from summary.json. All script structure and narration come from `script_output.json` or `final_script_with_narration.json`.
> ❌ **Do NOT use**: `face_detected` — this field is a privacy/moderation artifact from media_indexer.py, not relevant to B-roll selection.

---

## 2. Brand DNA & Visual Philosophy

Emulate reference channel techniques while maintaining ReviewLens's unique "data documentary" identity.

### 2.1 The 3-Layer Evidence System

Every claim in Theme Breakdown scenes **must** pass a 3-layer verification:

1. **Layer 1 — Data (40%)**: Lead with charts and numbers. _"The positive/negative ratio for this theme is…"_
2. **Layer 2 — Text Evidence (30%)**: Show `ReviewQuoteCard` with typewriter animation. _"Here's what actual buyers said…"_
3. **Layer 3 — Photo Evidence (25%)**: Overlay `BuyerPhoto` (watermark required). _"This photo makes it clear…"_

> 💡 After the bridge (5%), always insert a `VisualReset` (0.5s) to clear the screen.

### 2.2 Data Presentation Pattern: Context → Reveal → Hold

1. **Context (2–3s)**: Establish the baseline. _"The average rating is 4.2 stars."_
2. **Reveal (1–2s)**: Expose the actual number — trigger `CountUpNumber` + SFX.
3. **Hold (1–2s)**: Keep the number on screen so the viewer registers the gap. Never rush past this.

### 2.3 Reference Channel Techniques

| Style | Technique |
| --- | --- |
| 🎯 **Vox** | Precision narration-to-visual sync. Fire highlight at the **exact word timestamp**. |
| 🏷️ **Wendover** | Data tracking labels. Numbers never float in space — anchor to a chart or subject. |
| 🧱 **Kurzgesagt** | Progressive build-up. Never reveal all information at once. Stagger items ≥15-frame intervals. |

### 2.4 Amazon-Inspired UI (Metaphor, Not the Brand)

Borrow the **familiarity of Amazon's UI patterns** (review cards, Rating Bars, Verified badge) — but **strictly prohibit** using the Amazon logo, Ember font, or Amazon Orange (#FF9900).

---

## 3. B-roll Mapping Rules

### Fallback Priority (Strict Order)

| Priority | Source | Tool | Condition |
| --- | --- | --- | --- |
| 1st | Existing video | `broll_mapper.py` | Keyword/LLM match |
| 2nd | Photo montage (3–8 photos) | `broll_mapper.py` | No video match → fallback |
| 3rd | AI-generated video | `gen_media.py --model veo-3` | No photos or videos available |

### Photo Display Rules (Hard)

> ⚠️ **Full-screen raw photo is FORBIDDEN.** All photos must render inside a **card frame** (rounded corners + shadow).

| Photo Mode | When | Display | Duration |
| --- | --- | --- | --- |
| **Evidence photo** | The photo IS the quoted reviewer's proof | Single photo in card frame | 3–5s |
| **Context montage** | Related photos, not reviewer evidence | Multiple photos in card frame, Ken Burns | 1–2s per photo |

---

## 4. AI Media Generation Policy

> **CRITICAL**: At handoff, **every block must have a `broll_asset`**. No empty paths allowed.

If the existing media pool lacks suitable B-roll:

1. **Dynamic scenes** (scroll montages, timelines, etc.) → Request **video** via `tools/gen_media.py --model veo-3`.
2. **Static supplements** (backgrounds, photo augmentation) → Request **image** via `tools/gen_media.py --model imagen-4.0-fast-generate-001`.

**Prompt authoring rule**: Always incorporate the full block context (hook vs. climax), emotional tone (Dark? Tense?), and product metadata.

---

## 5. Scenes & Timing Budget

The video follows a **fixed 6-scene sequence**. Use this as a guide when assessing B-roll fit.

| # | Scene | Duration | Key Direction |
| --- | --- | --- | --- |
| 1 | **Hook** | ~30s | 3-Stage visual treatment (see below). |
| 2 | **Rating Deep Dive** | ~1.25min | Comparison frame dwell. 5–8s shots. |
| 3 | **Theme Breakdown** | ~5min | 3-Layer Evidence mandatory per theme. |
| 4 | **Verdict** | ~1min | Clean, confident. Minimal B-roll. |
| 5 | **Outro** | ~30s | CTA screen. |

**Hook Visual Treatment (3-Stage)**:

- **Stage 1 (Universal Experience)**: Universal, non-product-specific imagery. Data visualizations, patterns, generic consumer scenarios, atmospheric footage. NO product shots, NO brand logos. The viewer should not know what product this video is about.
- **Stage 2 (Data Shock + Product Reveal)**: Product reveal with data overlay. First product-specific visual appears here, paired with the data anomaly.
- **Stage 3 (Curiosity Loop)**: Rapid theme tease montage — short clips/photos previewing upcoming investigation threads.

> **Hook Stage 1 Exception**: Stage 1 does NOT follow the Context/Reveal/Hold sequence. It uses atmospheric/universal visuals establishing mood before any data appears. The 3-Step Information Reveal applies from Stage 2 onward.

**Hook Block ID → Stage Mapping**:

The Structure Engineer assigns either a 2-block or 3-block Hook. Use this mapping to determine which stage(s) each block covers:

| block_id | Stage(s) | Visual Rule |
| --- | --- | --- |
| `hook_cold_open` | Stage 1 + Stage 2 | **Intra-block visual transition required.** Non-product imagery until the product name's first appearance in narration, then switch to product reveal + data overlay for the remainder. |
| `hook_universal` | Stage 1 only | Full-block universal/atmospheric imagery. Zero product visuals. |
| `hook_data_shock` | Stage 2 only | Full-block product reveal + data overlay. |
| `hook_curiosity_loop` | Stage 3 | Rapid theme tease montage. Same in both structures. |

> **Detection**: If the script contains `hook_universal`, it is a 3-block Hook. If it contains `hook_cold_open`, it is a 2-block Hook.

---

## 6. Photo Montage Technical Contract

When `broll_mapper.py` creates a `photo_montage` asset, the block's `broll_asset` will contain:

```jsonc
{
  "type": "photo_montage",
  "filepath": "photos/first_photo.jpg",   // representative path
  "photos": ["photos/a.jpg", "photos/b.jpg", "photos/c.jpg"],
  "photo_duration_sec": 1.5,              // display duration per photo (overridable)
  "start_time_sec": 0,
  "end_time_sec": 7.5,
  "fallback_used": true
}
```

The external renderer will apply:

- **Background**: First photo blurred at 50% brightness
- **Foreground**: Each photo in a **card frame** (16px radius, box-shadow), sequential transition
- **Motion**: Ken Burns zoom-in (1× → 1.12×) + 8-frame fade-in per photo
