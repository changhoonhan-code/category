# Directing Reference — Technique Catalog

Reference tables for the Narration Agent. For rules and constraints → `SKILL.md`.

---

## Bracket Tags — Pacing & Disfluency Only (v2 Philosophy)

> **CRITICAL**: Inside TRANSCRIPT, use ONLY pacing/pause and disfluency tags.
> ALL acting direction — including emotional color, style, emphasis targets,
> and transitions — belongs in DIRECTOR'S NOTES as rich descriptive prose.
>
> Style tags (whispering, empathetic, curious, etc.) are BANNED from TRANSCRIPT.
> The model interprets emotional weight from DIRECTOR'S NOTES prose and the
> narration text itself. Inline tags exist solely for breath-forcing and pacing.

### Pacing & Pause Tags

| Tag | Effect | Reliability |
| --- | ------ | ----------- |
| `[extremely fast]` | Rapid-fire delivery from this point | High |
| `[speaking slowly]` | Reduced pace from this point | High |
| `[short pause]` | ~250ms stop (comma-level breath) | High |
| `[medium pause]` | ~500ms stop (sentence break) | High |
| `[long pause]` | ~1000ms+ stop (dramatic beat) | High |

> For pauses longer than 1 second, stack `[long pause]` tags:
> `[long pause] [long pause]` = ~2 seconds.

### Style Tags — MIGRATED TO DIRECTOR'S NOTES

> Style tags are **BANNED from TRANSCRIPT**. All emotional color is now
> expressed as rich descriptive prose in DIRECTOR'S NOTES, tied to specific
> sentences and words in the narration.

| Former Tag | DIRECTOR'S NOTES Responsibility |
| --- | --- |
| `[whispering]` | Describe reduced volume, breathy near-whisper on specific passage |
| `[shouting]` | Describe elevated volume, projected energy on specific phrase |
| `[sarcastic]` | Describe dry, ironic inflection on specific line |
| `[empathetic]` | Describe warmer, softer register for specific experience |
| `[curious]` | Describe rising intrigue tone on specific question/statement |
| `[excited]` | Describe contained enthusiasm, elevated energy on specific reveal |
| `[angry]` | Describe controlled edge, tense delivery on specific finding |
| `[thoughtful]` | Describe deliberate, reflective weight on specific observation |

**Permanently deleted** (persona-incompatible — never use in any layer):
- `[scornful]` — contempt breaks Category Intelligence Analyst persona
- `[robotic]` — mechanical delivery undermines data journalist credibility

> **These are NOT templates.** The agent reads the actual narration text and
> crafts unique, context-specific emotional direction for each block.

### Vocalization Tags

`[sigh]` · `[clears throat]` · `[uhm]`

### Absolutely Prohibited Content in Brackets

- ❌ Natural-language descriptions: `[Drop pitch, weight every digit with sharp consonants]`
- ❌ Scene/emotion narratives: `[The brightness of 69% evaporates here]`
- ❌ Invented timing tags: `[PAUSE=2s]`, `[Full stop]`, `[Brief pause]`, `[Micro-pause]`
- ❌ SSML markup: `<break>`, `<prosody>`, `<emphasis>`
- ❌ Archetype codes: `[Archetype C]`, `[Sustained Gravity]`

### Numerical Evidence — Spelled-Out Number Rule (Absolute)

**ALL numbers in TRANSCRIPT must be written as spoken English text.**
The TTS model frequently misfires on digit-form numbers (especially those
with commas: `1,759`, `123,456`). Digit-form numbers are BANNED from TRANSCRIPT.

The Narration Agent receives digit-form numbers from the Writer Agent's
`narration` field and converts them to spelled-out form during prompt writing.
The original `narration` field is never modified.

#### Conversion Rules

| Number Type | Digit Form (BANNED) | Spelled-Out Form (REQUIRED) |
| --- | --- | --- |
| Integers < 100 | `79` | `seventy-nine` |
| Integers 100-999 | `598` | `five hundred ninety-eight` |
| Integers 1,000+ | `1,759` | `seventeen fifty-nine` or `one thousand seven hundred fifty-nine` |
| Decimals | `4.2` | `four point two` |
| Percentages | `63.6%` | `sixty-three point six percent` |
| Ranges | `3-to-4 hours` | `three-to-four hours` |
| Ordinals | `1st`, `2nd` | `first`, `second` |

> For large integers (1,000+), prefer the conversational short form
> (`seventeen fifty-nine`) over the formal long form (`one thousand seven
> hundred fifty-nine`) unless the formal form reads more naturally in context.

#### Deliberate Pronunciation Directing

When a key number requires slow, deliberate, digit-by-digit pronunciation
(the "chew each digit" effect), do NOT use spaced digits in TRANSCRIPT.

Instead, use ALL of the following:
1. **TRANSCRIPT**: Write the number as normal spelled-out text with `[speaking slowly]` tag
2. **DIRECTOR'S NOTES → Key moments**: Add explicit pronunciation direction

**Example:**
```text
### DIRECTOR'S NOTES
- Key moments: "sixty-three point six percent" is the thesis —
  chew each digit with deliberate separation. Sharp consonants
  on every syllable. This number must ring in the viewer's ears.

#### TRANSCRIPT
[speaking slowly]
sixty-three point six percent positive.
```

#### Prohibited Patterns (Absolute)

| # | Prohibited | Replacement |
| - | --------- | ----------- |
| 1 | Digit-form numbers in TRANSCRIPT: `598`, `1,759` | Spelled-out: `five hundred ninety-eight`, `seventeen fifty-nine` |
| 2 | Spaced digits in TRANSCRIPT: `5 9 8`, `6 3 . 6` | Spelled-out + Director's Notes pronunciation direction |
| 3 | Comma-separated large numbers: `123,456` | Spelled-out: `one hundred twenty-three thousand four hundred fifty-six` |

Place `[speaking slowly]` before the spelled-out number. Detailed pronunciation
instructions (sharp consonants, chew each digit) go in DIRECTOR'S NOTES, not in brackets.

### Vocalization Strategy (Data Journalism Persona)

Non-verbal vocalizations add realism but must fit the "Category Intelligence Analyst" persona. The narrator is a composed professional — not a casual conversationalist.

#### Permitted Vocalizations & Placement

| Tag | Persona Fit | When to Use | Max per Script |
| --- | --- | --- | --- |
| `[clears throat]` | High | Before a major reveal or topic pivot. Signals "pay attention" | 1-2 |
| `[uhm]` | Moderate | Only in Hook Stage 1 (relatable moment) or before a surprising data point. Creates "the analyst pausing to choose words carefully" | 1 |
| `[sigh]` | Moderate | After delivering universally negative data (Universal Weakness context). Signals "even the analyst is affected by this finding" | 1 |
| `[laughing]` | Prohibited | Breaks data journalism persona. Never use | — |

#### Placement Rules

1. **Max 2-3 vocalization tags per entire script** (22+ blocks). More = parody.
2. Never place in Verdict blocks — the verdict is authoritative, not casual.
3. Never place in Laggard blocks — could imply mockery of the product.
4. Preferred placement: Hook (Stage 1), Context blocks, Standout pivots.

### Tag Misfire Prevention

The #1 cause of tag misfires is non-standard content inside brackets.

**Rule 1**: Brackets may contain ONLY pacing/disfluency tags (8 approved).
**Rule 2**: One tag per line. Use line breaks between tag and narration text.
**Rule 3**: NO style tags, sentences, or descriptions inside brackets.
**Rule 4**: NO SSML tags.
**Rule 5**: Inline tags exist for breath-forcing and pacing only — trust the text and Notes to carry emotion.

```text
# FRAGILE (misfire risk — model reads bracket content aloud):
[extremely fast] The 5-star count: 2,866. [Full stop. Drop to half speed, weight every digit] And 598 one-star reviews.

# ROBUST (standard tags + line breaks + spelled-out numbers):
[extremely fast]
The five-star count: twenty-eight sixty-six.
Four-star: four twenty-seven.
[long pause]
[speaking slowly]
And five hundred ninety-eight one-star reviews — a fourteen percent share.
```

### Depth Calibration — DIRECTOR'S NOTES Quality Bar

> **This example shows the minimum depth expected for DIRECTOR'S NOTES.**
> Style/emotion formerly conveyed by inline tags is now expressed as
> sentence-specific, word-level descriptive prose in Notes.
>
> **This is NOT a template.** The agent creates unique Notes for each block
> based on actual narration content. Copy-pasting = Anti-Pattern #1 violation.

**Theme Comparison Leader — Full-Depth Example:**

```text
### DIRECTOR'S NOTES
- Archetype: F
- Delivery: Warm, slightly elevated pitch — the analyst who found genuinely
  good data and presents it with quiet assurance. Not celebration; factual
  brightness. Softer register on the opening, contained Vocal Smile on the
  key percentage.
- Tone: Data-backed warmth. Vocal Smile territory.
- Emotional arc: Open "Product C's battery data tells a straightforward story"
  with the quiet confidence of an analyst who already knows the answer —
  slightly lowered volume, like sharing good news with a trusted colleague.
  On "seventy-eight percent," let contained brightness surface — chew each
  digit with deliberate separation; the number is the thesis. "Users
  consistently describe" flows naturally, conversational. "Without the
  charging case trick" — lift pitch on "without," lean into the differentiator
  through contrast, not volume. The warmth holds steady throughout but never
  tips into advocacy.
- Key moments: "seventy-eight percent" — Vocal Smile + deliberate delivery.
  "without" carries the differentiator contrast — slight pitch lift.
- Context: Previous block ended with category rating overview gap analysis.

#### TRANSCRIPT
Product C's battery data tells a straightforward story.
[speaking slowly]
seventy-eight percent of battery-related reviews are positive — the highest ratio in the category.
Users consistently describe ten-to-twelve-hour runtimes under mixed-use conditions.
[short pause]
That's without the charging case trick that other products in this lineup need
to hit similar numbers.
```

> **What makes this effective:**
> - **Sentence-level direction**: Each narration sentence has specific delivery intent
> - **Word-level targets**: "seventy-eight percent" and "without" have precise direction
> - **Emotional arc as prose**: What was formerly `[empathetic]` is a described journey
> - **TRANSCRIPT is clean**: Only pacing tags — emotional color lives entirely in Notes

---

## Directing Vocabulary (DIRECTOR'S NOTES Only)

These techniques are used in DIRECTOR'S NOTES to communicate delivery intent
to the TTS model's system prompt. They must **NEVER** appear inside TRANSCRIPT
bracket tags.

Always pair with a **specific target word or phrase** in the Key moments line.

| Technique | Description | When to Use |
| --------- | ----------- | ----------- |
| **Vocal Smile** | Soft palate raised, brightness | Positive reveals, praise |
| **Gravitas Drop** | Lower register, slower, weight on every syllable | Critical flaws, worst data |
| **Micro-pause** | `[short pause]` before key word | Shocking statistics |
| **Elongation** | Stretching a vowel to emphasize scale | "Sixty-eeight percent" |
| **Punchy Consonants** | Sharp, clipped delivery on hard consonants | Numbers, technical terms |
| **Tempo Drop** | Sudden 20-30% speed reduction | Context-to-reveal transition |
| **Volume Taper** | Gradually decreasing volume toward end | Understated disappointment |
| **Empathetic Delivery** | Narrator stays in the analytical observer persona but shifts to a softer, more empathetic register — acknowledging the reviewer's experience without attempting to "become" them. Use Gravitas Drop for negative experiences, Vocal Smile for positive ones. The emotional impact comes from the on-screen `highlight_phrase` + Visual Read Pause, not from vocal acting. **For Universal Weakness (`{theme}_context`) blocks**: do not direct sympathy toward any single product — instead adopt a "structural briefing" register (Reflective Discovery) that frames the limitation as a category-wide material/engineering constraint, delivered with measured sobriety rather than dramatic weight. | Blocks with `evidence_quotes` where narration paraphrases a reviewer's experience; `{theme}_context` blocks with `category_pattern_type: universal_weakness` |
| **Warm Connective** | Smooth, flowing, no hard stops | Bridge sentences between themes |

### Direction Quality — Notes vs. Inline

DIRECTOR'S NOTES carry ALL acting direction. TRANSCRIPT uses pacing/disfluency tags only:

| DIRECTOR'S NOTES (all acting direction) | TRANSCRIPT Inline (pacing/disfluency only) |
| --- | --- |
| "Drop pitch and slow down for the loss percentage. Sharp consonants on each digit." | `[speaking slowly]` |
| "Rapid-fire through the distribution as scaffolding, then hard brake on the outlier." | `[extremely fast]` ... `[long pause]` `[speaking slowly]` |
| "Softer register — acknowledge the frustration without dramatizing. Warmer tone on the paraphrase, measured sobriety on the data." | (Notes handle this — no inline tag) |
| "Return to confident, grounded tone after the pause. Deliberate, reflective weight on the conclusion." | (Notes handle this — no inline tag) |
| "Emphasize 'single' with a higher pitch — the isolated failure matters." | `[short pause]` (before the word) |
| "Volume Taper on the final clause — let the implication land quietly." | (no tag needed — text carries it) |

### Minimum Direction Requirements

Every block MUST meet the following requirements:

| Block length (sentences) | Min. DIRECTOR'S NOTES | Min. inline pacing/disfluency tags |
| --- | --- | --- |
| 1-2 sentences | 3-line Notes (incl. emotional color) | 1 pacing tag |
| 3-4 sentences | 4-line Notes (incl. Key moments + emotional color) | 2 pacing tags |
| 5+ sentences | 5-line Notes (incl. transitions + Key moments + emotional arc) | 3 pacing tags |

DIRECTOR'S NOTES handle ALL acting direction: emotional color, emphasis targets, transitions, pronunciation, and style.
Inline tags handle ONLY pacing/pause and human disfluency.

---

## Empathetic Delivery Guide (Evidence Quote Blocks)

In blocks where the narration paraphrases a reviewer's experience (per Quote Voicing Rule — narrator never reads the verbatim quote aloud), use DIRECTOR'S NOTES to communicate the empathetic intent. TRANSCRIPT uses pacing tags only.

| Reviewer Experience | DIRECTOR'S NOTES Direction | TRANSCRIPT Tag |
| ------------------- | -------------------------- | -------------- |
| Product failed immediately | "Gravitas Drop + matter-of-fact pace — let the data speak" | `[speaking slowly]` |
| Repeated failure / exhaustion | "Volume Taper + slower pace — warmer register, understated weight" | `[speaking slowly]` |
| Genuine praise | "Vocal Smile — brief brightness, grounded in data. Softer register." | (Notes handle emotional color) |
| Sharing a workaround | "Slightly lighter register, conversational, deliberate — but stay narrator" | (Notes handle emotional color) |
| Factual technical note | "Punchy Consonants on specifics — precise, grounded" | `[speaking slowly]` |
| Brief specific complaint | "Clipped pace, no embellishment — mirror the brevity" | (no tag — text carries it) |

> **Key principle**: The narrator **acknowledges** the reviewer's experience through the delivery intent in DIRECTOR'S NOTES. The verbatim quote appears on screen via `highlight_phrase` during the Visual Read Pause — that's where the reviewer's own voice lives.

---

## The 2-Speed Structure (Contrast Principle)

1. **Fast scaffolding** — context delivery, stat enumeration
2. **Slow reveal** — key data drop, the finding that matters

> **Critical**: A pause produces impact **only when it follows a fast section.**

```text
[extremely fast]
stat1. stat2. stat3.
[long pause]
[speaking slowly]
...and the worst?

# ❌ WRONG — uniform pacing with scattered pauses:
statement [medium pause] statement [medium pause] statement
```

**Max 1-2 pause directions per block.** If you need more, restructure the transcript.

### Mandatory 2-Speed Blocks

The following block types MUST include at least one speed transition (fast scaffolding → slow reveal OR baseline → tempo drop):

| Block Type | 2-Speed Application |
| --- | --- |
| `rating_overview_gap` | Sprint through headline numbers → hard brake on the gap |
| `{theme}_leader` | Flowing context → Tempo Drop on the key percentage |
| `{theme}_laggard` | Clinical enumeration → Gravitas Drop on the worst data point |
| `hook_contradiction` | Measured question → Pitch Drop on the contradiction data |

Blocks NOT requiring 2-Speed (single-tone delivery is acceptable):

- `{theme}_context` (Reflective Discovery — deliberate throughout)
- `standout_*` (Warm Conversational — flowing throughout)
- `verdict_outro` (Warm close — single register)

---

## Evocative Text Patterns (Lever 2 — READ-ONLY Reference)

Recognize these patterns in the narration text — each signals a specific DIRECTOR'S NOTES direction and inline tag response:

| Pattern in Transcript | DIRECTOR'S NOTES Direction | TRANSCRIPT Tag |
| --------------------- | -------------------------- | -------------- |
| `X — gone.` (one-phrase finality) | "Gravitas Drop + full stop before the fragment" | `[short pause]` before fragment |
| `N — also N.` (parallel zero) | "Punchy Consonants on each number; identical weight" | `[speaking slowly]` |
| `"That's not X. That's Y."` (reframe) | "Tempo Drop entering the second sentence" | `[medium pause]` between sentences |
| Single-word sentence (`"It snaps."`) | "Micro-pause before it; Volume Taper after" | `[short pause]` before |
| `"N distilled into one sentence:"` | "Tempo Drop immediately after the colon" | `[long pause]` after colon |
| Number + community validation | "Punchy Consonants on number; Vocal Smile on validation" | `[speaking slowly]` on number |

| Pattern | Example |
| ------- | ------- |
| X — gone. One phrase. | "Ten percent of the battery — gone." |
| N — also N. Parallel zero. | "22 reviews — zero positive. 16 more — also zero." |
| "That's not X. That's Y." | "That's not a variance. That's a different device." |
| Single-word sentence | "It snaps." |
| "[N] distilled into one sentence:" | "[N] reviews distilled into one sentence:" |
| Number + community validation | "[N] buyers marked this as helpful." |

---

## The 7 Pacing Archetypes

| # | Archetype | Character |
| - | --------- | --------- |
| A | **Staccato Cold Open** | Near-suspended, short sentences as full stops |
| B | **Analytical Inventory → Reveal** | Sprint scaffolding, hard brake on one number |
| C | **Sustained Gravity** | Single low pace, accumulation does the work |
| D | **Controlled Acceleration** | Baseline → speed through examples → hard landing |
| E | **Reflective Discovery** | Deliberate, pause-before-insight rhythm |
| F | **Warm Conversational** | Overview baseline, Vocal Smile, flowing |
| G | **Declarative Authority** | Firm, even, verdict register |

### Distribution Guide

```text
Hook:              B → A → D          (category question → contradiction → curiosity loop)
Rating Overview:   F → B/C            (lineup scaffolding → gap analysis)
Theme Comparison:  F/D → C/D → E     (leader → laggard → context; rotate across themes)
Standout:          F                  (controlled warmth — one per product)
Verdict:           G → G → F          (category judgment → use-case picks → warm close)
```

### Cross-Archetype Techniques

**Block-Level Empathetic Delivery** — when narration paraphrases a reviewer's experience, describe ALL emotional intent in DIRECTOR'S NOTES. TRANSCRIPT uses pacing tags only:

DIRECTOR'S NOTES:
```text
- Key moments: "hinge gave out" triggers softer register. Warmer tone
  acknowledging the frustration without dramatizing. Return to
  evidence-first tone after the pause.
- Emotional arc: Measured empathy on the paraphrase — the analyst
  acknowledging shared experience. Clinical return after the beat.
```

TRANSCRIPT:
```text
Fifty buyers described the same experience: three months in, the hinge gave out.
[short pause]
```

**Precision Emphasis** — for single-word or phrase-level weight without shifting the whole block:

DIRECTOR'S NOTES:
```text
- Key moments: "Forty-seven percent" is the thesis. Raise pitch and land
  the number firmly. The preceding sentence is deliberate, reflective
  buildup — each word lands with considered weight.
```

TRANSCRIPT:
```text
The data suggests something the spec sheet doesn't reveal.
[short pause]
[speaking slowly]
Forty-seven percent of negative reviews cite the exact same 3-month failure window.
```

---

## Block-Type Map & bgm_mood Alignment

### Block-Type Directing Map (Category Comparison)

| Block Type | Archetype | Default Character | Narrative Arc | Key Constraint |
| ---------- | --------- | ----------------- | ------------- | -------------- |
| Hook — Stage 1 (Category-Level Question) | Slow-Burn Reveal (B) | Measured curiosity, category-wide mystery, silence as tool. **Zero product references** | Low → building | |
| Hook — Stage 2 (Contradiction Reveal) | Authority Drop (A) | Controlled revelation, market contradiction weight. Product names as clauses only | Medium → high impact | |
| Hook — Stage 3 (Curiosity Loop) | Escalator (D) | Progressive intensity, investigation leads, controlled energy rise | Medium → high | |
| **Rating Overview — Lineup** | **F** | Brisk scaffolding. All product names land with **identical emphasis** — lineup, not ranking. BSR = "last month's sales volume" qualifier | Neutral baseline | **`[short pause]` between each product.** Counteract TTS descending list intonation |
| **Rating Overview — Gap** | **B → C** | Analytical precision. Sprint through headline numbers, hard brake on population gap | Rapid scaffolding → slow reveal | |
| **Theme Comparison — Leader** | **F / D** | Genuine brightness, grounded in data. Present a strength — not crown a winner | Warm flow (F) or controlled acceleration (D) | |
| **Theme Comparison — Laggard** | **C / D** | Clinical, matter-of-fact. Expose data pattern, not mock the product. **Register shift from Leader block IS the contrast** | Sustained gravity (C) or buildup → verdict (D) | |
| **Theme Comparison — Context** | **E** | Reflective, category-wide observation. Universal weakness / structural limitation framing | Deliberate, panoramic | |
| **Standout** | **F** | Controlled warmth — data-backed interest, not advocacy. Orthogonal Value spotlight | Factual reset → genuine brightness | Often `breathe` pacing — no `[extremely fast]`. Single-tone delivery, no 2-Speed |
| **Verdict — Category Judgment** | **G** | Macro-level category assessment. Firm, analytical | Authoritative, measured | |
| **Verdict — Use-Case Picks** | **G** | Trusted advisor. Each recommendation gets **identical vocal weight**. No product is "the winner" | Even authority, horizontal | **`[short pause]` between each recommendation.** Same energy first to last |
| **Verdict — Outro** | **F** | Quick, warm sign-off — friend saying goodbye, not broadcaster signing off | Warm close | Often `breathe` pacing — spacious delivery |

> **Evidence quotes** are embedded within theme blocks via `evidence_quotes` field — not a standalone block type. Use **Empathetic Delivery** direction in DIRECTOR'S NOTES when narration paraphrases a reviewer's experience. The verbatim quote is displayed on screen during the **Visual Read Pause** (SKILL.md §6).

### bgm_mood Alignment

| bgm_mood | DIRECTOR'S NOTES Direction |
| -------- | -------------------------- |
| `Bright` / `Neutral` | Vocal Smile territory, conversational pace |
| `Tense` / `Dark` | Gravitas Drop territory, slower pace, Volume Taper |
| `Silence` | Voice carries ALL weight — Archetypes A or C only |
| `Triumphant` | Firm confidence, slightly elevated energy (never hype) |

---

## Cross-Product Contrast Directing (Category Comparison)

The primary technique for multi-product category comparison videos. Product-to-product data gaps are made audible through intentional tonal shifts — not through verbal ranking language.

### Contrast Mechanisms

| Mechanism | Description | Application |
| --------- | ----------- | ----------- |
| **Block-Level Archetype Contrast** | The archetype shift between a Leader block (F) and a Laggard block (C) makes the data gap audible without ranking language | Theme Comparison scenes: `{theme}_leader` → `{theme}_laggard` |
| **Register Shift Directive** | Explicit "no warmth carryover" or "full register shift" direction in the Laggard block's DIRECTOR'S NOTES. Breaks TTS tonal inheritance from the previous block | First line of any Laggard or negative-contrast block's Notes |
| **Data Gap Stress** | When product names and numbers appear together, stress falls on the **data value** (percentage, ratio, count), NOT the product name (Noun). Prevents implicit ranking through vocal enthusiasm | All blocks containing cross-product numerical comparisons |
| **Lineup Equalizer** | In list-format blocks (`rating_overview_lineup`, `verdict_use_case_picks`), every item receives identical vocal weight. Counteract TTS "descending list intonation" bias | Rating Overview Lineup, Verdict Use-Case Picks |
| **Structural Briefing** | For Universal Weakness themes, adopt Reflective Discovery (E) register. Frame as category-wide limitation, not individual product attack | `{theme}_context` blocks with `category_pattern_type: universal_weakness` |

### Contrast Examples

**Leader → Laggard transition (inter-block contrast)**

Leader block prompt closing:
```text
### DIRECTOR'S NOTES
- Delivery: Warm, grounded. Data-backed brightness without celebration.
...

#### TRANSCRIPT
...without the charging case trick that other products in this lineup need.
```

Laggard block prompt opening (MUST break inherited tone):
```text
### DIRECTOR'S NOTES
- Delivery: Full register shift from previous block. Clinical, low-pitched,
  unemotional. No warmth carryover — the contrast between blocks IS the directing.
- Key moments: Land "sixty-two percent negative" with steady clinical weight —
  chew each digit of "sixty-two" with deliberate separation. The irony
  of "outselling every competitor" gets volume taper — let it speak for itself.

#### TRANSCRIPT
[speaking slowly]
Product A tells a different story.
[short pause]
[speaking slowly]
sixty-two percent of battery mentions are negative — the highest negative ratio in the
category by a twenty-point margin.
```

**Data Gap Stress (intra-block technique)**

```text
# ❌ WRONG — description inside brackets:
[Micro-pause. Drop pitch — land the gap, not the name] That's a 40-point gap.

# ✅ CORRECT — direction in Notes, standard tag inline:
### DIRECTOR'S NOTES
- Key moments: Land "forty-point gap" with full weight. Pitch drops on the
  number, not the product name. Chew each syllable of "forty-point."

#### TRANSCRIPT
[short pause]
[speaking slowly]
That's a forty-point gap from the category leader.
```

> For full block-level DIRECTOR'S NOTES + TRANSCRIPT examples → `references/category_comparison_examples.md`.

---

## Opening Direction — DIRECTOR'S NOTES Vocabulary Bank

Each block's DIRECTOR'S NOTES `Delivery:` line must be unique across the entire
script. Use the following vocabulary to differentiate block openings in Notes.
TRANSCRIPT opens with a standard tag only.

### Leader Block Openings (Archetype F/D)

Use DIFFERENT delivery descriptions for each leader block.

DIRECTOR'S NOTES vocabulary:
- "Warm shift — the battery story takes an unexpected turn here"
- "Bright register entering. Data-backed brightness, not celebration"
- "Reset to grounded curiosity. The fit data reveals the widest gap"
- "Flowing, natural — present the strength without crowning a winner"

TRANSCRIPT inline: pacing tags only (e.g. `[short pause]`, `[speaking slowly]`). Emotional color lives in DIRECTOR'S NOTES.

**Anti-Pattern**: Same delivery description used for 4+ leader blocks.

**Fix**: Each DIRECTOR'S NOTES must reference the specific narration content:

- ❌ `Delivery: Warm, grounded.` (repeated across all leaders)
- ✅ `Delivery: Warm shift — the battery story takes an unexpected turn. Data-backed brightness enters.`
- ✅ `Delivery: Reset to grounded curiosity. The fit data is about to reveal the widest gap in the category.`

### Laggard Block Openings (Archetype C/D)

The register shift directive is mandatory, but HOW you describe it must vary.

DIRECTOR'S NOTES vocabulary:
- "Full register shift. The warmth of 69% evaporates here."
- "Clinical, low-pitched. Where Samsung earned warmth, this data earns ice."
- "Strip all residual brightness. Measured sobriety from the first word."
- "Drop to clinical enumeration — the contrast IS the message."

TRANSCRIPT inline: `[speaking slowly]` or `[short pause]`. Emotional weight lives in DIRECTOR'S NOTES.

**Anti-Pattern**: Same register shift description used for 5+ laggard blocks.

**Fix**: Each DIRECTOR'S NOTES must describe the shift differently AND reference prior context:

- ❌ `Delivery: Full register shift — clinical, measured pace. No warmth carryover.`
- ✅ `Delivery: The brightness of 69% evaporates here. Drop to clinical enumeration — the contrast IS the message.`
- ✅ `Delivery: Where Samsung just earned warmth, this data earns ice. Measured, steady, no residual brightness.`
