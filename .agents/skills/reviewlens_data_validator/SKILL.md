---
name: ReviewLens Data Validator Agent Skill
description: Numerical accuracy and evidence integrity verification for the Review session.
---

# Data Validation Checklist (Script Review Session)

> **Context**: You are reviewing a `draft_script.json` written by someone else. You have NEVER seen this script before — examine it with fresh eyes. Cross-reference every number and quote against the category analysis file (the source of truth).

> **Input**: `data/draft_script.json` + `data/category_validator.json`
> **Output**: Updated `data/draft_script.json`
> **Your Field Ownership**: You may ONLY modify numerical values within `narration` text and `evidence_quotes` metadata. Do NOT touch tone, bgm_mood, or scene order. Crucially, you MUST preserve all root-level metadata (e.g., `category_name`, `products`, `excluded_themes`, `teaser_payoff_map`) unchanged. Do NOT drop them.

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
| `unique_strengths[].positive_ratio` | number | CHECK 1 source for Standout blocks |
| `unique_strengths[].best_quote` | object | CHECK 3 source for Standout blocks |
| `evidence_quotes` fields | - | Contains `text`, `star_rating`, `review_date`, `helpful_count`, `review_id`, `product_id` |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## CHECK 1: Source Number Cross-Reference

For **every number** that appears in any `narration` field, perform this verification:

1. Locate the exact source value in `category_validator.json` for the **specific product** being discussed.
2. Confirm they match exactly.
3. If they don't match, **correct the narration** and log the fix.

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

## CHECK 1.5: Pacing & Word Count Guard

When rewriting sentences to fix data errors (e.g., in CHECK 6), you MUST respect the Writer's pacing budget. The total `narration` must stay within the block's `pacing_profile` budget.

> Principle: **`.agents/rules/scene_visual_pacing.md` §7 Pacing Profiles**. If no `pacing_profile` field exists, treat as `standard` (legacy default).

If your correction inflates the word count, rigorously compress the surrounding filler text.

## CHECK 2: Numerical Consistency

- The **same data point** (price, rating, review count, timeframe) must appear identically throughout the entire script.
- Flag any block where a number contradicts its first appearance.

## CHECK 3: Evidence Quote Integrity

For every `evidence_quotes` entry:

1. **`product_id` verification (CRITICAL)**: The quote MUST belong to the product being discussed in the block. Verify that the quote's source in `category_validator.json` matches the `product_id` assigned to it.
2. **`highlight_phrase` substring verification**: Confirm it is a **verbatim case-sensitive** substring of the original quote text in `category_validator.json`. Validation: `text.find(highlight_phrase) != -1` in Python. If the phrase fails this test, locate the correct verbatim substring and correct it.
3. **`highlight_phrase` length verification**: Word count must be 3–8 words (target), 10 words hard ceiling. If a phrase exceeds 10 words, trim to the most impactful 3–8 word substring while maintaining verbatim case-sensitive accuracy.
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

> Principle: **`.agents/rules/evidence_integrity.md` §4 Rule 6**. Implementation below.

For any specific product's theme ranking where `mention_count < 15` in `category_validator.json`:

1. Scan the narration for **percentage values** (e.g., "67%", "zero percent").
2. Check whether the **absolute count** is stated **before** the percentage.
3. If a percentage appears without the absolute count preceding it, **rewrite** the sentence to lead with the absolute number.
4. For rankings with `mention_count < 10`, percentages should be **removed entirely** — use only absolute numbers.

- ❌ "67% of Product Condition reports for Product A concentrated in the recent window"
- ✅ "Of the 9 Product Condition reports for Product A, 6 appeared in the last 79 days"

## CHECK 7: Headline vs Recent Rating Methodology

> Principle: **`.agents/rules/evidence_integrity.md` §10 — Population Distinction Rules**. Verification steps below.

The script compares two numbers from **different populations** for each product. This CHECK ensures the narration never conflates them or misattributes the population to the wrong product.

### Verification Steps

1. **Population label check**: Every mention of `all_time_rating_avg` MUST be labeled as "ratings" (not "reviews"). Every mention of `recent_review_rating_avg` MUST be labeled as "reviews" (not "ratings").
   - ❌ "Product A has 4.1 stars across 4,278 **reviews**" (4,278 is the rating count, not review count)
   - ✅ "Product A has 4.1 stars across 4,278 **ratings** — including buyers who never wrote a word"
2. **No "decline" framing**: Comparing headline rating vs recent review rating must NOT be framed as a temporal decline (e.g., "dropped", "fell", "declined by X%"). These are different populations, not different time periods.
   - ❌ "Product A's average drops to 3.4 — that's a 17% decline"
   - ✅ "Product A's 232 most recent reviews average 3.4 — a gap between the headline and what reviewers actually report"
3. **Recent window methodology**: If the script explains how the recent window is calculated, verify it matches the products' recent days.

## CHECK 8: Structural Spoilers & Theme-Quote Alignment

The Writer Agent sometimes pulls a highly dramatic quote from a later climax scene and incorrectly places it in an early Hook or Context block, breaking the video's pacing.
For every block containing a specific quote (either in `evidence_quotes` or hardcoded in `narration`):

1. **Verify alignment**: Check if the quote belongs to the theme assigned to that block in `comparison_outline.json` (or the specific theme dictated in the Structure Engineer's block `notes`).
2. **Action**: If the quote belongs to a different, unassigned theme (a "Structural Spoiler"), you MUST:
   - Identify the correct assigned theme from the Structure Engineer's notes.
   - Replace the offending quote with a relevant quote from the correct theme in `category_validator.json`.
   - Completely rewrite the block's `narration` to seamlessly integrate the correct quote while respecting the pacing budget constraint (max 85 words). The rewritten narration **MUST follow the Quote Voicing Rule**: narrator paraphrases the quote's meaning; the verbatim text is displayed on screen only. Narrator must NOT read the full quote aloud.

## OUTPUT

Append every fix to the `critique_log` array at the root of `data/draft_script.json` as a JSON object (schema defined in `run_review.md`). Use the following taxonomy to categorize your `fix_type` and `reason` fields:

```text
- [Data Fix]: "<original_value>" → "<corrected_value>" — source: category_validator.json
- [Product ID Fix]: Quote from Product <wrong> assigned to Product <correct> → Replaced with correct quote or corrected attribution.
- [Evidence Fix]: highlight_phrase "<wrong>" not found in source; corrected to "<correct>"
- [Evidence Fix]: highlight_phrase "<phrase>" exceeds 10-word ceiling (<N> words) → trimmed to "<corrected>"
- [Consistency Fix]: "<value_A>" contradicts "<value_B>" first used in <other_block_id>
- [Coverage Warning]: Theme '<name>' — <action taken>
- [Small Sample Fix]: percentage "<X%>" used without absolute count for theme with <N> mentions → rewritten to lead with absolute count
- [Population Fix]: "<wrong label>" → "<correct label>" — headline rating uses "ratings", recent uses "reviews"
- [Methodology Fix]: temporal decline language used → reframed as population gap
- [Structural Spoiler Fix]: Quote from <wrong_theme> used in <current_scene> → replaced with correct <assigned_theme> quote and rewrote block
- [Placement Warning]: selection_reason "<reason>" inappropriate for <position> in <block_id> — flagged for downstream review
```

If zero errors found, do not append anything to the log.

### CHECK 9: Story-Fact Verification

> Authority: **`.agents/rules/evidence_integrity.md` §4 Rule 8** and **`.agents/rules/evidence_integrity.md` §9**

Scan narration for story-framed sentences (scenarios, experiential descriptions). For each:

1. **Derivability**: Can this scenario be derived from `evidence_quotes` text or `category_validator.json` data? If the scenario describes something no reviewer actually wrote about → FLAG
2. **Attribution**: Does the sentence present the scenario as established fact or use speculative/attributed framing? Unattributed scenarios → FLAG
3. **Binding**: Is the sentence data-bound (direct, adjacent, or speculative binding per `.agents/rules/evidence_integrity.md` §4 Rule 8)? Floating narrative → FLAG

**Action**: FLAG only — use `[Story-Fact Warning]` or `[Story-Data Binding Warning]` in critique_log. The Data Validator does NOT rewrite story sentences. Flagged items are addressed by the Tone Editor (CHECK 8) or Head Writer.

**Hook Stage 1 exemption**: Stage 1 blocks are exempt from direct binding (they connect to Stage 2), but they must NOT contain product names or unattributed fiction.
