# Quote Curator Output Schema

Output Schema for Quote Curator. For rules and constraints → `SKILL.md`.

---

## OUTPUT FORMAT (JSON)

You must use the `write_to_file` tool to save your completed output directly to `data/draft_script.json`.
- Do not wrap your output in Python scripts.
- Take the entire `data/draft_narration.json` and produce `data/draft_script.json`. You must populate `evidence_quotes`, `headline`, and `title`. All other fields must pass through unchanged.

### EvidenceQuote Object Structure

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `product_id` | string | ✅ | Which product this quote belongs to (e.g., `"product_a"`). Mandatory for Cross-Product traceability. |
| `review_id` | string | ✅ | Unique Amazon review identifier. Copy exactly from `category_writer.json`. |
| `highlight_phrase` | string | ✅ | The most impactful core phrase. MUST be a **verbatim, case-sensitive substring** of the original text. Length: **3–8 words target, 12 words max**. |
| `star_rating` | number | ✅ | The star rating for this quote, copied exactly from `category_writer.json`. |
| `selection_reason` | string | ✅ | `"anchor"` / `"contrast"` / `"hook"` / `"supplementary"`. See SKILL.md for assignment rules. |

> ⚠️ `review_date` and `has_media` are NOT available in the filtered writer profile. Omit from output.



## Example Output Structure

The output is the full `draft_narration.json` with `evidence_quotes` populated:

```json
{
  "thought_process": "...(preserved from Writer)...",
  "critique_log": [
    {
      "fix_type": "[Coverage Warning]",
      "reason": "Theme only had 3 unique quotes available after deduplication."
    }
  ],
  "category_name": "{Category Name}",
  "video_question": "...(preserved from Writer)...",
  "products": [
    {"product_id": "product_a", "product_name": "{Product A Name}"},
    {"product_id": "product_b", "product_name": "{Product B Name}"}
  ],
  "excluded_themes": [],
  "teaser_payoff_map": {},
  "scenes": [
    {
      "scene_id": "hook_scene",
      "scene_type": "hook",
      "blocks": [
        {
          "block_id": "hook_contradiction",
          "title": "",
          "narration": "...(preserved from Writer)...",
          "pacing_profile": "breathe",
          "evidence_quotes": []
        }
      ]
    },
    {
      "scene_id": "theme_comparison_{theme_key}",
      "scene_type": "theme_comparison",
      "headline": "{Theme Headline}",
      "assigned_themes": ["{Theme Name}"],
      "blocks": [
        {
          "block_id": "{theme_key}_showdown",
          "title": "{Product}: {X}% Positive",
          "narration": "...(preserved from Writer)...",
          "pacing_profile": "standard",
          "evidence_quotes": [
            {
              "product_id": "product_c",
              "review_id": "R2G6WL6A2QT5YS",
              "highlight_phrase": "{impactful phrase about strength}",
              "star_rating": 5,
              "selection_reason": "anchor"
            },
            {
              "product_id": "product_c",
              "review_id": "R1ABC2DEF3GHI",
              "highlight_phrase": "{another supporting positive phrase}",
              "star_rating": 5,
              "selection_reason": "supplementary"
            },
            {
              "product_id": "product_a",
              "review_id": "R4JKL5MNO6PQR",
              "highlight_phrase": "{phrase highlighting a flaw}",
              "star_rating": 2,
              "selection_reason": "contrast"
            },
            {
              "product_id": "product_b",
              "review_id": "R7STU8VWX9YZA",
              "highlight_phrase": "{another phrase showing failure}",
              "star_rating": 1,
              "selection_reason": "contrast"
            },
            {
              "product_id": "product_c",
              "review_id": "R0BCD1EFG2HIJ",
              "highlight_phrase": "{contextual phrase confirming pattern}",
              "star_rating": 5,
              "selection_reason": "supplementary"
            }
          ]
        }
      ]
    }
  ]
}
```
