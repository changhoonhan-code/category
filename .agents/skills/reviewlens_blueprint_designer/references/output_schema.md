# `comparison_blueprint.json` Output Schema

> **Source of Truth**: `data_contracts.md` §2.5
> **Producer**: Blueprint Designer | **Consumer**: Structure Engineer (primary input) + Writer (read-only reference)
> **Path**: `data/comparison_blueprint.json`
>
> The Blueprint Designer's **strategic decision artifact**. Contains the answer to "what will we show?"
> The Structure Engineer uses this file to determine scene order, block count, and pacing.

```jsonc
{
  // ── Video Investigation Question ──
  // Product names prohibited. Category-level universal question (brand_identity.md §1, §3)
  "video_question": "Why does every bestseller in this category share the exact same fatal flaw?",

  // ── Hook Contradiction Selection ──
  // Selected from category_blueprint.json contradiction_pairs
  // Priority: Cross-Product > Within-Product > Expectation Gap (scene_visual_pacing.md §6)
  "selected_hook_contradiction": {
    "source": "cross_product",        // "cross_product" | "within_product" | "expectation_gap"
    "theme_name": "ANC Performance",   // Theme containing the contradiction
    "product_ids": ["product_a", "product_c"],  // Related products (single product for within-type)
    "contradiction_summary": "Product A leads ANC at 68.9% positive; Product C trails at 26.6% — yet both are $200+ bestsellers.",
    "selection_rationale": "Largest cross-product positive_ratio gap (0.423) in the highest-interest theme. Creates immediate 'why?' tension for viewers who assume premium = consistent quality."
  },

  // ── Selected Theme List ──
  // Curated from ~10 common_themes down to 4–5 (scene_visual_pacing.md §7 block cap)
  "selected_themes": [
    {
      "theme_name": "ANC Performance",
      "category_pattern_type": "differentiator",  // From category_blueprint.json
      "narrative_directive": "Differentiator theme: user experiences diverge sharply across products. Use leader/laggard narrative structure. Must leverage contradiction_pairs data.",
      "selection_rationale": "Highest category interest + cross-product contradiction exists. Payoff scene for Hook contradiction.",
      "has_contradiction_pairs": true,
      "block_hint": 3  // Recommended to Structure Engineer (final decision rests with Structure)
    },
    {
      "theme_name": "Build Quality",
      "category_pattern_type": "universal_weakness",
      "narrative_directive": "Category structural limitation: frame as 'weakness of the entire category' rather than individual product comparison. Foreshadowing for category_intelligence conclusion.",
      "selection_rationale": "All products negative_ratio > 60%. Core evidence for category maturity narrative.",
      "has_contradiction_pairs": false,
      "block_hint": 2
    }
    // ... remaining selected themes
  ],

  // ── Standout Mapping ──
  // Mapped from category_blueprint.json unique_strengths
  "standout_mapping": [
    {
      "product_id": "product_a",
      "theme_name": "Wearing Comfort",
      "why_unique": "Only product maintaining 85%+ positive ratio in comfort despite premium weight.",
      "recommended_use_case": "Extended listening sessions (commute, office)"
    }
    // ... one per product
  ],

  // ── Verdict Strategy ──
  "verdict_sources": {
    "category_intelligence_ref": true,   // Whether to reference category_intelligence data
    "trap_products": ["product_b"],      // Products where is_trap === true
    "buy_if_themes": ["ANC Performance", "Wearing Comfort"],   // Themes for Buy-If recommendations
    "skip_if_themes": ["Build Quality", "Touch Control"]       // Themes for Skip-If warnings
  },

  // ── Excluded Themes ──
  "excluded_themes": [
    {
      "theme_name": "Warranty and Support",
      "exclusion_reason": "Only appears in 2 products. Combined mention_count of 18 — insufficient narrative value at the category level."
    }
    // ... remaining excluded themes
  ]
}
```

## Field Rules

| Field | Rule |
|:---|:---|
| `video_question` | Product/brand names prohibited. Must pass the test: "Would someone with zero interest in this category still be curious?" |
| `selected_hook_contradiction.source` | Priority: `cross_product` > `within_product` > `expectation_gap` |
| `selected_hook_contradiction.selection_rationale` | **Required**. Critical field for preventing context loss — record the selection rationale in natural language |
| `selected_themes[].narrative_directive` | Dynamic narration approach directive based on `category_pattern_type`. Structure Engineer includes in `notes`, Writer references for final output |
| `selected_themes[].selection_rationale` | **Required**. Record the rationale for including this theme |
| `selected_themes[].block_hint` | Advisory value. May be overridden by Structure Engineer's final decision |
| `standout_mapping` | 1:1 mapping from `category_blueprint.json` `unique_strengths`. Products without a unique strength have no Standout block |
| `verdict_sources.trap_products` | Only products where `category_blueprint.json` `products[].trap_candidate.is_trap === true` |
| `excluded_themes[].exclusion_reason` | Qualitative justification required. Exclusion based solely on numbers is prohibited |
