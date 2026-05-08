---
description: Review Timing — Orchestrator maps evidence reviews to narration time ranges for Remotion rendering.
---

# /9_timing

> **Agent**: Orchestrator (direct execution — no subagent SKILL needed).
> **Execution Model**: Sequential N-Block — each group processes up to 5 blocks in a **SEPARATE fresh session** to prevent context overload.
> **Purpose**: Assign `start_sec` and `end_sec` to each evidence review, so Remotion knows WHEN to show each review card during the narration.

## Prerequisites

- `data/script_output.json` must exist (Writer + Curator output)
- `data/narration_audio/manifest.json` must exist (TTS + Sync output)

---

## Step 1: Generate Block Data (Deterministic)

// turbo
```bash
python tools/extract_block_data.py
```

This script assembles per-block JSONs from `script_output.json`, `manifest.json`, and the review DB. Output: `data/blocks/{scene_type}_{block_id}.json`.

---

## Step 2: Prepare Input (Deterministic)

// turbo
```bash
python tools/prepare_review_timing.py
```

This script:
- Reads all `data/blocks/*.json` with evidence_reviews
- Splits each block's narration into sentences
- Maps each sentence to a `(time_start, time_end)` range via `word_timestamps`
- Outputs `tmp/review_timing_input.json` with minimal review metadata per block

---

## Step 3: Orchestrator Semantic Mapping (N-Block Groups)

> This is the **only step requiring agent judgment**. The orchestrator reads the prepared input and assigns each review to the optimal narration sentence.

### 2.1 Load Input

1. Read `tmp/review_timing_input.json`.
2. Determine which group to process:
   - If `tmp/review_timing_output.json` doesn't exist → Start from Group 1
   - Otherwise → Continue with the next unprocessed group

### 2.2 Per-Group Mapping Protocol

For each block in the current group (up to 5 blocks):

1. **Read the sentences** — understand the narration's semantic flow (what is each sentence saying?).
2. **Read the reviews** — understand each review's highlight_phrase, rating (positive/negative), and title.
3. **Assign each review to a sentence** — which narration sentence does this review best support?

   Mapping criteria:
   - **Content alignment**: Match the review's topic/sentiment to the narration sentence that discusses the same concept.
   - **Star rating alignment**: Negative reviews (★1-2) → sentences describing problems/failures. Positive reviews (★4-5) → sentences describing strengths/praise.
   - **Temporal spread**: Avoid clustering all reviews into one sentence. Distribute across the block's duration when semantically valid.

4. **Calculate display timing** from the matched sentence's time range:
   - `start_sec` = sentence's `time_start` (or slightly before, to let the card appear as the narrator begins the relevant statement)
   - `end_sec` = `start_sec + 3.0` seconds (fixed display duration)
   - If two reviews map to the same sentence, stagger them: second review starts 1.5 sec after the first.
   - Clamp `end_sec` to never exceed `audio_duration_sec`.

5. **Provide matched_sentence** for each assignment (the narration sentence text — for debugging).

### 2.3 Write Output

Write (or append to) `tmp/review_timing_output.json` in this schema:

```json
{
  "blocks": [
    {
      "block_id": "active_context",
      "assignments": [
        {
          "review_id": "R2YQD32SXN6S8U",
          "start_sec": 7.74,
          "end_sec": 10.74,
          "matched_sentence": "...report a piercing feedback screech loud enough to be alarming.",
          "sentence_index": 1
        }
      ]
    }
  ]
}
```

### 2.4 End Group Session

> **STOP HERE.** Instruct the user to open a **new chat session** and type `@[/timing]` to continue with the next group. Do NOT continue in the same session.
>
> If all groups are complete, proceed to Step 4.

---

## Step 4: Inject Timing (Deterministic)

// turbo
```bash
python tools/inject_review_timing.py
```

This script:
- Reads `tmp/review_timing_output.json`
- Validates all timing assignments (bounds, ordering, no overlaps)
- Injects `start_sec`, `end_sec`, and `matched_sentence` into each evidence_review in `data/blocks/*.json`

---

## Verification

After Step 4, spot-check 2-3 blocks:

1. Open a block JSON (e.g. `data/blocks/metric_chapter_active_context.json`)
2. Verify each `evidence_review` has `start_sec` and `end_sec`
3. Confirm negative reviews appear during problem-describing narration segments
4. Confirm positive reviews appear during praise/strength narration segments
5. Confirm no timing overlaps between consecutive reviews
