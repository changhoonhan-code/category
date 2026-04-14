---
description: Audio Step 1 — Prompt. Write Director's Notes and vocal direction prompts per block (Hybrid 4-Group Execution).
---

# /prompt

> **Agent Skill**: The Narration Agent (`reviewlens_narration_agent`) owns this step.
> **Execution Model**: Hybrid 4-Group — each group runs in a **SEPARATE fresh session** to prevent cognitive overload.
> This is not optional optimization; it is the primary quality defense mechanism.

## Why 4 Groups?

A single session writing 21+ TTS prompts sequentially suffers from **Creative Fatigue**:
- Blocks 1–5: Rules fully loaded, diverse patterns → high quality
- Blocks 6–12: Rules fading, patterns repeating → medium quality
- Blocks 13–21: Self-output lock-in, rules partially forgotten → **lowest quality on the most important blocks (Verdict)**

Each group session loads ALL skill files fresh — the repeated context cost is not waste, it is **rule re-recognition insurance**.

## Group Definitions

| Group | Scenes | Est. Blocks | Filter command |
|-------|--------|-------------|----------------|
| **1 (Opening)** | Hook + Rating Overview | 4 | `python tools/filter_script.py --profile narration --group 1` |
| **2a (Theme Front)** | First 3 theme comparison scenes | 7–9 | `python tools/filter_script.py --profile narration --group 2a` |
| **2b (Theme Back)** | Remaining theme comparison scenes | 4–6 | `python tools/filter_script.py --profile narration --group 2b` |
| **3 (Closing)** | Standout + Verdict | 5–7 | `python tools/filter_script.py --profile narration --group 3` |

> [!NOTE]
> `--group` automatically detects scene_ids from `script_output.json` and sets the output path to `tmp/script_narration_group{id}.json`. Manual `--scenes` specification is no longer needed.

> [!IMPORTANT]
> Terminal encoding artifacts: Em-dashes (`—`) and other Unicode characters may appear as `??` in PowerShell console output. This is a shell rendering issue, not a data corruption problem. Always verify data content via `view_file` on the output JSON, not via console STDOUT.

## Per-Group Execution Protocol

Repeat the following for each group in order: **1 → 2a → 2b → 3**

### Step -1: Auto-Detect Next Group (Do this FIRST)

When invoked via `@[/prompt]` without a specific group argument, you MUST automatically determine the next group to process:
1. Use `view_file` on `tmp/scene_handoff.json`.
2. Look at the `"completed_groups"` array:
   - If file doesn't exist or array is empty → Next group is **1**
   - If `["1"]` → Next group is **2a**
   - If `["1", "2a"]` → Next group is **2b**
   - If `["1", "2a", "2b"]` → Next group is **3**
3. Use this determined group as `{group_id}` for all subsequent steps.

### Step 0: Filter Script for This Group

> **IMPORTANT**: The `--group` option automatically saves to a group-specific file (`tmp/script_narration_group{id}.json`). It does NOT overwrite `tmp/script_narration.json` (the full-script version created in `run_audio.md` Step 0.3 — needed by `scene_handoff_manager.py` for block ordering).

```bash
python tools/filter_script.py --profile narration --group {group_id}
```

### Step 1: Load Context (EVERY session — full load, no shortcuts)

1. Read `reviewlens_narration_agent/SKILL.md` — rules, constraints, anti-patterns.
2. Read `reviewlens_narration_agent/references/directing_reference.md` — technique catalog, archetypes, block-type map.
3. Read `reviewlens_narration_agent/references/archetypes_examples.md` — all 7 archetype delivery examples in full.
4. Read `reviewlens_narration_agent/references/category_comparison_examples.md` — multi-product directing examples.
5. **If Group 2a, 2b, or 3**: Load `tmp/scene_handoff.json` — use `last_sentence` for Context field, check each entry's **`delivery` field** in `opening_brackets_used` for Delivery uniqueness, check `archetype_sequence` for 3+ repetition risk.

### Step 2: Load Data

1. Read the group-specific filtered script JSON from Step 0 (e.g. `tmp/script_narration_group1.json`).
2. Read `tmp/visual_pause_map.json` (generated in `run_audio.md` Step 0.4).

### Step 3: Write Prompts

Write `tmp/tts_prompt_{block_id}.txt` for all blocks in this group's filtered script.

### Step 4: Self-Check (SKILL.md §2 Step 2)

Direction Density Audit for this group's blocks. Including cross-group uniqueness check against `scene_handoff.json`.

### Step 5: Generate Handoff

```bash
python tools/scene_handoff_manager.py --group {group_id}
```

### Step 6: End Session

> **STOP HERE.** You MUST instruct the user exactly what to do next. Do NOT continue to the next group in the same session — this defeats the purpose.
> Follow this format in your final message to the user:
> 
> "Group {current_group} is complete! To avoid cognitive overload, please open a **new chat session** and simply type the exact command below to continue:"
> ```text
> @[/prompt]
> ```
> *(If the current group is 3, instruct them to return to the `/run_audio` workflow and proceed to Step 2: Synthesis).*

---

## Post-All-Groups Audit

After all 4 groups complete (Groups 1, 2a, 2b, 3):

### 1. Rebuild Handoff (최신 프롬프트 동기화)

```bash
python tools/scene_handoff_manager.py --rebuild
```

### 2. Run Audit

```bash
python tools/audit_opening_brackets.py
```

- If `status: PASS` → proceed to `/tts` (Step 2 in `run_audio.md`).
- If `status: NEEDS_REVISION` → read the violations, revise the flagged `tts_prompt_{block_id}.txt` files, then **re-run both rebuild and audit**:

```bash
python tools/scene_handoff_manager.py --rebuild
python tools/audit_opening_brackets.py
```

Repeat until `status: PASS`.
