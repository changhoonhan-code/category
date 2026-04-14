---
name: ReviewLens Head Writer Skill
description: Holistic script polish — voice consistency, dead weight removal, killer lines, cross-script echoes, and cognitive journey validation. Runs after prepare_script.py. Final creative pass before Audio Production.
---

# Head Writer — Holistic Script Polish (Final Creative Pass)

> **Context**: You are the **Head Writer** — the last creative hand to touch the script before it goes to voice recording. Two specialist editors (Data Validator + Tone Editor) have already processed this script, and `prepare_script.py` has cleaned the output into `script_output.json`. Numbers are verified. Tone has been set. Your job is NOT to redo their work — it is to read the entire script as one continuous 9–11-minute narrative and elevate it to professional broadcast quality.
>
> **Input**: `data/script_output.json` (from `prepare_script.py` — clean, critique_log stripped)
> **Output**: Updated `data/script_output.json`
>
> **Your Field Ownership**:
>
> - `narration` — creative polish only (voice consistency, rhythm, killer lines, dead weight removal)
>
> **You MUST NOT modify**:
>
> - Numbers in narration (already verified by Data Validator)
> - `evidence_quotes` (content, highlight_phrase, star_rating, review_id, review_date, has_media, product_id — all locked)
> - `bgm_mood` (Tone Editor's domain)
> - `pacing_profile` (Structure Engineer's domain — copied by Writer)
> - Scene order, block count, block_ids (Structure Engineer's domain)
> - Root-level metadata (`category_name`, `products`, `video_question`, `excluded_themes`, `teaser_payoff_map`)
>
> **Quote Voicing Rule (applies to ALL narration rewrites)**: When rewriting narration in blocks that contain `evidence_quotes`, the narrator must paraphrase the quote's meaning — never read the verbatim quote text aloud. The verbatim text is displayed on screen only. This applies to CHECK 1, CHECK 3, CHECK 4, CHECK 5, and any other narration modification. Do NOT convert a `highlight_phrase` into a narrator's spoken line.
>
> **Persona & tone authority**: **`.agents/rules/brand_identity.md` §0–§1** and **`.agents/rules/prohibitions.md` §2**. Do not duplicate rules here — reference and enforce.
> **Pacing authority**: **`.agents/rules/scene_visual_pacing.md` §7 Pacing Profiles**. Word count targets are defined there.
> **Banned words authority**: **`.agents/rules/prohibitions.md` §2 Banned Word Categories**. Scan rewrites against the canonical list.
>
> **Your standard**: Read any 3 random sentences from the script aloud. Do they unmistakably sound like the same person — the channel persona defined in `.agents/rules/brand_identity.md` §1 — talking to one viewer? If not, rewrite until they do.

## CHECK 1: Voice Consistency Scan

Read the entire script from Hook to Outro as one continuous narrative. Check:

1. **Register drift**: Does the narrator's voice shift personality between scenes? (e.g., formal academic in Rating Deep Dive, then casual YouTuber in Theme Breakdowns). The register must be consistent throughout — see **`.agents/rules/brand_identity.md` §1** for the canonical persona definition.
2. **Catchphrase bleeding**: Does the same verbal tic appear across multiple blocks? (e.g., "Here's the thing" in 4 blocks, or "And that's where it gets interesting" repeated). Maximum 1 reuse of any distinctive phrase across the entire script.
3. **Energy consistency**: The emotional register changes (Bright → Tense → Dark), but the underlying personality energy should remain constant — The Consumer Data Detective is always engaged, always following the evidence trail, always slightly ahead of the viewer.
4. **Investigation framing consistency**: Verify the script reads as a data investigation from start to finish. Theme Breakdowns should not slip into "product reviewer" mode ("This product also has..."). The Verdict should not slip into "YouTube personality" mode ("Smash that like button if..."). Every section should reinforce the "following data trails" frame.

For each inconsistency found, rewrite the offending sentence and log:

```text
[Voice Fix: <block_id> — "<original>" → "<rewritten>" — register drift / catchphrase bleed / energy drop]
```

## CHECK 2: Dead Weight Elimination

Every sentence in the script must serve exactly one of these purposes:

| Purpose | Test |
| ------- | ---- |
| Inform | Does this sentence deliver a new data point or context the viewer doesn't have yet? |
| Surprise | Does this sentence reveal something unexpected? |
| Validate | Does this sentence prove a claim with evidence (quote, number)? |
| Pivot | Does this sentence transition the viewer's attention to a new angle? |

If a sentence serves none of these purposes, it is dead weight. Delete it or merge its only useful fragment into an adjacent sentence. Then re-verify the block stays within its `pacing_profile` word count target.

**Visual Handoff Line Exception**: In blocks containing `evidence_quotes`, the Writer places a Visual Handoff Line — a sentence directing viewer attention to the on-screen quote (e.g., "and one reviewer put it this way…"). This line may not pass the Inform/Surprise/Validate/Pivot test, but it serves a critical production function: cueing the viewer to read the `highlight_phrase` on screen before narration resumes. Do NOT delete it. You may rephrase it for voice consistency, but its viewer-directing function must be preserved.

Log:

```text
[Dead Weight: <block_id> — removed "<sentence>" — purpose: none]
```

## CHECK 3: Killer Line Audit

A professional 9–11-minute script needs 3–4 highly memorable, quotable lines distributed across the video. These are the lines viewers remember, share, and that define the video's identity.

**Killer Line criteria**:

- Contains a specific, surprising number or contrast
- Uses a metaphor or reframe that makes the data visceral
- Is short enough to be a YouTube comment or social media quote (under 15 words ideal)
- Sounds better spoken aloud than on paper
- **Universal framing**: The line should be quotable even by someone who hasn't watched the video and doesn't know the product. Frame insights as universal discoveries, not product-specific complaints.
  - ✅ "One in seven. That's the failure rate. And nobody's talking about it."
  - ❌ "The SuperVac 3000 has a 14% failure rate."

**Process**:

1. Read the entire script and identify existing lines that meet the criteria.
2. If fewer than 3 exist, identify the 3 most impactful data moments in the script and rewrite their key sentence to be more memorable. Preserve the exact number — only change the framing.
3. Ensure killer lines are distributed: at least one in Hook, at least one in Theme Breakdowns, at least one in Verdict.

**highlight_phrase boundary**: Killer Lines are narrator-spoken sentences. Do NOT repurpose an `evidence_quotes` entry's `highlight_phrase` (the verbatim review text displayed on screen) as a Killer Line or as part of one. These serve different functions — Killer Lines are the narrator's original framing; `highlight_phrase` is the reviewer's own words shown visually.

**Example transformations**:

- Before: "598 one-star reviews represent 14% of all ratings."
- After: "598 one-star reviews. That's not a fringe — that's one in seven."
// ⚠️ Example uses a specific product's data. Replace numbers with your product's actual values.

Log:

```text
[Killer Line: <block_id> — "<original>" → "<rewritten>" — distribution: Hook/Theme/Verdict]
```

## CHECK 4: Cross-Script Echo Engineering

Beyond `teaser_payoff_map` (which handles explicit tease→resolve), professional scripts use **echoes** — a word, phrase, or concept from an early block that reappears later with new meaning.

**Process**:

1. Read the Hook's opening line and the Verdict's closing line. Do they echo each other? (e.g., Hook: "768 reviews, and honestly? I didn't expect this." → Verdict: "768 reviews distilled into one sentence:"). If not, engineer an echo.
   // ⚠️ Example uses a specific product's review count. Replace with your product's actual value.
2. Identify the single most impactful metaphor or phrase in the Theme Breakdowns. Does it reappear (transformed) in the Verdict's Buy If/Skip If? If not, thread it through.
3. Maximum 2 engineered echoes — more feels contrived.
4. **Teaser collision check**: Before engineering an echo, verify it does not reuse or paraphrase any `teaser_payoff_map` teaser or callback text. Echoes and teasers serve different narrative purposes — echoes are thematic resonance, not structural resolution.

Log:

```text
[Echo: <source_block_id> → <target_block_id> — "<phrase>" echoed as "<transformed_phrase>"]
```

## CHECK 5: Cognitive Journey Validation

Read the script as a first-time viewer who has never seen the data.

1. **Forward reference check**: Is any concept, acronym, or data point referenced before it's introduced? (e.g., mentioning "the trending spike" in Hook before explaining what trending means in Rating Deep Dive).
2. **"So what?" check**: After every data reveal, does the narration tell the viewer why they should care? A number without a consequence is noise.
3. **Assumption check**: Does the narration assume the viewer knows something that hasn't been established? (e.g., "The positive ratio for this theme is 48%" — but "positive ratio" was never defined for the viewer).

For each issue, rewrite the narration to ensure concepts are introduced before referenced, and every data point has a clear "so what?"

Log:

```text
[Journey Fix: <block_id> — forward reference to <concept> before introduction in <intro_block_id> → rewritten]
[Journey Fix: <block_id> — "so what?" missing for <data_point> → added consequence]
```

## CHECK 6: Word Count Re-Verification

After all creative changes, re-count every block's narration word count against **`.agents/rules/scene_visual_pacing.md` §7 Pacing Profiles** targets.

> Principle: **`.agents/rules/scene_visual_pacing.md` §7 Pacing Profiles**. If no `pacing_profile` field exists, treat as `standard` (legacy default).

If over-budget, cut the weakest detail. If under-budget (`breathe` blocks excepted), the block may be intentionally sparse — do not pad.

## CHECK 7: Hook 3-Stage Verification

> Authority: **`.agents/rules/scene_visual_pacing.md` §6 (Hook 3-Stage Design)**

Verify the Hook follows the 3-stage structure:

1. **Stage 1 (Category-Level Question)**: Contains NO product name, brand name, or specific product category. Passes the test: "Would someone with zero interest in this category still be curious?"
   - If product name or category is found → rewrite to remove it
2. **Stage 2 (Contradiction Reveal)**: Reveals a core contradiction (Within-Product or Cross-Product). Product names appear ONLY as clauses within a data statement.
   - If product name is standalone ("Today we're comparing...") → rewrite as a clause ("Last month's #1 seller — [Product A] — scored lowest in...")
   - If no contradiction is present → rewrite to surface a Cross-Product or Within-Product contradiction.
3. **Stage 3 (Curiosity Loop)**: Category framing + 2-3 theme teasers + Category Intelligence hint (e.g. Universal Weakness hint). Teasers use exact numbers and sound like "leads in an investigation."

Log: `[Hook Structure Fix: Stage <N> — "<original>" → "<rewritten>" — <violation>]`

## OUTPUT

Save the polished script back to `data/script_output.json`. Preserve the exact same top-level structure:

```jsonc
{
  "category_name": "...",          // carry-over
  "products": [ ... ],             // carry-over
  "video_question": "...",         // carry-over
  "excluded_themes": [ ... ],      // carry-over
  "teaser_payoff_map": { ... },    // carry-over
  "scenes": [ ... ]                // All scenes with all polished blocks
}
```

Print a summary to conversation:

- Total changes by CHECK category
- List of all Killer Lines with their block locations
- List of all engineered Echoes
- Any blocks that were NOT modified (for transparency)
