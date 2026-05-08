---
description: Audio Step 1 — Prompt. Write Director's Notes and vocal direction prompts per block (Sequential N-Block Execution).
---

# /prompt

> **Agent Skill**: The Narration Agent (`reviewlens_narration_agent`) owns this step.
> **Execution Model**: Sequential N-Block — each group processes up to 5 blocks in a **SEPARATE fresh session** to prevent cognitive overload.
> This is not optional optimization; it is the primary quality defense mechanism.

## Why Separate Sessions?

A single session writing 21+ TTS prompts sequentially suffers from **Creative Fatigue**:
- Blocks 1–5: Rules fully loaded, diverse patterns → high quality
- Blocks 6–12: Rules fading, patterns repeating → medium quality
- Blocks 13–21: Self-output lock-in, rules partially forgotten → **lowest quality**

Each group session loads ALL skill files fresh — the repeated context cost is not waste, it is **rule re-recognition insurance**.

## Group Model

Groups are **sequential chunks of 5 blocks** in script order. No keyword classification, no hardcoded scene names — purely block-count driven.

- Group size: `BLOCKS_PER_GROUP = 5` (defined in `config.py`)
- Group count: `ceil(total_blocks / 5)` — auto-detected from `script_output.json`
- For a 21-block script: Groups 1(5), 2(5), 3(5), 4(5), 5(1)

```bash
python tools/filter_script.py --profile narration --group {N}
```

> [!NOTE]
> `--group` is a 1-based integer. Output auto-saves to `tmp/script_narration_group{N}.json`. The script prints `Group N/M: blocks X–Y of Z` so you always know the total.

> [!IMPORTANT]
> Terminal encoding artifacts: Em-dashes (`—`) and other Unicode characters may appear as `??` in PowerShell console output. This is a shell rendering issue, not a data corruption problem. Always verify data content via `view_file` on the output JSON, not via console STDOUT.

## Per-Group Execution Protocol

Repeat the following for each group in order: **1 → 2 → 3 → ... → N**

### Step -1: Auto-Detect Next Group (Do this FIRST)

When invoked via `@[/prompt]` without a specific group argument, you MUST automatically determine the next group to process:
1. Use `view_file` on `tmp/scene_handoff.json`.
2. Look at `"completed_groups"` array and `"total_groups"` field:
   - If file doesn't exist or array is empty → Next group is **1**
   - Otherwise → Next group is `len(completed_groups) + 1`
   - If `len(completed_groups) >= total_groups` → **ALL GROUPS COMPLETE** — proceed to `/tts`
3. Use this determined group number for all subsequent steps.

### Step 0: Filter Script for This Group

```bash
python tools/filter_script.py --profile narration --group {N}
```

> **IMPORTANT**: `--group` auto-saves to a group-specific file (`tmp/script_narration_group{N}.json`). It does NOT overwrite `tmp/script_narration.json` (the full-script version created in `run_audio.md` Step 0.3).

### Step 1: Load Context (EVERY session — full load, no shortcuts)

1. Read `reviewlens_narration_agent/SKILL.md` — all rules, constraints, system prompt template, block-type map, number format, and anti-patterns (single source).
2. **If Group 2+**: Load `tmp/scene_handoff.json` — use `last_sentence` for `## Sample Context:` section.

### Step 2: Load Data

1. Read the group-specific filtered script JSON from Step 0 (e.g. `tmp/script_narration_group1.json`).

### Step 3: Write Prompts

Write `tmp/tts_prompt_{block_id}.txt` for all blocks in this group's filtered script.

For each block:
1. Write Director's note (Style, Pacing, Accent) and Scene.
2. Prepare Transcript: number conversion (§4), contraction normalization.
3. **Apply delivery markers** (§3): translate 2–4 key Director's note moments
   into audio tags, ellipses, emphasis, or structural adjustments in Transcript.
4. Self-check: read Transcript aloud. Remove any marker that feels forced.


### Step 4: Quality Audit

Run `python tools/audit_prompt_quality.py` — it scans **ALL** existing `tts_prompt_*.txt` files in `tmp/` (including previous groups) to catch cross-block violations. Checks: Style uniqueness (Jaccard), persona tag compliance, pacing profile, and synthesis preamble. Review flagged items and fix before proceeding.

### Step 5: Generate Handoff

```bash
python tools/scene_handoff_manager.py --group {N}
```

### Step 6: End Session

> **STOP HERE.** You MUST instruct the user exactly what to do next. Do NOT continue to the next group in the same session — this defeats the purpose.
> Follow this format in your final message to the user:
> 
> "Group {N} is complete! To avoid cognitive overload, please open a **new chat session** and simply type the exact command below to continue:"
> ```text
> @[/prompt]
> ```
> *(If `scene_handoff.json` shows `len(completed_groups) >= total_groups`, instruct them to return to the `/run_audio` workflow and proceed to Step 2: Synthesis.)*

---

## Post-All-Groups Audit

After all groups complete:

### 1. Rebuild Handoff (Optional — only if prompts were manually edited post-session)

```bash
python tools/scene_handoff_manager.py --rebuild
```

> [!NOTE]
> Each group session already generates its handoff incrementally via `--group`. This rebuild is only needed if you manually edited prompt files after their group session completed.

### 2. Proceed

- Verify `tmp/prompt_audit_report.json` shows `status: PASS`.
- Proceed to `/tts` (Step 2 in `run_audio.md`).
