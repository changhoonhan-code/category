---
description: Script Decomposition — SSOT-first reverse-sync. raw_draft.md is the single source of truth; outline adapts to the draft.
---

# Script Decomposition (SSOT Reverse-Sync)

> **Core Principle**: `raw_draft.md` is the **Single Source of Truth (SSOT)**. The agent reads the draft, understands its natural semantic structure, and builds a new `draft_script.json` from scratch. The outline is consulted only for **schema reference** (field names, scene_type vocabulary, naming conventions) — never as a structural constraint.
>
> **Authority**: `raw_draft.md` is **read-only**. This agent has zero write access to the draft. No rewriting, no paraphrasing, no reordering of sentences, no trimming, no additions. Every character copied into `draft_script.json` must be byte-identical to the source.

## Prerequisites

1. Verify `data/raw_draft.md` exists. If missing, run `/4_write` first.
2. Verify `data/comparison_outline.json` exists. If missing, run `/3_draft` first.

---

## Step 1 — Load Schema Reference

Read `data/comparison_outline.json` and extract **only**:

- `scene_type` vocabulary (e.g., `hook`, `metric_chapter`, `verdict`)
- Block ID naming patterns (e.g., `{theme_key}_showdown`, `verdict_{product_key}`)
- `pacing` profile vocabulary (`breathe`, `standard`, `dense`)
- `assigned_themes` list (the theme names used in the pipeline)

Do NOT use the outline's block order, block count, or scene boundaries as constraints.

## Step 2 — Semantic Decomposition of the Draft

Read `data/raw_draft.md` as a continuous monologue. Analyze the prose contextually to identify natural **semantic segments** — passages that serve a single rhetorical purpose. Detect boundaries by:

- **Topic shifts**: When the subject changes from one theme to another (e.g., ANC discussion ends, battery discussion begins).
- **Rhetorical function shifts**: When the prose moves from data comparison to causal analysis, from category-level observation to product-specific warning, etc.
- **Product focus shifts**: When the text transitions from one product to another within a verdict context.

Do NOT rely on markdown headers (`##`), paragraph breaks, or any formatting. The Writer may or may not have used them consistently.

## Step 3 — Build Scene & Block Structure

For each semantic segment identified in Step 2:

1. **Assign a `scene_type`** from the schema vocabulary based on what the prose is doing.
2. **Assign a `block_id`** following the naming conventions from the schema.
3. **Assign a `pacing` profile** based on word count:
   - ≤ 60 words → `breathe`
   - 61–85 words → `standard`
   - 86+ words → `dense`
4. **Assign the exact prose text to the `narration` key**.
5. **Group blocks into scenes** by thematic coherence.

### Structural Rules

- **No empty blocks**: Every block must contain text from the draft.
- **No text left behind**: Every sentence in `raw_draft.md` must appear in exactly one block.
- **No rewriting**: Preserve the original wording verbatim. This is a structural operation, not a creative pass.
- **Scene order = draft order**: The scene/block sequence in `draft_script.json` must match the linear reading order of the draft.

### Block ID Naming Conventions

| Scene Type | Block ID Pattern | Examples |
|---|---|---|
| `hook` | `hook_contradiction`, `hook_curiosity_loop` | |
| `intro_credibility` | `intro_lineup`, `intro_gap` | |
| `metric_chapter` | `{theme_key}_showdown`, `{theme_key}_fallout`, `{theme_key}_context`, `{theme_key}_diagnosis`, `{theme_key}_spectrum` | `active_showdown`, `battery_fallout` |
| `verdict` | `verdict_{product_key}`, `verdict_conclusion` | `verdict_product_a`, `verdict_conclusion` |

## Step 4 — Save

1. Write the result to `data/draft_script.json`.
2. Confirm no empty blocks and no orphaned text.

## Completion

1. Confirm `data/draft_script.json` is saved.
2. Notify the user and mandate running `/6_curator` **in a brand new session**.
