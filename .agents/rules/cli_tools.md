---
trigger: manual
---

# CLI Tools Reference

> Detailed flags and arguments are defined in each stage's command file. Model IDs are defined in `tools/config.py`.

## Data Absorption

| Tool | Purpose |
| ---- | ------- |
| `phase0_loop_runner.py` | Data Absorption Phase 0 extraction loop orchestrator |
| `absa.py` | Aspect-Based Sentiment Analysis on reviews |
| `data_bridge.py` | Consolidate analysis results into unified JSON + summary (produces `summary.json` theme list) |
| `cross_product_analyzer.py` | Cross-product comparative analysis and matching |
| `filter_category.py` | Core helper: Generates agent-specific filtered data files based on `--profile` |
| `filter_data.py` | Helper: filter reviews by specific theme |
| `check_quotes.py` | Helper: diagnose quote quality in summary.json |
| `merge_screen.py` | Merges Orchestrator's screening decisions into category profile |
| `merge_intelligence.py` | Merges Category Analyst qualitative insights into category profile |

## Script Writing + Review

| Tool | Purpose |
| ---- | ------- |
| `build_outline.py` | Script Writing: Deterministic structure outline generator (replaces Structure Engineer agent) |
| `filter_script.py` | Core helper: Filters draft script for specific agent/group review workflows |
| `script_auditor.py` | Script Review: Deterministic mechanical checks (banned words, scene balance, data anchoring, drama patterns) |
| `prepare_script.py` | Script Review Step 2.5: Converts `draft_script.json` → `script_output.json` (critique_log cleanup + root field normalization) |
| `extract_monologue.py` | Script Review Step 3: Extracts narration text from `script_output.json` into `tmp/head_writer_input.txt` continuous monologue + `tmp/head_writer_block_map.json` block order mapping |
| `merge_monologue.py` | Script Review Step 3: Merges Head Writer's polished monologue (`tmp/head_writer_output.txt`) back into `data/script_output.json` |
| `generate_briefing.py` | Script Review Step 3: Converts `script_auditor.py` CHECK 10 repetition flags into `tmp/head_writer_briefing.txt` text briefing with paragraph-number locations |
| `validate_script.py` | Script Review Step 4: Schema integrity validation of `script_output.json` (Audio Production entry gate) |

## Audio Production

| Tool | Purpose |
| ---- | ------- |
| `audit_prompt_quality.py` | TTS prompt quality audit: cross-scene anti-pattern detection (Delivery uniqueness, persona tag compliance, pacing profile, synthesis preamble) |
| `tts_synthesize.py` | Gemini TTS API call, produces WAV |
| `audio_evaluator.py` | Multimodal audio QA — listens to WAV directly, checks tag misfire + quality, returns `{"is_valid", "reason"}` |
| `word_align.py` | stable-ts(Whisper) word-level forced alignment |

## Visual Media

| Tool | Purpose |
| ---- | ------- |
| `media_indexer.py` | Indexes generated and existing media files for accurate matching |
| `filter_media.py` | Filters candidate media clips based on scene rules and requirements |
| `broll_mapper.py` | Maps specific B-roll queries and types to precise narration timestamps |
| `merge_block_timestamps.py` | Integrates narration timestamps, visualization data, and metadata into individual block JSON chunks |
| `gen_media.py` | Invokes AI image/video generators for missing media segments |
| `scene_handoff_manager.py` | Manages data and state handoff boundaries between contiguous scenes |

## Automation & Utilities

| Tool | Purpose |
| ---- | ------- |
| `cleanup_session.py` | Cleans up temporary files and session state for fresh pipeline runs |
| `run_full_pipeline.py` | Audio Production (TTS + alignment) → Visual Media mapping automated |
| `runner_phase2_tts.py` | Audio Production standalone automation (direct import) |
