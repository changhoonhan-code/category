---
trigger: manual
---

# Scene Structure, Visual Rhythm & Pacing Rules

## §5 — Visual & Sound Directing Rhythm

### The 3-Step Information Reveal (Mandatory Order)

Every data point must appear in this exact sequence:

1. **Context (2–3s)**: Establish the baseline on screen (e.g., "Category average is 5%")
2. **Reveal (1–2s)**: Product's actual data + `CountUpNumber` + Signature Sound Cue
3. **Hold (1–2s)**: Number stays visible — never rush past data. Let the contrast land.

> **Hook Exception**: The Hook scene uses its own sequence (Category-Level Question → Contradiction Reveal → Curiosity Loop) defined in §6. The 3-Step Information Reveal applies from the Category Rating Overview onward.

## §6 — Scene Structure (Category Comparison)

| # | Scene Type | Blocks | Purpose |
| - | ---------- | ------ | ------- |
| 1 | `hook` | 1–2 | **Contradiction/question-driven storytelling** — Opens with a core contradiction (Cross-Product or Within-Product) surfaced by the Contradiction Detector. Lead with story, not numbers |
| 2 | `category_rating_overview` | 2–3 | Multi-product rating comparison + Population Gap analysis. **SEO Rule: All product names MUST be spoken for the first time in this scene, ensuring every product name appears in the transcript within the first 60 seconds** |
| 3–N | `theme_comparison` | 2–3 per theme | Per-product strength/weakness differentiation within a shared theme + use-case highlighting. Based on `common_themes` from `category_analysis.json` |
| N+1 | `standout` | 1 per product | **Orthogonal Value Spotlight**. Rescues each product's unique killer strength that gets buried in shared-theme comparison tables. "It loses on common metrics, but thousands buy it just for this one feature." Based on `unique_strengths` from `category_analysis.json` |
| N+2 | `verdict` | 2–3 | Use-case recommendations (Buy If / Skip If) + Category Intelligence judgment + CTA |

### Hook Design (Contradiction-Driven, Mandatory)

The Hook is the primary mechanism for breaking out of the narrow niche. It must capture viewers who have NO interest in the specific products being compared.

| Stage | Duration | Content | Story:Data |
| ----- | -------- | ------- | ---------- |
| **Stage 1: Category-Level Question** | ~10–15s | A universally relatable question or scenario that spans the entire category. **ZERO product/brand references.** The viewer should not even know which product category this video covers at this point. Test: "Would someone with zero interest in this category still be curious?" | 90% : 10% |
| **Stage 2: Contradiction Reveal** | ~10–15s | Reveal a core contradiction extracted from `contradiction_pairs` in `category_analysis.json`. **Cross-Product contradictions take priority** (e.g., "Last month's #1 seller scored the lowest satisfaction in the very feature it advertises most."). Product names appear **only as clauses within data statements**. | 10% : 90% |
| **Stage 3: Curiosity Loop** | ~15–20s | Category framing + 2–3 theme teasers + Category Intelligence hint (e.g., "And surprisingly, every bestseller in this category shares the exact same fatal flaw."). Teasers must sound like "leads in an investigation," not "topics to cover." | 30% : 70% |

**Stage 1 Rules**:

- Must lead with a universally relatable experience, question, or observation
- Zero product name, brand name, or specific product category references
- The scenario must be derivable from the review data (not pure fiction) — but the data source is not revealed until Stage 2
- Block pacing: `breathe`

**Stage 2 Rules**:

- **Contradiction Source Priority**: Cross-Product contradiction > Within-Product contradiction > Expectation Gap (fallback)
- Product name(s) appear as clauses within a data statement: ✅ "Last month's #1 seller — [Product A] — scored lowest in the very feature it advertises most." ❌ "Today we're comparing [Product A], [Product B], and [Product C]."
- Creates an Expectation Gap that makes the viewer want to understand the pattern
- Block pacing: `breathe`

**Stage 3 Rules**:

- Category Intelligence hint: May tease a Universal Weakness or Maturity Assessment in a single line (full analysis unfolds in Verdict)
- Teasers should sound like "leads in an investigation" not "topics to cover"
- Block pacing: `dense`

**Block Options**: The Structure Engineer may use either:

- **1-block Hook**: All three stages compressed into a single block (rare — only for very short contradictions)
- **2-block Hook**: `hook_contradiction` (Stage 1 + Stage 2 combined) + `hook_curiosity_loop` (Stage 3)

Choose based on whether the contradiction needs room to breathe. 2-block is the default.

**Product name rules**: MUST NOT appear in Stage 1. First appears in Stage 2 as a clause within the data statement.

### Category Rating Overview Design

| Block | Role | Pacing |
|-------|------|--------|
| `rating_overview_lineup` | Full product lineup introduction + bestseller rank context (last month's sales). **All product names MUST appear in the transcript in this block** (SEO: all product names within first 60 seconds) | `standard` |
| `rating_overview_gap` | all_time_rating vs recent_review_rating comparison → Population Gap analysis. Highlight the product with the largest gap | `standard`–`dense` |

**Design Rules**:

1. Bestseller rank (BSR) MUST be explicitly labeled as **"based on last month's sales volume."** Never conflate with "all-time cumulative" or "quality ranking."
2. Apply Population Distinction rules (`evidence_integrity.md` §10) — directly comparing Headline Rating vs Recent Review Rating and framing it as a "rating drop" is a methodological error.
3. If any product has `trap_candidate.is_trap === true`, hint at the "trap signal" in this scene, but reserve the full exposé for Theme Comparison or Verdict.

### Theme Comparison Design

Each Theme Comparison scene covers ONE shared theme across ALL products.

| Block Pattern | Role | Pacing |
|---------------|------|--------|
| `{theme}_leader` | Strengths + evidence quotes from the product with the highest positive_ratio in this theme | `standard` |
| `{theme}_laggard` | Weaknesses + evidence quotes from the product with the lowest positive_ratio in this theme | `standard` |
| `{theme}_context` (optional) | Mid-ranked product summary or category_pattern commentary (e.g., universal_weakness). Omit if 2 blocks are sufficient | `dense` |

**Design Rules**:

1. **Horizontal differentiation only**: The goal is NOT to crown a "winner" or "loser" per theme, but to explain **why this product suits a certain user type while another does not** — use-case-driven narrative differentiation.
2. Themes with `category_pattern_type === "universal_weakness"` receive special treatment: Prioritize **"structural limitation of the entire category"** framing over individual product comparison → foreshadowing for the Category Intelligence conclusion.
3. If a Contradiction Pair exists for a theme, the contradiction MUST be developed within the block. Specify `contradiction_pairs` data in the `notes` for the Writer.
4. **Ranking ban (`brand_identity.md` §2)**: Narration MUST NEVER use vertical ranking language ("1st / 2nd / last place"). positive_ratio-based data rankings are used ONLY in the Structure Engineer's internal block placement logic and MUST NEVER surface in the script.

### Standout Design

| Block | Role | Pacing |
|-------|------|--------|
| `standout_{product_id}` | The product's unique killer strength + recommended use case / user profile | `breathe`–`standard` |

**Design Rules**:

1. **Mandatory placement**: Every product with an entry in the `unique_strengths` array of `category_analysis.json` MUST receive a Standout block.
2. A product that underperformed in shared-theme comparisons CAN be rescued here. "It loses on common metrics, but thousands buy it just for this one feature."
3. Standout blocks are placed AFTER all Theme Comparison scenes and BEFORE the Verdict.
4. Products without `unique_strengths` entries proceed without a Standout block. (Their strengths are already sufficiently covered in shared themes.)

### Verdict Design (Category Comparison)

| Block | Role | Pacing |
|-------|------|--------|
| `verdict_category_judgment` | Category Intelligence conclusion: category maturity assessment + buy/avoid rationale. "Is this category even worth buying into?" | `standard` |
| `verdict_use_case_picks` | Use-case-based product recommendations (vertical ranking ❌ → horizontal differentiation ✅). "If battery life is your priority → Product C", "If app customization matters most → Product A" | `standard` |
| `verdict_outro` | Closing line + Channel CTA | `breathe` |

**Design Rules**:

1. `verdict_category_judgment` MUST directly reference `category_intelligence` data from `category_analysis.json` (maturity_assessment, universal_weaknesses, buy_in_category/avoid_category).
2. **Scorecard as B-roll**: During `verdict_category_judgment`, the B-roll layer MUST display an all-themes × all-products matrix infographic. The viewer sees the visual summary while the narrator delivers the category-level conclusion. Include matrix chart generation instructions for the B-roll Agent in `notes`.
3. `verdict_use_case_picks` MUST NEVER declare a single "best product." Only use-case-differentiated recommendations are allowed (`brand_identity.md` §2).
4. If any product has `trap_candidate.is_trap === true`, include an explicit warning in `verdict_use_case_picks`.
5. Block count: 2–3. The Structure Engineer determines based on the complexity of the category judgment.

## §7 — Runtime Budget (Dynamic Caps)

### Dynamic Block Caps

| Product Count | Max Theme Comparison Scenes | Max Total Blocks (incl. Standout) |
|:---:|:---:|:---:|
| 3 | 5 | 22 |
| 4 | 4 | 24 |
| 5 | 4 | 27 |

- **Teaser → Payoff**: must resolve within 3 scenes
- **Reference allocation**: Hook 1–2 / Category Rating Overview 2–3 / Theme Comparison avg 2–3 per theme / Standout 1 per product / Verdict 2–3

### Pacing Profiles

Each block receives a `pacing_profile` from the Structure Engineer that determines its word count budget and screen time character.

| Profile | Word Count (Writer) | Max After Edit (Tone/DV) | Screen Time | Story Density Max | When to Assign |
| ------- | ------------------- | ------------------------ | ----------- | ----------------- | -------------- |
| `breathe` | 40–55 words | 60 words | ~20–25 sec | 60% | Hook Stage 1 & 2, Standout blocks, single-quote evidence blocks, emotional hold moments, Verdict Outro |
| `standard` | 65–80 words | 85 words | ~30 sec | 30% | Category Rating Overview lineup, most Theme Comparison blocks (leader/laggard), Verdict category judgment & use-case picks |
| `dense` | 75–85 words | 90 words | ~35 sec | 10% | Category Rating Overview gap analysis, Theme Comparison context blocks, Curiosity Loop |

- "Max After Edit" applies to agents that rewrite narration (Tone Editor, Data Validator, Head Writer) — a 5-word buffer over Writer targets.
- **Distribution rule (percentage-based)**:
  - `breathe`: **15–25%** of total blocks. Consecutive `dense` blocks are forbidden — always interleave with `standard` or `breathe`.
  - `standard`: **55–70%** of total blocks.
  - `dense`: **10–15%** of total blocks. Consecutive `dense` blocks PROHIBITED.
  - Round to nearest integer. Verify after rounding that sum equals total block count.
  - **Reference table** (pre-calculated for common block counts):

  | Total Blocks | breathe | standard | dense |
  |:---:|:---:|:---:|:---:|
  | 20 | 3–5 | 11–14 | 2–3 |
  | 22 | 3–5 | 12–15 | 2–3 |
  | 24 | 4–6 | 13–17 | 2–4 |
  | 27 | 4–7 | 15–19 | 3–4 |

- If `pacing_profile` is absent (legacy script), treat as `standard`.

### Story Density by Video Section

Story density varies by section to achieve the "bookend concentration" strategy. The Tone Editor enforces these limits.

| Section | Story : Data | Purpose |
| ------- | ------------ | ------- |
| **Hook** (first ~45s) | 80% : 20% | Entry barrier destruction — category-level question + contradiction pulls in non-niche viewers |
| **Core** (Rating Overview + Theme Comparisons + Standout) | 20% : 80% | Authority maintenance — data-first comparative analysis preserves credibility |
| **Verdict** (last ~60s) | 60% : 40% | Emotional landing + share trigger — synthesizes investigation into use-case recommendations |

> A "story sentence" is one that describes a scenario, experience, or emotional state rather than citing/interpreting data. The Tone Editor classifies each sentence for density verification.

## §8 — B-roll Priority (Strict Fallback Order)

1. **Showrunner Selection** (`block_visual_mapping.json`) — Contextual theme-filtered choice
2. Existing video (`products/{product_id}/movies/`) — keyword/LLM match fallback
3. Photo montage (`products/{product_id}/photos/`) — Ken Burns effect inside card frame
4. AI-generated (`gen_media.py`) — only when no suitable existing assets match

> **Cross-Product Visual Rule**: In Theme Comparison scenes, **interleave** assets from the compared products to maximize visual contrast. No single product's video/photo should run for more than 5 consecutive seconds.
