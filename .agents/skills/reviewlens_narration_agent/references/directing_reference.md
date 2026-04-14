# Directing Reference — Technical Constraints & Structural Mappings

> **Authority**: This reference complies with the
> [Google TTS Prompting Guide](https://ai.google.dev/gemini-api/docs/speech-generation#prompting-guide).
>
> **Principle**: "Define only what's important to the performance, being
> careful to not overspecify. Too many strict rules will limit the models'
> creativity and may result in a worse performance." -- Google TTS Prompting Guide

For rules, prompt format, anti-patterns, and agent scope -> `SKILL.md`.

---

## Director's Notes — The Sole Directing Layer

> **The goal is NOT a perfect announcer. The goal is a real human being talking.**
> Natural rhythm, genuine reactions, conversational breath — a person who found
> something in the data and is telling you about it. Not a teleprompter reader.
> Not a news anchor. A real person with something important to say.

The Narration Agent's output: DIRECTOR'S NOTES (rich natural language directing) + TRANSCRIPT (clean narration text, zero markup).

| Layer | Role | Responsibility |
| --- | --- | --- |
| **Director's Notes** | ALL delivery direction | **Sentence-level, word-level natural language directing.** The agent writes like a film director in a recording booth, briefing the voice actor before each take. The goal is human naturalness — a real person talking, not a polished broadcast. Every pacing decision, every pause, every breath, every speed change — expressed as vivid, concrete prose. |
| **TRANSCRIPT** | Clean narration text | Spoken words exactly as they should appear. Zero brackets. Zero tags. Zero markup. |

### What Great Director's Notes Sound Like

The agent directs toward **human naturalness**, not announcer perfection.
Think: a colleague who just spent hours in the data, leaning across a desk at midnight, saying "look at this." They speed up through the boring parts because they want to get to the point. They slow down on a number because it genuinely surprised them. They pause — not because a script told them to, but because they're choosing their next words.

**The kind of directing expected:**
- "The rating enumeration is scaffolding — move through it the way you'd rattle off a phone number to someone. Fast, functional, you don't care about these numbers. Then STOP. The silence before the next number is where you shift — because this one actually matters."
- "On 'sixty-two percent', slow down the way you would if you were reading bad news off a medical chart. Not dramatic — just... careful. Like each digit costs something. Let it hang in the air."
- "The emotional state is quiet sobriety — this person just found something that surprised them. Lower volume, like sharing bad news with a friend over coffee at 2AM. Not performing sadness. Just... tired honesty."
- "Open with the confidence of someone who already knows the ending. Two short sentences, flat certainty — the way you'd say 'the sky is blue' to someone who asked. No warmth, no cold. Just obvious."
- "The word 'without' is doing all the work. Slight lift — like you're raising one eyebrow. Everything around it stays flat. The contrast lives in that one preposition."
- "After this line, hold silence. Not a dramatic pause — just the natural gap where the viewer reads the quote on screen. Two seconds of nothing. Don't fill it."

---

## 1. Clean TRANSCRIPT Rule

TRANSCRIPT contains narration text ONLY. Zero brackets. Zero tags. Zero markup.

ALL delivery direction — pacing, pauses, speed changes, breath, emphasis, designed silence — lives exclusively in DIRECTOR'S NOTES as natural language prose.

### Prohibited in TRANSCRIPT

| Type | Examples | Why |
| --- | --- | --- |
| Bracket tags (any) | `[short pause]`, `[speaking slowly]`, `[sigh]` | All pacing/breath direction belongs in Director's Notes as prose |
| Style/emotion tags | `[whispering]`, `[empathetic]`, `[curious]` | Express as descriptive prose in Director's Notes |
| Invented timing tags | `[PAUSE=2s]`, `[Full stop]`, `[Micro-pause]` | TTS will vocalize these |
| SSML markup | `<break>`, `<prosody>`, `<emphasis>` | Gemini TTS ignores or errors on SSML |
| Descriptions in brackets | `[Drop pitch, weight every digit]` | TTS reads bracket content aloud |
| Archetype codes | `[Archetype C]`, `[Sustained Gravity]` | Archetype declaration belongs in Director's Notes |

> **All direction belongs in Director's Notes as descriptive prose.**
> TRANSCRIPT is the clean script on the page — nothing more.

---

## 2. Numerical Evidence -- Spelled-Out Rule

ALL numbers in TRANSCRIPT must be written as spoken English text.
The TTS model frequently misfires on digit-form numbers.

### Conversion Table

| Number Type | Digit Form (BANNED) | Spoken Form (REQUIRED) |
| --- | --- | --- |
| Integers < 100 | `79` | `seventy-nine` |
| Integers 100-999 | `598` | `five hundred ninety-eight` |
| Integers 1,000+ | `1,759` | `seventeen fifty-nine` |
| Decimals | `4.2` | `four point two` |
| Percentages | `63.6%` | `sixty-three point six percent` |
| Ranges | `3-to-4 hours` | `three-to-four hours` |
| Ordinals | `1st`, `2nd` | `first`, `second` |
| Compound modifiers | `0.5-point gap` | `half-point gap` (see below) |

> For large integers (1,000+), prefer conversational short form
> (`seventeen fifty-nine`) over formal long form unless formal reads better in context.

### Compound Modifier Collision Rule

When a decimal number appears as part of a hyphenated compound modifier containing
the word "point" (e.g., `X.X-point gap`), mechanical conversion creates a
"point" collision: `0.5-point gap` → `zero point five-point gap` (3x "point").

**Convert using natural spoken English instead:**

| Digit Form | Spoken Form | Why |
| --- | --- | --- |
| `0.5-point gap` | `half-point gap` | Natural English for 0.5 |
| `0.7-point gap` | `point-seven gap` | Drops redundant "zero" prefix |
| `0.9-point gap` | `point-nine gap` | Same pattern |
| `1.5-point gap` | `one-and-a-half-point gap` | Natural English for 1.5 |

> **Detection**: Any digit-form decimal immediately followed by `-point` in the
> source narration triggers this rule. Apply spoken-form conversion that avoids
> the word "point" appearing in both the number and the unit.

### Deliberate Pronunciation

When a key number requires slow, deliberate pronunciation, direct it through DIRECTOR'S NOTES:
1. **Director's Notes**: Describe the pronunciation intent ("Slow down and chew each digit of sixty-two with deliberate separation — like placing evidence on a table")
2. **TRANSCRIPT**: Contains only the clean spelled-out number (no tags)

---

## 3. Director's Notes — Pacing & Physical Direction Examples

When the agent needs to control pacing, pauses, or physical delivery, express them in DIRECTOR'S NOTES:

| Desired Effect | Director's Notes Instruction |
| --- | --- |
| Short pause between clauses | "Brief breath between these two clauses — the analyst is organizing thoughts." |
| Long designed silence | "Hold complete silence for two seconds after this line. The viewer needs time to read the on-screen quote." |
| Rapid scaffolding delivery | "Move through this data like reading coordinates — fast, mechanical, disposable." |
| Slow deliberate emphasis | "Slow down and chew each syllable of this number. Separate every digit like it costs something." |
| Audible exhale/sigh | "Audible exhale before this sentence — the physical release of processing surprising data." |
| Hesitation | "Slight hesitation before this word — the analyst is weighing whether to say it." |

---

## 4. Block-Type Map (Category Comparison)

Structural mapping of block types to allowed archetypes.
This map is enforced by `audit_opening_brackets.py`.

| Block Type | Allowed Archetypes | Key Constraint |
| ---------- | ------------------ | -------------- |
| `hook_contradiction` | A, B | Pitch Drop on data gap, not product name |
| `hook_curiosity_loop` | D, E | Progressive intensity, investigation leads |
| `rating_overview_lineup` | F | **Identical emphasis per product.** Direct equal rhythmic separation in Notes |
| `rating_overview_gap` | B, C | Sprint through headlines, brake on gap |
| `{theme}_leader` | F, D | Present strength -- not crown a winner |
| `{theme}_laggard` | C, D | Clinical, not mocking. **Register shift from Leader IS the contrast** |
| `{theme}_context` | E | Category-wide structural observation |
| `standout_{product_id}` | F, E, D | Controlled warmth -- orthogonal value spotlight |
| `verdict_category_judgment` | G | Macro-level category assessment |
| `verdict_use_case_picks` | G | **Identical vocal weight per recommendation.** Direct equal rhythmic separation in Notes |
| `verdict_outro` | F | Warm close -- friend, not broadcaster |

---

## 5. bgm_mood -> Delivery Alignment

| bgm_mood | Delivery Direction |
| -------- | ------------------ |
| `Bright` / `Neutral` | Conversational, lighter register |
| `Tense` / `Dark` | Gravitas territory, slower, heavier weight |
| `Silence` | Voice carries ALL weight -- Archetypes A or C only |
| `Triumphant` | Firm confidence, slightly elevated (never hype) |

---

## 6. Cross-Product Contrast Directing

Multi-product comparison videos require intentional tonal shifts between
blocks to make data gaps audible -- without verbal ranking language.

| Mechanism | Description |
| --------- | ----------- |
| **Archetype Contrast** | The shift between Leader(F) and Laggard(C) makes the gap audible |
| **Register Shift** | Laggard block MUST break tonal inheritance from Leader. State this in Notes |
| **Data Gap Stress** | Stress falls on the data value (percentage, ratio), NOT the product name |
| **Lineup Equalizer** | In list-format blocks, every item receives identical vocal weight |
