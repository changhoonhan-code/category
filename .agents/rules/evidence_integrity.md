---
trigger: manual
---

# Evidence & Data Integrity Rules

## §3 — The 3-Layer Evidence System (Core Differentiation)

Every major insight MUST be backed by all three layers to build unshakeable viewer trust:

| Layer | Weight | Rule |
| ----- | ------ | ---- |
| **Data Layer** | ~40% | Statistics + comparison baseline. **Numbers without context are dead** — always pair with a baseline. Baselines include: category-wide averages from `category_analysis.json`, cross-product `positive_ratio` deltas (`common_themes[].rankings`), and `population_gap` differentials. (e.g., "The category average negative ratio for battery is 58% — but Product C sits at just 29%") |
| **Text Evidence Layer** | ~30% | Verified Purchase review quotes with `highlight_phrase` animations proving the pattern. **Cross-Product Quoting**: When contrasting quotes from different products in the same theme, each quote MUST carry its `product_id` label. Never quote the same product twice consecutively in a comparison block — interleave products |
| **Visual Evidence Layer** | ~25% | Authentic buyer-uploaded photos inside card frames (full-screen is forbidden; card frame + shadow required). **Cross-Product Interleaving**: In comparison scenes, no single product's media may run for more than 5 consecutive seconds (`scene_visual_pacing.md` §8) |
| **Transition (VisualReset)** | ~5% | 0.5s screen clear between segments — not a content layer |

## §4 — Data Integrity Rules

1. `sentiment_distribution.negative` ≠ specific event count — it is a broad negative sentiment aggregate
2. The same data point (rating, review count, positive_ratio, mention_count) for the same product MUST use identical numbers throughout the entire script — across ALL scenes from Category Rating Overview through Verdict
3. `evidence_quotes` must directly support the specific claim in the same block's narration. In cross-product blocks, each quote MUST be attributed to the correct `product_id` — misattributing a quote from Product A to Product B is a critical violation
4. `highlight_phrase` must be a verbatim, case-sensitive substring of the original review text (3–8 words target, 10 words hard ceiling) — exact match required for programmatic extraction
5. `root_cause` is LLM inference — express as speculation, not fact (hedging required: "likely", "appears to", "reviews suggest")
6. **Count-First Rule**: `positive_ratio` may be cited ONLY after the corresponding `mention_count` for that product × theme has been established in the same scene. Once established, the ratio may be used freely within that scene. Citing a ratio without prior count establishment is a critical violation — the viewer must have the sample-size context to judge statistical weight independently
7. Anti-Repetition: never reuse the same narrative entry pattern across blocks
8. **Story-Data Binding Rule (Absolute)**: A narrative sentence that does not bind to data within the same or adjacent block MUST NOT EXIST. Four binding types are valid:
   - **Direct binding**: The sentence contains or directly references a specific data point (count, percentage, rating, quote)
   - **Adjacent binding**: The sentence is immediately preceded or followed by a data-backed sentence in the same block
   - **Speculative binding**: The sentence uses hedged framing attributing the scenario to review data ("a scenario that 82 reviewers described", "the pattern reviews suggest")
   - **Cross-Product Comparative binding**: The sentence directly compares data points across two or more products, traceable to `common_themes[].rankings` in `category_analysis.json` (e.g., "Product A's 71% positive ratio in battery towers over Product B's 29%"). Both product identifiers and their respective data must be verifiable
   - **Violation**: Any narrative/story sentence floating without data binding in the same or adjacent sentence must be rewritten or removed. Hook Stage 1 (Category-Level Question) is exempt from direct binding but must connect to Stage 2's contradiction reveal.
   - **Cross-Product Violation (Methodological)**: Comparing values from different data fields across products — e.g., Product A's `all_time_rating_avg` vs Product B's `recent_review_rating_avg` — is a **Population Distinction violation** (§10 below). Same-field comparison only.
9. **Cross-Product Data Source Binding**: Every cross-product comparison MUST reference the source `product_id`. A comparison statement with a naked ratio (e.g., "one product scored 71%") that does not name the product is a critical violation. The authoritative data source for all cross-product claims is `category_analysis.json` (`common_themes[].rankings`)
10. **Contradiction Pair Completeness**: When narrating a `contradiction_pair` from `category_analysis.json`, BOTH the `positive_quote` and `negative_quote` MUST appear as `evidence_quotes` in the same or adjacent blocks. Presenting only one side of a contradiction violates the investigation frame — the viewer must see both data points to judge independently
11. **Product Identifier Consistency**: Once a product's `product_name` is established in the Category Rating Overview scene, that exact name MUST be used for the rest of the script. Switching between brand name, model number, and informal nicknames is forbidden
12. **Ranking Surface Ban**: `common_themes[].rankings[].rank` is an internal data order for the Structure Engineer's block placement logic. This rank number MUST NEVER surface in narration. Narration uses the underlying `positive_ratio` values, not ordinal positions (`brand_identity.md` §2 — Ban Vertical Rankings)

## §9 — Framing Pivot & Story-Data Integration Rules

> This section governs the framing and integration of story and data. All agents MUST comply accordingly.

### The Investigation Frame

Every video is a **consumer data investigation** into a product category. The Top 3–5 bestsellers are **case studies** within that investigation. The `video_question` (set by the Blueprint Designer) is the investigation's driving question — it must work without ANY product name, framing the entire category as the subject (`brand_identity.md` §3 Category-Level Question Test).

The channel's competitive edge is not "we review products" — it is **"we cross-examine product categories using thousands of verified buyer experiences to uncover patterns that no individual reviewer could find alone."** Every script, from Hook to Verdict, must reinforce this frame.

### 3 Defense Lines Against Drama Drift

These are testable rules, not guidelines:

1. **Data Trigger Rule (Strict Enforcement of §4.8)**: Every story sentence must originate directly from data evidence. A story sentence without a traceable data source in `summary.json`, `category_analysis.json`, or `evidence_quotes` is a critical violation of the §4 Story-Data Binding Rule. **Cross-Product claims** must trace to `common_themes[].rankings` or `contradiction_pairs` — fabricated relative performance claims are a critical violation.
2. **1st Person Observer Rule (Strict Enforcement of §2)**: The narrator is an analytical observer who represents user experiences strictly through evidence — never through emotional projection. Refer completely to the banned/allowed pattern table in `.agents/rules/prohibitions.md §2` Drama Pattern Prohibitions.
3. **Visual Fact Check Rule**: Even when narration uses story framing, the screen MUST display hard evidence (review quotes, data visualizations, buyer photos, cross-product comparison charts). The B-roll Agent enforces this — story-heavy narration blocks require evidence-category B-roll, not atmospheric footage. **In Theme Comparison scenes**: the B-roll layer should display comparative data visualizations (e.g., side-by-side `positive_ratio` bars) while the narrator delivers the story.

### LLM Inference in Story Sentences

Story sentences that describe scenarios not directly quoted from review text are **LLM inference**. They are permitted ONLY when:

- The scenario is **derivable** from actual `evidence_quotes` text (e.g., "battery died mid-cycle" → "coming home to a stopped machine" is derivable)
- The sentence uses **speculative/attributed framing** ("a scenario that 82 reviewers described", "the pattern reviews suggest")

Unattributed fictional scenarios ("Picture a tired parent coming home to find...") are prohibited per `.agents/rules/prohibitions.md §2` Drama Pattern Prohibitions.

**Cross-Product LLM Inference**: Causal explanations for WHY one product outperforms another in a specific theme (e.g., "Product C likely uses a newer chipset with lower power consumption") are LLM inference. They are permitted ONLY when:

- The hypothesis is listed in `contradiction_pairs[].resolution_hypothesis` in `category_analysis.json`
- The sentence uses hedged framing ("likely", "the data suggests", "one possible explanation")
- The hypothesis is plausible given the evidence quotes from BOTH products

Stating a cross-product causal claim as fact (e.g., "Product C's better chipset is the reason") is a critical violation.

### Story-Data Integration Examples

**Correct Hook Stage 1→2 transition (Category Comparison):**
> Stage 1: "You've bought the bestselling one. The one with the most reviews, the highest rating, the one your friend recommended. So why does it feel... wrong?"
> Stage 2: "I cross-examined 12,847 reviews across the Top 4 bestsellers. Last month's #1 seller — [Product A] — scored the lowest satisfaction in the very feature it advertises most. And the product that actually leads? A brand most of you have never heard of."

**Correct Theme Comparison with Contradiction Pair:**
> "Product A's noise cancellation earned a 71% positive ratio from 89 reviewers. Product C? 29% — from roughly the same sample size. Same category. But dig into the reviews, and the reason for the gap has nothing to do with hardware."

**Correct Verdict with Category Intelligence binding:**
> "12,847 reviews across 4 bestsellers. One pattern kept surfacing: every product in this category shares the same battery limitation — it's a structural constraint of the open-ear form factor, not a manufacturer defect. If 8-hour continuous use is non-negotiable, this category isn't ready for you yet."

**Violation — unbound cross-product comparison:**
> ❌ "Product A completely dominates Product C in sound quality." (No data binding — naked claim)
> ✅ "Product A's sound quality theme shows a 78% positive ratio versus Product C's 45% — a gap driven almost entirely by bass response complaints in Product C's reviews."

**Violation — Population Distinction error:**
> ❌ "Product A's rating dropped from 4.4 to 3.8, while Product C maintained 4.6." (Mixing `all_time_rating_avg` with `recent_review_rating_avg` — methodological error per §10 below)
> ✅ "Among 143 recent text reviewers of Product A, the average sits at 3.8. Product C's 98 recent reviewers average 4.6. Different reviewer pools, different sample sizes — but the gap is striking."

**Violation — one-sided contradiction:**
> ❌ "One reviewer called Product B's battery 'exceptional' — lasting a full 8-hour shift." (Only positive side of a within-product contradiction)
> ✅ "One 5-star reviewer says the battery lasts a full 8-hour shift. One 1-star reviewer of the same product says it's dead in 2 hours. The difference? A single firmware setting most users never find."

## §10 — Population Distinction Rules

> This is a **data interpretation principle** not encoded in software. Referenced by Writer, Data Validator, and Head Writer.
> Absorbed from the former `data_contracts.md` §3.

Amazon product pages display two star-rating metrics derived from **different populations**:

| Metric | Field | Population | Characteristic |
|:---|:---|:---|:---|
| **Headline Rating** | `all_time_rating_avg` | All buyers including those who only clicked a star rating | Skews positive (silent satisfied majority) |
| **Recent Review Rating** | `recent_review_rating_avg` | Only buyers who wrote a text review within the recent period | Skews negative (complaint-motivated population) |

**Rules:**

1. Directly comparing these two numbers as a "rating decline" is a **methodological error**
2. Every number MUST carry a population label: "12,247 total ratings" vs "143 recent reviews"
3. When comparing across products, place `population_gap` values side by side — the product with the largest gap has the most "hidden negativity"
4. Use `is_trending` (theme-level) to detect actual temporal changes
5. `last_month_sold` is a sales velocity indicator, NOT a quality metric — never conflate the two in narration
