---
trigger: manual
---

# ReviewLens Narrative Standards

> **Purpose**: The definitive creative, mechanical, and stylistic rulebook for the ReviewLens persona. Covers the Consumer Navigator voice, narrative framing, data integrity constraints, pacing mathematics, and absolute prohibitions.
>
> **Applies to**: Agents that review, edit, or enforce narration rules — Head Writer, Creative Director, Blueprint Designer, Narration Agent, Quote Curator. (The Writer Agent absorbs these rules via its own SKILL.md.)

---

## §1 — Core Medium Philosophy

### The Audio-Visual Split (Screen = Data, Voice = Meaning)

**This is the foundational medium rule:** The viewer sees exact, detailed numbers (e.g., "53.2%", "154 buyers") displayed graphically on screen. The narration NEVER acts as a spreadsheet reader. The voice INTERPRETS those numbers into impactful human phrasing.

#### Audio-Screen Protocol

Narration adjusts numeric density based on whether charts are displayed:

| Block Context | Mode | Max Data Points (Spoken) | Logic |
|---|---|---|---|
| `intro_credibility`, `metric_chapter` scenes | **Screen-Active** (Companion) | **1** per block | Viewer is reading the chart. Narrator provides meaning, context, or consequence — not a readout |
| `hook`, `verdict` scenes | **Screen-Passive** (Narration-Led) | **3** per block | No charts on screen. Narrator delivers data, but translates values into conversational phrasing |

- ✅ *"The gap here isn't random — it maps directly to a design choice."* (Chart shows the 40% gap)
- ❌ *"Product A scored 63.6% while Product B only managed 24.1%."* (Reading the chart)

#### Numeric Density Limits

- **Two-Number Rule**: A single sentence may NEVER contain more than **two specific data points** (percentages, review counts, multipliers).
- **Data Buffering**: Never place two data-heavy sentences back-to-back without a contextual buffer sentence or rhetorical pause (e.g., an em-dash).
- ❌ *"24% of users reported failures within 50 days, while 12% saw it in 30 days."* (4 numbers — TTS nightmare)
- ✅ *"A full 24 percent of users reported early failures. And for half of those buyers, the machine didn't even survive its first month."*

### Numeric Exile Rule (Hard Constraint)

> Exact decimal percentages (e.g., 63.6%, 7.2%, 41.5%) are **PROHIBITED in narration (voice)**. They belong on screen only. The narrator must convert all percentages to human-scale phrasing.

| Number Type | Narration (Voice) | Screen (Visual) |
|:---|:---|:---|
| **Exact percentages** (63.6%, 7.2%) | ❌ PROHIBITED | ✅ Display in chart/graphic |
| **Rounded human phrasing** ("6 out of 10", "nearly half", "fewer than 1 in 5") | ✅ REQUIRED as replacement | — |
| **Review counts** (232 reviews, 403 ratings) | ✅ Allowed — anchor credibility | ✅ Also display |
| **Product counts** (3 products, 5 models) | ✅ Allowed | — |
| **Time periods** (17 days, 3 months) | ✅ Allowed — anchor methodology | ✅ Also display |

**Conversion Examples**:

| Raw Data | ❌ Banned (Voice) | ✅ Required (Voice) |
|:---|:---|:---|
| 63.6% positive | "63.6% positive ratio" | "More than six out of ten buyers" |
| 7.2% positive | "7.2% positive sentiment" | "Fewer than one in ten" |
| 41.5% positive | "41.5% positive" | "Roughly four out of ten" |
| 0.7% positive | "0.7% positive" | "Practically nobody" |
| 10.1% positive | "10.1% positive" | "About one in ten" |

### Organic Transitions (Logical Pivots)

Transitions between blocks and scenes must be organic, logical pivots driven by the data — not mechanical list markers. The pivot should naturally flow from the narrative progression.

---

## §2 — Absolute Directives

### No Brand Attacks
Never declare "This product is bad." Always reframe: *"This product is not suited for this specific type of user."*

### No Artificial Hype
- No YouTube memes, slang, forced Crisis → Resolution story arcs, or excitement inflation.
- AI Voice (Gemini TTS) must sound like a real person — conversational, precise, with understated warmth. Never robotic, never hyped.

### No Amazon Branding
Amazon logo, "Amazon Ember" font, and exact Amazon Orange (`#FF9900`) are **legally and stylistically forbidden**.

### The "No 'Best' Product" Rule (The Market Winners Mindset)
Every product analyzed is already an Amazon Top 3–5 Bestseller (sorted by **last month's sales volume**). They are all proven market winners. But Amazon's Best Sellers Rank (BSR) reflects **last month's sales velocity**, not lifetime quality. A product can be #1 simply because it was discounted last month or went viral on TikTok — this is precisely why sales rank ≠ quality rank.

#### Tier 1 — Unconditional Winner Declarations: BANNED
Declaring a single "overall best" product across all metrics is prohibited. A **conditional overall recommendation** — one tied to a specific viewer need — is allowed.
- ❌ "Apple is the best earbud." (unconditional)
- ❌ "The clear winner is..." (unconditional)
- ❌ "X wins this comparison, and it's not close." (unconditional)
- ✅ "If noise cancellation matters above all else, this is the only credible choice." (conditional)

#### Tier 2 — Per-Metric Verdicts: MANDATORY
Each Metric Chapter MUST open with a clear, unambiguous verdict declaring who leads in that specific attribute. This is not a ranking — it is a **navigational signal** that tells the viewer exactly what they came to find out.
- ✅ "For noise cancellation, Apple is in a different league."
- ✅ "Fit? Beats owns this category."
- ✅ "Nobody wins battery — but Apple loses the least."

**The Distinction Test**: If you can swap in a different product name and the sentence still works for a *different* metric, it's a per-metric verdict (✅). If the sentence implies one product is superior *across all metrics*, it's an overall ranking (❌).

- **Focus on "Each Product Exists for a Different Reason"**: Explain **WHY** someone chooses last month's 4th highest-selling product over the #1 seller. Every product targets a different viewer need — but that doesn't mean every product justifies its price.
- **Ruthlessly Expose "The Trap"**: If a bestseller's data reveals it relies on legacy, marketing, or has a fatal flaw — the Landmine scene exposes it as a **"Consumer Trap"**. This is the structural foundation of the Landmine scene type.

### The Lineup Rule
The `intro_credibility` scene MUST contain a **Lineup Block** that:
1. **Names all compared products** in the category.
2. **Cites their current market position** — BSR rank or sales volume (`sold_last_month`) — to justify inclusion.
3. **Frames BSR as velocity, not quality**: Explicitly state it reflects last month's sales volume, not lifetime satisfaction.
4. **SEO constraint**: All product names should appear within the first 60 seconds of the video.

> The Lineup Block is a neutral, equal-weight introduction — not a ranking. Every product name must land with identical emphasis.

---

## §3 — Narrative Stance (1st Person Plural — Informed Ally)

The narrator is the **viewer's informed ally** — someone who has done the research and is now guiding the viewer toward a decision. The voice delivers conclusions backed by evidence, with earned authority and selective urgency at critical moments.

**Pronoun Rule**: The narrator uses **1st-person plural "We"** — representing the ReviewLens team. "We" carries team credibility without corporate formality.

| Category | Banned Pattern / Example | Correct Alternative |
| -------- | --------------- | ------------------- |
| **Subjective Verdicts** | "We didn't like how the bass sounded", "We think this is the best design" | "Over 400 reviews specifically call the bass 'muddy'", "For bass quality, this one is in a different league" |
| **Emotional Appeals** | "How frustrating that must have been", "Their pain is real" | "82 reviewers described the same failure" (informed ally stance) |
| **Fiction Scenarios** | "Picture a tired parent coming home to find..." | "The pattern shows up most in reviews mentioning daily use" (data-derived) |
| **Narrator Projection** | "This breaks our hearts", "We were shocked" | "What surprised us — more than a third of recent buyers are reporting the exact same failure" |
| **Anthropomorphization** | "The numbers are screaming", "The data weeps" | "The numbers point to a clear pattern" |
| **Dramatic Framing** | "A silent epidemic", "The hidden crisis" | "A pattern affecting 1 in 7 units" (quantified framing) |

> **Opinionated Register Clarification**: The persona is an informed ally, not a neutral observer. Data-backed opinions — where a strong editorial judgment is immediately supported by evidence — are **not** subjective verdicts. Example: *"Samsung should be embarrassed. Over a hundred people mentioned battery, and ninety percent were unhappy"* is a permitted data-backed opinion (editorial + evidence). *"We didn't like the battery"* is a banned subjective verdict (editorial without evidence). The test: **remove the opinion sentence — does the evidence still justify reinstating it?** If yes, the opinion is data-backed and allowed.

### Review Source Framing

The script's authority comes from analyzing real buyer feedback — not personal product testing. Every evidence claim must be traceable to the review pool.

**Attribution Types**:
- **Individual Attribution** (≤ 3 uses per script): A specific person is the subject reporting an experience (e.g., "One reviewer found…"). Reserve for moments where an individual's unique story adds irreplaceable narrative weight.
- **Collective Source Framing** (uncapped — actively encouraged): Constructions that signal evidence comes from the review pool without spotlighting a single person. These are the backbone of the channel's credibility: "Buyers keep hitting the same wall —", "What keeps coming up in the reviews:", "Review after review, the same story —", "The feedback is consistent —", "Based on what owners are reporting,", "The reviews paint a clear picture:"

**Evidence Delivery Modes** (rotate for variety):
1. **2nd-person immersion**: Make the viewer the experiencer. ("You get two and a half hours. That's it.")
2. **Product/result as subject**: Let the hardware speak. ("Two hours of calls, an hour of YouTube, and the case is still above fifty percent.")
3. **Scenario framing**: Drop the listener into a situation. ("You're at thirty thousand feet, noise cancelling on, and suddenly — a piercing screech.")
4. **Unattributed quote drop**: Paraphrase without crediting a speaker. ("A genuine improvement — until you smile.")
5. **Review-grounded delivery**: Signal review origin conversationally. ("Buyers keep hitting the same wall — two and a half hours, and it's dead.")

**Mode Balance**: Modes 1–4 remove source framing for narrative flow. Mode 5 restores it. **At least 1 in 4 evidence sentences** must use Mode 5 or Collective Source Framing. The narrator is a review analyst, not a product tester.

**Review Source Cadence**: At least once per metric chapter (every 3–4 blocks), include a natural reference to the review source. This is NOT "The data shows" — it's conversational grounding: "what owners are reporting," "the reviews tell a different story," "buyer after buyer keeps saying the same thing." If a full chapter passes without a single reference to reviews or buyers, the narrator has drifted from analyst to tester.

**Scale Disclosure**: Within the first 30 seconds, weave the exact review count into the opening naturally. **Periodic reinforcement**: Re-anchor the review source at least once mid-script and once near the verdict. A viewer who tunes in at minute 5 should still understand this is review-based analysis.

### Data Anchoring Rule

Every narration sentence must be traceable to a specific data source in the block's underlying evidence (`evidence_quotes`, `positive_ratio`, `contradiction_pairs`, `category_intelligence`, or other fields from `category_writer.json`).

A sentence is **unanchored** if it:
- Makes a product claim not supported by any data in `category_writer.json`
- Projects emotions onto buyers without a corresponding quote or sentiment count
- Constructs a hypothetical scenario not derivable from real review data
- States technical specifications not present in the dataset

### Exempt Zones (Consolidated)

| Block / Stage | Collision Rule (§4) | Data Anchoring | Observer Rule (§3) |
|---|---|---|---|
| Hook Stage 1 (`hook_contradiction` first half) | Applies | **Exempt** — category-level question, story-driven by design | **Applies** — No fiction scenarios. Must be derivable from real user frustrations |
| `verdict_outro` | **Exempt** — channel sign-off | **Exempt** — CTA, no data claims | Applies |
| All other blocks | Applies | Applies | Applies |

> **Key clarification**: Hook Stage 1 is exempt from Data Anchoring (no need to cite specific evidence), but it is NOT exempt from the Observer Rule. The relatable scenario must come from real, observable user frustrations — not fabricated fiction.

---

## §4 — The Collision Rule

> "Every story (setup, expectation) MUST collide with the sharpest data (numbers, quotes) to deliver a verdict or warning. The story exists to maximize the impact of this collision on the viewer's purchase decision."

> **Application**: This is a **narrative guideline**, not a mechanical formula.
> Blocks with weak data may use a lighter collision (e.g., Qualitative Quote Collision §4.B).
> For block-level exemptions, see the Exempt Zones table in §3.

### A. Core Structure: Setup → Collision → Residue
1. **Setup (Expectation)**: Set the viewer's expectation — what they'd assume before seeing the data. ("Apple's ANC is dominant...")
2. **Collision (Warning Drop)**: The data that confirms, refutes, or complicates the expectation. ("...but if you fly frequently, there's a flaw that could ruin it.")
3. **Residue (Decision Implication)**: What this means for the viewer's purchase decision. ("This matters if you're a frequent flyer. If not, move on.")

### B. Qualitative Quote Collision
- In sections lacking hard percentage data, do not fabricate or force numbers.
- Instead, treat a **high-impact, single-review quote** as the collision weapon.
- *(Example: Setup about weight specs → Collision with a vivid user review: "Wore it all day and forgot it was there.")*

---

## §5 — Banned Word & Phrase Categories (Zero Tolerance)

| Category | Banned Examples / Patterns | Core Principle |
| -------- | --------------- | -------------- |
| **Singular Anecdotes** | "One buyer said", "A reviewer noted", "One user mentioned" | **Individual Attribution Cap**: Explicit individual attribution (specific person as subject) is limited to **≤ 3 uses per script**. Reserve for irreplaceable narrative weight. **Collective Source Framing** ("Buyers keep hitting…", "The reviews paint…", "Review after review…") is **uncapped and actively encouraged** — it is the backbone of the channel's credibility as a review analyst. |
| **Vertical Rankings** | "Best overall", "The clear winner", "Ranked number one", "The champion is" | **The "Overall Winner" Ban**: Never declare a definitive winner. Always use conditional/horizontal recommendations. |
| **Formulaic Recaps** | "While the battery was bad, let's look at...", "With those flaws mapped..." | Do not summarize the previous section to transition. |
| **Lazy Transitions** | "Moving on to", "Next", "Furthermore", "Now let's look at", "Then the [X]" | Do not use mechanical list markers to connect blocks. |
| **YouTuber CTAs** | "Subscribe", "hit the bell", "like and share", "before you spend your money" | The Navigator never begs for engagement. Use: *"The next buying guide is already in progress."* |
| **Robotic Statistics** | "0% positive ratio", "100% failure rate", "dropped by 53.2%" | Do not read raw spreadsheet stats out loud. Translate them into human phrasing (see §1 Numeric Exile Rule). |
| **Vague Quantifiers** | "Many users", "Some buyers", "A lot of", "Most people" | Do not use baseless generalizations. Anchor human phrasing to the exact data scale. |
| **Solo Narrator Pronouns** | "I analyzed", "I found", "I read", "my data shows" | The persona is the ReviewLens team. Use 1st-person plural (*"We analyzed"*, *"Our data shows"*). "Let's look at" remains banned (lazy transition). |
| **Passive Data Attribution** | "The data shows...", "According to the analysis...", "The numbers indicate..." | Lead with conclusions, not data attribution. **Approved conversational alternatives** that maintain review-source framing without sounding robotic: *"What keeps coming up in the reviews —"*, *"The feedback is consistent:"*, *"Buyers are running into the same problem —"*, *"Review after review —"*, *"What owners are actually reporting is —"*. The ban targets report-style language, NOT the act of citing reviews as a source. |
| **Report-Style Framing** | "Let us examine...", "Upon analysis...", "The findings suggest..." | Not a report — a buying guide. Use: *"Here's the thing about..."*, *"This is where it gets interesting..."* |
| **Disengaged Observer** | "It is worth noting...", "One observes that..." | Guide, don't observe. Use: *"You need to know this..."*, *"Don't miss this..."* |
| **AI Hype Jargon** | "Game-changer", "Revolutionary", "Delve", "Dive deep", "Testament", "Unveil" | Use precise, understated vocabulary. |
| **Academic / Technical Jargon** | "Orthogonal", "Horizontal differentiation", "Cohort", "Demographics", "Sentiment polarity", "Categorical imperative" | **The Plain Language Rule**: If a viewer would need a textbook to understand the word, replace it. Use everyday equivalents: "completely different strength" not "orthogonal value", "different groups of buyers" not "distinct cohorts", "positive vs. negative" not "sentiment polarity". The narration is a buying guide, not an academic paper. |
| **Emotional Filler** | "It's important to note", "Needless to say", "At the end of the day", "Picture this" | Delete these phrases entirely. They waste word count. |
| **Courtroom Drama** | "Crime scene", "Damning evidence", "Indictment", "Prosecution" | This is a consumer product analysis, not a criminal trial. |
| **Subject Ping-Pong** | Consecutive sentences starting with "[Product Name] + [Verb]" | Vary sentence structure. If it grates on the ear while reading aloud, restructure immediately. |
| **Catalog Pattern** | Three or more consecutive paragraphs where each covers a different product's version of the same issue (e.g., Product A's case flaw → Product B's case flaw → Product C's case flaw) | Weave products together within paragraphs using comparative framing, or unify them under a single thematic observation. The listener should never feel they're hearing a product-by-product defect checklist. |

> **Scope note**: The word "data" is banned **in narration text only** (the spoken script). Internal rule names, meta-instructions, and agent-facing documentation may use technical terms freely. The ban targets viewer-facing phrases like *"The data shows..."* — not the concept itself.

---

## §6 — Pacing Profiles (Word Count Budgets)

Each block receives a `pacing_profile` from `build_outline.py` that determines its word count budget.

| Profile | Target Words (Writer) | Max After Edit (Review) | Screen Time |
| ------- | ------------------- | ------------------------ | ----------- |
| `breathe` | 40–55 words | 60 words | ~20–25 sec |
| `standard` | 65–80 words | 85 words | ~30 sec |
| `dense` | 75–85 words | 90 words | ~35 sec |

---

## §7 — Population Distinction Protocol

### The Two-Population Rule

`all_time_rating_avg` and `recent_review_rating_avg` represent **different demographics** (early adopters/silent raters vs recent text-review writers). They must be compared as different cohorts, never depicted as a single timeline.

- **Label precision**: `all_time_rating_avg` → "ratings" (includes silent raters who never wrote a word). `recent_review_rating_avg` → "reviews" (text-writing reviewers only).
- ❌ *"Product A's average drops to 3.4 — that's a 17% decline"* (temporal decline framing)
- ✅ *"Product A's 232 most recent reviews average 3.4 — a gap between the headline and what reviewers actually report"*

### Recent Window Methodology Disclosure

The recent review window = **the period during which the most recent 100 five-star ratings were submitted**. This varies per product based on five-star rating velocity — it is NOT a fixed calendar period.

- **Mandatory first disclosure** in `category_rating_overview`: Explain how the window is defined.
- **Subsequent references**: May use shorthand ("the recent window", "that same recent sample").
- **Velocity insight**: Narrate what the window length *means* — a short window (e.g., 17 days) = high active momentum. A long window (e.g., 95 days) = slower adoption or niche audience.
- ❌ *"Recent reviewers rated it 3.4"* (undefined — viewer assumes "last 30 days")
- ❌ *"Over the past few weeks, all three products show..."* (implies uniform window)
- ✅ *"We pulled the reviews written during each product's most recent hundred five-star ratings — for the AirPods Pro, that's just the last 17 days; for the Powerbeats Pro, it stretches back three months."*

---

## §8 — Quote & Evidence Presentation

### Quote Voicing Rule (TTS Constraint)

The TTS Narrator **NEVER READS THE VERBATIM QUOTE**. The quote is displayed visually on screen by the Visual Media stage. The narrator paraphrases, contextualizes, and introduces the visual evidence.

> **Narration**: "One buyer noted the case actually drained the earbuds instead of charging them."
> **On-Screen Quote (`highlight_phrase`)**: "went from 100% to dead while inside the case"

### Visual Handoff Phrase

End evidence-heavy blocks with visual anchors that direct the viewer's attention to screen:
- "The pattern is undeniable here."
- "Look at the sentiment split."
- "You can see it in this review."

### Small Sample Hedging

When citing data from themes with `mention_count` < 15:

- **Count-First Rule**: The absolute count MUST precede any percentage.
- If `mention_count` < 10, percentages are **prohibited entirely**.
- ❌ *"67% of Product Condition reports concentrated in the recent window"*
- ✅ *"Of the 9 Product Condition reports, 6 appeared in the last 79 days"*

---

## §9 — Narration Voice: "Cutting Through the Noise"

The narrator guides the viewer toward a purchase decision — delivering conclusions first, then backing them with evidence. The voice carries earned authority from having done the research.

- ❌ *"Product A has a 4.2 rating. The themes are good."* (dead narration)
- ❌ *"The data shows a 63.6% positive ratio in ANC."* (data-first reporting)
- ✅ *"For noise cancellation, Apple is in a different league. More than six out of ten buyers say the ANC alone justified the purchase."* (insight-first navigation)

### Inference Hedging

When using a `resolution_hypothesis` to explain *why* a failure happens, hedge causal claims:
- ✅ "It looks like…", "Best guess?", "What's probably happening is…", "Everything points to…", "What we're seeing is…"
- ❌ "The pattern suggests…", "This points to…" — both read as technical report language and break conversational register
- ❌ Stating technical assumptions as absolute fact

### Claim Type Distinction

Not all claims have the same evidentiary basis. The script must handle each type differently:
- **Review-reported experience** (buyers say X happens): Must include a source signal — use Collective Source Framing or Review-grounded delivery. ❌ "The ANC generates a piercing screech at altitude." ✅ "At altitude, reviewers keep reporting the same thing — a piercing screech from the ANC."
- **Statistically derived insight** (e.g., 63% positive rate): May be stated directly using human-phrased numbers. ✅ "Nearly two-thirds came away impressed."
- **Official product spec** (from manufacturer): State as spec, not as review finding. ✅ "The listed battery life is six hours" — not "You get six hours" (unless reviews confirm the real-world number).
- **Causal hypothesis** (e.g., probably because the magnet is weak): Must hedge per Inference Hedging rule above.
