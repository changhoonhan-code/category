# `comparison_outline.json` Output Schema

> **Source of Truth**: Formerly `data_contracts.md` §2.7
> **Producer**: Structure Engineer | **Consumer**: Writer (primary input), Data Validator · Tone Editor · Head Writer (read-only reference)
> **Path**: `data/comparison_outline.json`
>
> The Structure Engineer's **structural decision artifact**. Fully replaces the legacy `scene_outline.json`.
> The Writer creates narration based on this file's scene/block structure and `notes`.

```jsonc
{
  // ── Strategic decisions carried through from Blueprint (do not modify) ──
  "video_question": "...",       // Passed through from Blueprint as-is
  "excluded_themes": [ ... ],    // Passed through from Blueprint as-is

  // ── Structure Engineer's structural decisions ──
  "scenes": [
    {
      "scene_id": "hook",
      "scene_type": "hook",
      "block_ids": ["hook_contradiction", "hook_curiosity_loop"],
      "block_pacing": {
        "hook_contradiction": "breathe",
        "hook_curiosity_loop": "dense"
      },
      "assigned_themes": [],
      "notes": "contradiction_source: cross_product (ANC Performance). product_a (68.9%) vs product_c (26.6%). Stage 1: Category-level question (zero product names). Stage 2: Contradiction reveal with product names as clauses. Stage 3: 2-3 theme teasers + category intelligence hint."
    },
    {
      "scene_id": "category_rating_overview",
      "scene_type": "category_rating_overview",
      "block_ids": ["rating_overview_lineup", "rating_overview_gap"],
      "block_pacing": {
        "rating_overview_lineup": "standard",
        "rating_overview_gap": "dense"
      },
      "assigned_themes": [],
      "notes": "SEO: All 3 product names MUST appear in rating_overview_lineup. Population Gap: product_b has largest gap (0.9). trap_signal: product_b is_trap=true — hint but reserve full exposé for later."
    },
    {
      "scene_id": "theme_anc_performance",
      "scene_type": "theme_comparison",
      "block_ids": ["anc_leader", "anc_laggard", "anc_context"],
      "block_pacing": {
        "anc_leader": "standard",
        "anc_laggard": "standard",
        "anc_context": "dense"
      },
      "assigned_themes": ["ANC Performance"],
      "notes": "narrative_directive: [Blueprint] Differentiator theme: use leader/laggard structure. Leverage contradiction_pairs. | [Structure] Hook payoff scene. anc_leader=product_a (pos 68.9%), anc_laggard=product_c (pos 26.6%). anc_context: mid-ranked product + resolution_hypothesis. teaser_payoff: resolved here."
    },
    {
      "scene_id": "standout",
      "scene_type": "standout",
      "block_ids": ["standout_product_a", "standout_product_b", "standout_product_c"],
      "block_pacing": {
        "standout_product_a": "breathe",
        "standout_product_b": "breathe",
        "standout_product_c": "breathe"
      },
      "assigned_themes": [],
      "notes": "standout_product_a: Wearing Comfort (pos 85%). standout_product_b: Ecosystem Integration (pos 85.7%). standout_product_c: Bluetooth Pairing (pos 87.5%). Each block: unique killer strength + recommended use case."
    },
    {
      "scene_id": "verdict",
      "scene_type": "verdict",
      "block_ids": ["verdict_category_judgment", "verdict_use_case_picks", "verdict_outro"],
      "block_pacing": {
        "verdict_category_judgment": "standard",
        "verdict_use_case_picks": "standard",
        "verdict_outro": "breathe"
      },
      "assigned_themes": [],
      "notes": "verdict_category_judgment: direct reference to category_intelligence. B-roll: all-themes × all-products matrix infographic. verdict_use_case_picks: horizontal differentiation only, NO single 'best' declaration. trap_warning: product_b. buy_if_sources: [ANC Performance, Wearing Comfort]. skip_if_sources: [Build Quality, Touch Control]."
    }
  ],

  // ── Teaser/Payoff Mapping ──
  "teaser_payoff_map": {
    "hook_curiosity_loop": {
      "teaser": "ANC performance gap (Short-term Bridge)",
      "resolved_in": "theme_anc_performance",
      "distance_scenes": 1
    }
  },

  // ── Runtime Metadata ──
  "runtime_metadata": {
    "total_blocks": 15,
    "block_cap": 22,
    "compression_log": []  // Compression history if runtime cap is exceeded
  }
}
```

## Field Rules

| Field | Rule |
|:---|:---|
| `video_question` | Carried through from Blueprint as-is. Structure Engineer modification **prohibited** |
| `excluded_themes` | Carried through from Blueprint as-is. Structure Engineer modification **prohibited** |
| `scenes[].notes` | Include Blueprint's `narrative_directive` with `[Blueprint]` prefix, then append structural supplements (data references, pacing rationale, payoff info) with `[Structure]` prefix. **Append-only** approach |
| `block_pacing` | Every entry in `block_ids` must have a corresponding pacing entry. Must comply with `scene_visual_pacing.md` §7 distribution rules |
| `teaser_payoff_map` | Track short-term teasers only. Climax teasers are not tracked. Maximum distance: 3 scenes |
| `runtime_metadata.compression_log` | Record compression/merge/drop history when block cap is exceeded. Empty array means no compression applied |
