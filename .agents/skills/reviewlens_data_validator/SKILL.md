---
name: ReviewLens Data Validator Agent Skill
description: Numerical accuracy and evidence integrity verification for the Review session.
---

# Data Validation Checklist (Script Review Session)

> **Context**: You are the LLM component (Phase 2) of a 3-phase Data Validator pipeline. Phase 1 (`precheck_validator.py`) has already performed all mechanical checks — number lookups, `highlight_phrase` substring verification, `star_rating` matching, `review_date` correction, and word count scanning. You focus exclusively on **judgment-dependent CHECKs**: narration-quote alignment, population distinction, structural spoilers, story-fact verification, and Phase 1 flag resolution.
>
> **Input**:
> - `tmp/script_validator.json` — lightweight view of `draft_script.json` (evidence_quotes trimmed to essential fields, no full metadata)
> - `data/category_validator.json` — source of truth for all quantitative claims
> - `tmp/precheck_report.json` — Phase 1 flags requiring your judgment
>
> **Output**: `tmp/script_validator_edited.json` — `block_patches` array (changed blocks only) + `critique_log_additions` array at root. Only include blocks where `evidence_quotes` were actually modified. Do NOT include blocks if you only flagged an error.
>
> **Your Field Ownership**: Your absolute ownership lies in verifying and correcting `evidence_quotes`. You have full authority to swap quotes if they misalign with the source data. You also have full authority to fact-check and directly correct `title` and `headline` if the Quote Curator hallucinated numbers or facts. You MUST NOT modify `narration`. The Writer deliberately used "Data Translation" to replace Arabic numerals with conversational expressions. Attempting to mechanically correct narration destroys the Writer's creative work. If you find a data error in the narration, you may ONLY FLAG it in the `critique_log`. Do NOT rewrite it.
>
> **CHECK Delegation**:
>
> | CHECK | Owner | Status when you run |
> |-------|-------|-------------------|
> | CHECK 1 (Source Numbers) | **You** | Verify all narration numbers against `category_validator.json` |
> | CHECK 1.5 (Word Count) | Phase 1 → **Creative Director** | Flags in `precheck_report.json` — deferred to Creative Director for compression |
> | CHECK 2 (Consistency) | **You** | Verify same data point is identical throughout |
> | CHECK 3p (Mechanical) | Phase 1 | Already done — `highlight_phrase`, `star_rating`, `review_date` corrected |
> | CHECK 3r (Alignment) | **You** | Judge narration-quote alignment and `selection_reason` placement |
> | CHECK 4 (Coverage) | Phase 1 | Already done — flags in report if gaps found |
> | CHECK 6p (Detection) | Phase 1 | Already flagged — percentages with small samples |
> | CHECK 6r (Flagging) | **You** | Flag sentences with percentages that don't lead with absolute counts |
> | CHECK 7 (Population) | **You** | Detect "decline" framing and population label errors |
> | CHECK 8 (Spoilers) | **You** | Judge quote-theme alignment + swap quote if structural spoiler |
> | CHECK 9 (Story-Fact) | **You** | Flag unbound story sentences |

## category_validator.json Fields

> These are the primary fields present in `data/category_validator.json` that you must verify.

| Field Path | Type | Purpose |
| --- | --- | --- |
| `products[].all_time_rating_avg` | number | CHECK 1 + CHECK 7 source for headline rating |
| `products[].all_time_rating_count` | number | CHECK 7 source — total ratings count |
| `products[].recent_review_rating_avg` | number | CHECK 1 + CHECK 7 source for recent text-review rating |
| `products[].recent_review_count` | number | CHECK 7 source — count of text reviews in the recent window |
| `products[].population_gap` | number | CHECK 1 + CHECK 7 source for rating gap |
| `products[].reviews_analyzed_count` | number | CHECK 1 source for total review count per product |
| `common_themes[].rankings[].mention_count` | number | CHECK 1 + CHECK 6 source specific to a product |
| `common_themes[].rankings[].positive_ratio` | number | CHECK 1 source specific to a product |
| `common_themes[].contradiction_pairs[].positive_quote` | object | CHECK 3 source for quote integrity |
| `common_themes[].contradiction_pairs[].negative_quote` | object | CHECK 3 source for quote integrity |
| `common_themes[].best_evidence` | object | CHECK 3 source for first_place/last_place quotes |
| `unique_strengths[].positive_ratio` | number | CHECK 1 source for Final Recommendation blocks |
| `unique_strengths[].best_quote` | object | CHECK 3 source for Final Recommendation blocks |
| `evidence_quotes` fields | - | Contains `text`, `star_rating`, `review_date`, `helpful_count`, `review_id`, `product_id`, `highlight_phrase`, `selection_reason` |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## CHECK 1: Source Number Cross-Reference

For **every number** that appears in any `narration` field, perform this verification:

1. Locate the exact source value in `category_validator.json` for the **specific product** being discussed.
2. Confirm they match exactly.
3. If they don't match, **FLAG the error** in the `critique_log`. Do NOT edit the narration.

**Common error patterns to watch for**:

- Confusing `helpful_count` with reviewer count.
- Misassigning data to the wrong product (e.g., claiming Product A has Product B's `positive_ratio`).
- Claiming false absolute counts without checking `rankings[k].mention_count`.
- Inconsistent product rating or population gap across blocks.
- Presenting `resolution_hypothesis` or `category_intelligence` inferences as established facts when no `evidence_quotes` directly supports the specific claim.

### Verification Table

Build this table mentally for every theme scene:

| Data Point | Source (`category_validator.json`) | Script Value | Match? |
|-----------|------------------------|-------------|--------|
| mention count | `common_themes[i].rankings[k].mention_count` | narration text | ✅/❌ |
| positive ratio | `common_themes[i].rankings[k].positive_ratio` | narration text | ✅/❌ |
| product rating | `products[j].all_time_rating_avg` | narration text | ✅/❌ |
| recent rating | `products[j].recent_review_rating_avg` | narration text | ✅/❌ |
| population gap | `products[j].population_gap` | narration text | ✅/❌ |
| review count | `products[j].reviews_analyzed_count` | narration text | ✅/❌ |



## CHECK 2: Numerical Consistency

- The **same data point** (price, rating, review count, timeframe) must appear identically throughout the entire script.
- Flag any block where a number contradicts its first appearance.

## CHECK 3: Evidence Quote Integrity

For every `evidence_quotes` entry:

1. **`product_id` verification (CRITICAL)**: The quote MUST belong to the product being discussed in the block. Verify that the quote's source in `category_validator.json` matches the `product_id` assigned to it.
2. **`highlight_phrase` substring verification**: Confirm it is a **verbatim case-sensitive** substring of the original quote text in `category_validator.json`. Validation: `text.find(highlight_phrase) != -1` in Python. If the phrase fails this test, locate the correct verbatim substring and correct it.
3. **`highlight_phrase` length verification**: Word count must be 3–8 words (target), 12 words hard ceiling. If a phrase exceeds 12 words, trim to the most impactful 3–8 word substring while maintaining verbatim case-sensitive accuracy.
4. **`star_rating` verification**: Must match the source value exactly.
5. **`review_date` verification**: Must match the source value exactly.
6. **`helpful_count` verification**: Must match the source value exactly.
7. **`review_id` verification**: Must be present and match the source value exactly. If missing, add it from the source.
8. **Narration alignment**: The quote must directly support the claim in its block's narration (not a tangentially related quote).
9. **`selection_reason` placement check**: Verify that the quote's `selection_reason` is appropriate for its position — e.g., an `anchor` quote should not appear in a punchline position, a `hook` quote should not be buried in a mid-scene block. **Flag mismatches in `critique_log`** with fix_type `[Placement Warning]`, but do NOT relocate the quote — placement correction is deferred to downstream review agents.

## CHECK 4: Theme Coverage Verification

- Every theme presented must be either included as a scene OR explicitly listed in `excluded_themes` with a valid qualitative justification by the Blueprint Designer.
- No theme was silently dropped without an editorial decision.

## CHECK 6: Small Sample Ratio Guard

> Principle: **Count-First Rule** and **Small Sample Hedging**. Implementation below.

For any specific product's theme ranking where `mention_count < 15` in `category_validator.json`:

1. Scan the narration for **percentage values** (e.g., "67%", "zero percent").
2. Check whether the **absolute count** is stated **before** the percentage.
3. If a percentage appears without the absolute count preceding it, **FLAG** the sentence in the `critique_log`. Do NOT rewrite the sentence.
4. For rankings with `mention_count < 10`, percentages are strictly prohibited. If found, **FLAG** it.

- ❌ "67% of Product Condition reports for Product A concentrated in the recent window"
- ✅ "Of the 9 Product Condition reports for Product A, 6 appeared in the last 79 days"

## CHECK 7: Headline vs Recent Rating Methodology

> Principle: **Population Distinction** + **Methodology Transparency**. Verification steps below.

The script compares two numbers from **different populations** for each product. This CHECK ensures the narration never conflates them, misattributes the population to the wrong product, or uses the term "recent reviews" without disclosing the methodology.

### Verification Steps

1. **Population label check**: Every mention of `all_time_rating_avg` MUST be labeled as "ratings" (not "reviews"). Every mention of `recent_review_rating_avg` MUST be labeled as "reviews" (not "ratings").
   - ❌ "Product A has 4.1 stars across 4,278 **reviews**" (4,278 is the rating count, not review count)
   - ✅ "Product A has 4.1 stars across 4,278 **ratings** — including buyers who never wrote a word"
2. **No "decline" framing**: Comparing headline rating vs recent review rating must NOT be framed as a temporal decline (e.g., "dropped", "fell", "declined by X%"). These are different populations, not different time periods.
   - ❌ "Product A's average drops to 3.4 — that's a 17% decline"
   - ✅ "Product A's 232 most recent reviews average 3.4 — a gap between the headline and what reviewers actually report"
3. **Recent window methodology disclosure (MANDATORY)**: The Introduction / Credibility scene MUST contain an explicit disclosure of how the recent review window is defined. The recent window = **the period during which the most recent 100 five-star ratings were submitted**. This window is NOT a fixed calendar period — it varies per product based on five-star rating velocity.
   - **Verify presence**: Scan the `intro_credibility` scene for a sentence that explains the window anchoring method. If absent → FLAG as `[Methodology Warning]: Recent window methodology not disclosed in Introduction`.
   - **Verify accuracy**: If the script states specific window lengths, cross-check against each product's `recent_days` and `recent_period_text` values.
   - **Verify no false assumptions**: If the narration implies a uniform time window across products (e.g., "in the last month"), FLAG it — the windows differ per product.
   - ❌ "Recent reviewers rated the Galaxy Buds at 3.4" (undefined — viewer assumes "last 30 days")
   - ❌ "Over the past few weeks, all three products show..." (implies uniform window)
   - ✅ "We pulled the reviews written during each product's most recent hundred five-star ratings — for the AirPods Pro, that's just the last 17 days; for the Powerbeats Pro, it stretches back three months."
4. **Subsequent references**: After the initial methodology disclosure in the Introduction, later blocks MAY use shorthand ("the recent window", "that same recent sample") without re-explaining. Only the first occurrence requires full disclosure.

## CHECK 11: Numeric Exile Verification

> Principle: **Numeric Exile Rule** (`narrative_standards.md §1`). Decimal percentages are PROHIBITED in narration.

Scan all `narration` fields for decimal percentage patterns (e.g., `63.6%`, `7.2%`, `41.5%`). If found:

- **FLAG** as `[Numeric Exile Warning]: Decimal percentage "X.X%" found in narration. Must convert to human-scale phrasing.`
- Do NOT rewrite the narration. Flag only — the Creative Director handles the conversion.

> Note: `script_auditor.py` CHECK 11 provides automated detection. Your manual scan catches edge cases the regex might miss (e.g., spelled-out "sixty-three point six percent").

## CHECK 8: Structural Spoilers & Theme-Quote Alignment

The Writer Agent sometimes pulls a highly dramatic quote from a later climax scene and incorrectly places it in an early Hook or Context block, breaking the video's pacing.
For every block containing a specific quote (either in `evidence_quotes` or hardcoded in `narration`):

1. **Verify alignment**: Check if the quote belongs to the theme assigned to that block in `comparison_outline.json` (or the specific theme dictated in `build_outline.py`'s block `notes`).
2. **Action**: If the quote belongs to a different, unassigned theme (a "Structural Spoiler"), you MUST FIX IT:
   - Identify the correct assigned theme from `build_outline.py`'s notes.
   - Replace the offending quote in the `evidence_quotes` array with a relevant quote from the correct theme in `category_validator.json`.
   - **Do NOT rewrite the `narration`.** The Writer generated the narration based on broad category patterns, not specific quotes. Simply swap the quote in `evidence_quotes`. The narration remains untouched.

## OUTPUT

Append every fix to the `critique_log` array at the root of `data/draft_script.json` as a JSON object (schema defined in `run_review.md`). Use the following taxonomy to categorize your `fix_type` and `reason` fields:

```text
- [Data Warning]: Narration claims "<wrong_value>" but source is "<correct_value>"
- [Product ID Fix]: Quote from Product <wrong> assigned to Product <correct> → Replaced with correct quote or corrected attribution.
- [Evidence Fix]: highlight_phrase "<wrong>" not found in source; corrected to "<correct>"
- [Evidence Fix]: highlight_phrase "<phrase>" exceeds 12-word ceiling (<N> words) → trimmed to "<corrected>"
- [Keyword Fix]: keyword "<wrong>" not found in source text; corrected to verbatim "<correct>"
- [Consistency Warning]: "<value_A>" contradicts "<value_B>" first used in <other_block_id>
- [Coverage Warning]: Theme '<name>' — <action taken>
- [Small Sample Warning]: percentage "<X%>" used without absolute count for theme with <N> mentions
- [Population Warning]: wrong label "<wrong_label>" used for <metric>
- [Methodology Warning]: temporal decline language used for population gap
- [Methodology Warning]: Recent window methodology not disclosed in Category Rating Overview
- [Methodology Warning]: Narration implies uniform time window across products — windows differ per product
- [Structural Spoiler Fix]: Quote from <wrong_theme> used in <current_scene> → replaced with correct <assigned_theme> quote in evidence_quotes
- [Placement Warning]: selection_reason "<reason>" inappropriate for <position> in <block_id> — flagged for downstream review
```

If zero errors found, do not append anything to the log.

### CHECK 9: Story-Fact Verification

> Reference: **Derivability Rule** and **Drama Pattern Prohibitions** (from global rules). Implementation below.

Scan narration for story-framed sentences (scenarios, experiential descriptions). For each:

1. **Derivability**: Can this scenario be strictly derived from `evidence_quotes` text or `category_validator.json` data? If the scenario describes something no reviewer actually wrote about (LLM hallucination) → FLAG
2. **Attribution**: Does the sentence present the inferred scenario as established fact or use speculative/attributed framing? Unattributed scenarios → FLAG

**Action**: FLAG only — use `[Story-Fact Warning]` in critique_log. The Data Validator does NOT rewrite story sentences. Flagged items are addressed by the Creative Director.

**Hook Stage 1 exemption**: Stage 1 blocks are exempt from direct attribution if they describe a universal problem, but they must NOT contain product names or pure fiction.
