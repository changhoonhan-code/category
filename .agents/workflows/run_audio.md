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

This file is preserved throughout the entire N-group execution:
- `scene_handoff_manager.py` uses it for block ordering across groups
- `runner_phase2_tts.py` and `word_align.py` read `data/script_output.json` directly

> [!WARNING]
> Do NOT overwrite this file with group-filtered versions. Per-group filters use `--group {N}` which auto-saves to `tmp/script_narration_group{N}.json` (see `/prompt` workflow).

> [!NOTE]
> `runner_phase2_tts.py` and `word_align.py` continue reading `data/script_output.json` unchanged.

---

## Step 0.4: Prompt File Format

The Narration Agent writes each `tts_prompt_{block_id}.txt` as a self-contained prompt: Preamble → Audio Profile → Director's note → Scene → Sample Context → Transcript. Each prompt file is self-contained — the TTS API receives only `prompt`, no separate system instruction.

> [!NOTE]
> Skill file loading (SKILL.md) happens **per group session** in the `/prompt` workflow. The agent constructs the Audio Profile section directly from script data — no separate generation step required.

---

## Step 1: Per-Block Prompt Writing (Sequential N-Block Execution)

> This step runs across **multiple separate sessions** (5 blocks per group) to prevent cognitive overload.
> Each session loads ALL skill files fresh — the repeated cost is quality insurance, not waste.
> See `/prompt` workflow for the full per-group execution protocol.

### Quick Reference

Groups are sequential chunks of 5 blocks (`BLOCKS_PER_GROUP` in `config.py`).
For a 21-block script: 5 groups (5+5+5+5+1 blocks).

```bash
python tools/filter_script.py --profile narration --group {N}  # N = 1, 2, 3, ...
```

For each group:
1. Filter script (`--group N`) → Load handoff (if not Group 1) → Load ALL skill files → Write prompts → Self-check → Generate handoff → **New session**

After all groups:
1. `python tools/audit_prompt_quality.py` → fix violations if any
2. Proceed to Step 2 (Synthesis)


> **Key rules**: no copy-paste Style patterns across blocks — every block's Style description must be unique. See SKILL §2 TTS-Safe Writing Rules and §3 Audio Tag Palette for full checklist.

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

## Step 3: Post-Synthesis Verification

> Tag misfire, monotone, and completeness checks are fully automated by `runner_phase2_tts.py` (Step 2). This step covers only **post-runner manual verification**.

1. **QA failures**: Scan `manifest.json` for `qa_passed: false` — these exhausted all 3 retries. Read `qa_reason` to diagnose, revise the prompt file, and re-run single-block synthesis (Step 2 fallback command).
2. **Block count**: Manifest entries must equal blocks in `script_output.json`.
3. **Flat text flags**: Check `tmp/flat_text_flags.json`.
   - `minor`: No action required (Narration Agent compensated through directing).
   - `major`: Manually revise the `narration` field in `data/script_output.json` for the flagged block(s), then re-write the TTS prompt and re-run synthesis.

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
- [ ] `tmp/prompt_audit_report.json` exists with `status: PASS` (run `python tools/audit_prompt_quality.py` if missing)
