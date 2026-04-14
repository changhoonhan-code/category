# Writer Output Schema & Quote Guidelines

Output Schema & Quote Guidelines for Writer Agent. For rules and constraints → `SKILL.md`.

---

## OUTPUT FORMAT (JSON)

Return ONLY valid JSON. Your output must be **EITHER** a Veto rejection **OR** a complete Draft Script.

### OPTION A: Veto (Structural Rejection)
If you absolutely cannot complete a block due to critically insufficient evidence or impossible logical constraints, return ONLY this root object:
```json
{
  "structural_rejection": {
    "reason": "Clear explanation of why the data does not support the Structure Engineer's instructions.",
    "veto_scope": "theme_selection" // or "block_count"
  }
}
```

### OPTION B: Complete Draft Script
If proceeding with the script, the top-level root object MUST include these global fields to prevent data loss in downstream stages:

1. `"thought_process"`: A mandatory string space. Write out your **3-Pass reasoning** (Skeleton → Muscle → Skin) here before generating the final narration blocks.
2. `"category_name"`: copied from `category_writer.json → category_name`
3. `"products"`: A lightweight array mapping `product_id` to `product_name`, e.g., `[{"product_id": "product_a", "product_name": "Bose..."}]`. Copied from `category_writer.json → products`.
4. `"excluded_themes"`: passed through exactly as received from Structure Engineer's `comparison_outline.json`
5. `"teaser_payoff_map"`: passed through exactly as received from Structure Engineer's `comparison_outline.json`

Every block MUST include all required fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `block_id` | string | ✅ | Unique ID (e.g., `hook_teaser`, `theme_battery_leader`) |
| `narration` | string | ✅ | Spoken narration text (English, written for voice) |
| `pacing_profile` | string | ✅ | Copied from Structure Engineer's `comparison_outline.json → block_pacing`. One of: `breathe`, `standard`, `dense` |
| `evidence_quotes` | EvidenceQuote[] | ✅ | Array of 0–5 structured review quotes (see Quote Selection Guidelines below). Use an empty array `[]` if no evidence is required for the block. |

> ⚠️ `bgm_mood` **MUST NOT** be included. It is not your field. It belongs to the Tone Editor later in the pipeline.
> ⚠️ `is_humorous` is defined ONLY inside `EvidenceQuote` objects. Do NOT add an `is_humorous` field at the block level.

## EvidenceQuote Object Structure

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `product_id` | string | ✅ | Which product this quote belongs to (e.g., `"product_a"`). Mandatory for Cross-Product traceability. |
| `review_id` | string | ✅ | Unique Amazon review identifier. Copy exactly from `category_writer.json`. |
| `highlight_phrase` | string | ✅ | The most impactful core phrase. MUST be a **verbatim, case-sensitive substring** of the original text. Length: **3–8 words target, 10 words max**. |
| `star_rating` | number | ✅ | The star rating for this quote, copied exactly from `category_writer.json`. |
| `is_humorous` | boolean | ✅ | Copied from `category_writer.json`. If missing, set based on your own judgment. |
| `review_date` | string/null | ❌ | Not available in the filtered writer profile. Omit from output. |
| `has_media` | boolean | ❌ | Not available in the filtered writer profile. Omit from output. |
| `selection_reason` | string | ✅ | `"anchor"` / `"contrast"` / `"hook"` / `"supplementary"`. Copied from `category_writer.json`. |

## evidence_quotes Core Rules

1. **Theme Blocks Require Evidence** — At least one quote is mandatory per breakdown/comparison block. Unsubstantiated claims are prohibited. Standout blocks may use empty arrays if no `best_quote` exists.
2. **Maximum 5 Quotes Per Block** — (practical ceiling: 2-3 in most blocks).
3. **`highlight_phrase` Extraction** — Must be exact substring, max 10 words. This is displayed visually.
4. **Narration ↔ Evidence Alignment** — Narration frames and analyzes; quote provides the verbatim proof visually. Narrator does NOT read the quote aloud.
5. **Structural Spoiler Ban** — Do NOT drag a quote from a later assigned theme into an earlier block. Quotes must stay within their Structure Engineer-assigned scene.
6. **Cross-Product Attribution** — In Theme Comparison logic, if you interleave quotes from different products, ensure `product_id` correctly identifies the source of the quote.

## Quote Selection Guidelines (Role-Based)

Use the predefined quotes provided in `category_writer.json` (`best_evidence`, `contradiction_pairs`, `best_quote`). Do NOT invent quotes or pull quotes outside of the provided JSON.

| `selection_reason` | Role | Application |
| --- | --- | --- |
| `"anchor"` | Validated core evidence | Lead with this quote. Best for establishing a product's primary strength or weakness. |
| `"contrast"` | Opposite sentiment / issue | Use to create tension, or represent a failure in another product (within `contradiction_pairs`). |
| `"hook"` | Naturally funny / ironic | Use as a punchline. |
| `"supplementary"` | Additional context | Use only if the block needs more depth. |

```json
// Example Output Structure (Comparative Analysis)
{
  "thought_process": "Pass 1 (Skeleton): Product C has strong call quality. Quote R7KVIZLI3PEF supports this. Product B fails. Quote R3FSXEBVA29KKZ shows this. Pass 2 (Muscle): Tie them together contrasting algorithm vs aggressive tuning. Pass 3 (Skin): Make sentences punchy for TTS.",
  "category_name": "Premium Open-Ear Headphones",
  "products": [
    {"product_id": "product_a", "product_name": "Bose Ultra Open"},
    {"product_id": "product_b", "product_name": "Shokz OpenFit"}
  ],
  "excluded_themes": [],
  "teaser_payoff_map": {
    "hook_curiosity_loop": {
      "teaser": "One model fails the wind test spectacularly",
      "resolved_in": "theme_comparison_call_quality",
      "distance_scenes": 2
    }
  },
  "scenes": [
    {
      "scene_id": "theme_comparison_call_quality",
      "blocks": [
        {
          "block_id": "call_quality_leader",
          "narration": "When it comes to rendering human voices, the algorithmic approach of the second contender drastically outperforms the rest. Even standing next to a loud fan, the microphones managed to isolate speech without aggressive compression.",
          "pacing_profile": "standard",
          "evidence_quotes": [
            {
              "product_id": "product_c",
              "review_id": "R7KVIZLI3PEF",
              "highlight_phrase": "heard and could hear just fine",
              "star_rating": 5,
              "is_humorous": false,
              "selection_reason": "anchor"
            }
          ]
        },
        {
          "block_id": "call_quality_laggard",
          "narration": "The first model, however, takes noise suppression too far. The aggressive tuning causes the caller's voice to sound thin and watery to whoever is on the other end.",
          "pacing_profile": "standard",
          "evidence_quotes": [
            {
              "product_id": "product_b",
              "review_id": "R3FSXEBVA29KKZ",
              "highlight_phrase": "like I'm underwater",
              "star_rating": 1,
              "is_humorous": false,
              "selection_reason": "contrast"
            }
          ]
        }
      ]
    }
  ]
}
```
