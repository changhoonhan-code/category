---
description: ReviewLens Audio Production — /prompt → /tts → /sync
---

# Audio Production: Narration & Timestamp Sync

This workflow generates block-level TTS narration based on the finalized script and aligns word-level timestamps.

## Prerequisite Check

Verify the existence of the following file:

- `data/script_output.json`

> [!WARNING]
> If the above is missing, output a **warning message**: "Script Writing and Review are not complete. Please run `/run_write` (new session) then `/run_review` first."

---

## Step 0: Session Cleanup

Remove stale artifacts from any previous Audio Production session to prevent carry-over contamination:

```bash
python tools/cleanup_session.py --stage audio
```

---

## Step 0.3: Filter Script for Narration Context

```bash
python tools/filter_script.py --profile narration
```

Generates `tmp/script_narration.json` — the **full-script** lightweight view with non-narration fields stripped.

This file is preserved throughout the entire 4-Group execution:
- `scene_handoff_manager.py` uses it for block ordering across groups
- `runner_phase2_tts.py` and `word_align.py` read `data/script_output.json` directly

> [!WARNING]
> Do NOT overwrite this file with group-filtered versions. Per-group filters use `--output tmp/script_narration_group{id}.json` (see `/prompt` workflow).

> [!NOTE]
> `runner_phase2_tts.py` and `word_align.py` continue reading `data/script_output.json` unchanged.

---

## Step 0.4: Visual Read Pause Map

Generate a lookup file that maps each block to its Visual Read Pause duration (if applicable). The Narration Agent uses this to insert `[long pause]` tags without needing access to `evidence_quotes` content.

```bash
python tools/generate_visual_pause_map.py \
    --script data/script_output.json \
    --output tmp/visual_pause_map.json
```

The script extracts `evidence_quotes` presence and `highlight_phrase` word count per block, then computes `pause_sec` using:

- highlight_phrase ≤ 5 words → 1.5
- highlight_phrase 6–8 words → 2.0
- highlight_phrase 9–10 words → 2.5

Blocks without `evidence_quotes` are mapped to `null`.

> [!NOTE]
> This file is consumed by the Narration Agent in Step 1 (see SKILL.md §6). It does NOT modify `script_output.json`.

---

## Step 0.5: System Prompt Base Setup

Generate the TTS system prompt base (Audio Profile + Recording Session + Scene) with dynamic data automatically injected:

```bash
python tools/generate_tts_system.py
```

The script reads `category_analysis.json` and injects category name, product names, product count, and total review count into the template. Writes `tmp/tts_system_base.txt`.

The Narration Agent copies this system prompt into the **top of every `tts_prompt_{block_id}.txt`** file, followed by `---`, then Director's Notes and TRANSCRIPT. Each prompt file is self-contained -- the TTS API receives only `prompt`, no separate system instruction.

> [!NOTE]
> Skill file loading (SKILL.md, directing_reference.md) happens **per group session** in the `/prompt` workflow. Step 0.5 only generates the system prompt text that gets embedded into each prompt file.

---

## Step 1: Per-Block Prompt Writing (Hybrid 4-Group Execution)

> This step runs across **4 separate sessions** to prevent cognitive overload.
> Each session loads ALL skill files fresh — the repeated cost is quality insurance, not waste.
> See `/prompt` workflow for the full per-group execution protocol.

### Quick Reference

| Group | Filter command | Est. Blocks |
|-------|---------------|-------------|
| 1 (Opening) | `python tools/filter_script.py --profile narration --group 1` | 4 |
| 2a (Theme Front) | `python tools/filter_script.py --profile narration --group 2a` | 7-9 |
| 2b (Theme Back) | `python tools/filter_script.py --profile narration --group 2b` | 4-6 |
| 3 (Closing) | `python tools/filter_script.py --profile narration --group 3` | 5-7 |

For each group:
1. Filter script (`--group`) → Load handoff (if not Group 1) → Load ALL skill files → Write prompts → Self-check → Generate handoff → **New session**

After all groups:
1. `python tools/audit_opening_brackets.py` → fix violations if any
2. Proceed to Step 2 (Synthesis)

> **Key rules**: no copy-paste DIRECTOR'S NOTES Delivery patterns across blocks — every block's Delivery description must be unique. For blocks with `evidence_quotes`, insert a Visual Read Pause using `[long pause]` tags after the Visual Handoff Line (see SKILL §6). See SKILL §7 Anti-Patterns for full checklist.

---

## Step 2: Synthesis

After writing **all** `tmp/tts_prompt_*.txt` files, run the automation runner:

```bash
python tools/runner_phase2_tts.py
```

The runner handles synthesis + QA + retries + manifest in a single pass:

- Each block synthesized, then evaluated by `audio_evaluator.py` (Gemini multimodal)
- QA checks: **tag misfire** (bracket tags read aloud) + **monotone/quality** + **completeness**
- Up to **3 attempts** per block (initial + 2 retries)
- Writes `data/narration_audio/manifest.json` with `qa_passed` and `qa_reason` per block

**Manual single-block fallback** (re-generating one specific block only):

```bash
python tools/tts_synthesize.py \
    --prompt-file  ./tmp/tts_prompt_{BLOCK_ID}.txt \
    --output       data/narration_audio/{BLOCK_ID}.wav \
    --model        gemini-2.5-pro-preview-tts
```

**Manifest schema** (canonical definition — inline below):

```jsonc
{
  "<block_id>": {
    "audio_path": "data/narration_audio/<block_id>.wav",
    "actual_duration_sec": 4.235,  // MUST be this key — NOT "duration_sec"
    "qa_passed": true,
    "qa_reason": "Natural delivery..."
  }
}
```

---

## Step 3: Quality Check & Re-generation

Tag misfire and monotone/quality checks are automated by `audio_evaluator.py` inside the runner. Remaining manual checks:

1. **QA failures**: Scan `manifest.json` for `qa_passed: false` — these exhausted all 3 retries. Read `qa_reason` to diagnose, revise prompt, re-generate.
2. **Block count**: Manifest entries = blocks in `script_output.json`.
3. **File integrity**: All WAV files non-zero bytes.

   ```bash
   # List WAV files with sizes — any 0-byte file is a failure
   ls -la data/narration_audio/*.wav
   ```

4. **File size**: Flag any WAV under **10 KB** — silent or corrupt.
5. **Duration range**: `actual_duration_sec` must be **2.0 – 90.0 seconds**.
6. **Pacing sanity**: `word_count / actual_duration_sec` must be **1.5 – 4.0 words/sec** (English TTS ~130–160 wpm).

7. **Flat text flags**: Check `tmp/flat_text_flags.json` (written by the Narration Agent in Step 1).
   - `minor` flags: The Narration Agent compensated through directing. Note them but no action required.
   - `major` flags: The narration text itself is too flat for TTS direction to save. **Action**: Manually revise the `narration` field in `data/script_output.json` for the flagged block(s), then re-write the TTS prompt and re-run synthesis for those blocks only.

   ```bash
   # After revising narration in script_output.json:
   # 1. Refresh the filtered view so the agent sees the updated narration
   python tools/filter_script.py --profile narration
   # 2. Rewrite tmp/tts_prompt_{block_id}.txt with updated narration
   # 3. Re-run single-block synthesis:
   python tools/tts_synthesize.py \
       --prompt-file  ./tmp/tts_prompt_{BLOCK_ID}.txt \
       --output       data/narration_audio/{BLOCK_ID}.wav
   ```

### Re-generation

For any flagged block:

1. Read `qa_reason` in manifest — tag misfire vs. monotone vs. other.
2. Revise `./tmp/tts_prompt_{block_id}.txt` per SKILL.md §2–§4 directing guidelines.
3. Re-run manual single-block fallback (Step 2) and update `manifest.json`.

---

## Step 4: Word-Level Timestamp Alignment

```bash
python tools/word_align.py \
    --audio-dir    data/narration_audio/ \
    --manifest     data/narration_audio/manifest.json \
    --script       data/script_output.json \
    --output       data/word_timestamps.json \
    --updated-script data/final_script_with_narration.json
```

Produces:

- `data/word_timestamps.json` — per-word `start` / `end` timestamps (seconds, 3 decimal places)
- `data/final_script_with_narration.json` — script with `narration_audio` field, `absolute_start_sec` / `absolute_end_sec` timeline, and `total_duration_sec`

---

## Completion Criteria

All of the following must be true:

- [ ] `data/narration_audio/manifest.json` exists
- [ ] `data/word_timestamps.json` exists
- [ ] `data/final_script_with_narration.json` exists
- [ ] Manifest block count = `script_output.json` block count
- [ ] All WAV files referenced in the manifest are non-zero bytes
- [ ] `tmp/bracket_audit_report.json` exists with `status: PASS` (run `python tools/audit_opening_brackets.py` if missing)
