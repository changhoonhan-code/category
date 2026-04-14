---
trigger: manual
---

# CLI Tools Reference

> Detailed flags and arguments are defined in each stage's command file. Model IDs are defined in `tools/config.py`.

## Data Absorption

| Tool | Purpose |
| ---- | ------- |
| `absa.py` | Aspect-Based Sentiment Analysis on reviews |
| `data_bridge.py` | Consolidate analysis results into unified JSON + summary (produces `summary.json` theme list) |
| `filter_data.py` | Helper: filter reviews by specific theme |
| `check_quotes.py` | Helper: diagnose quote quality in summary.json |

## Script Writing + Review

| Tool | Purpose |
| ---- | ------- |
| `prepare_script.py` | Script Review Step 2.5: Converts `draft_script.json` → `script_output.json` (critique_log cleanup + root field normalization) |
| `validate_script.py` | Script Review Step 4: Schema integrity validation of `script_output.json` (Audio Production entry gate) |

## Audio Production

| Tool | Purpose |
| ---- | ------- |
| `tts_synthesize.py` | Gemini TTS API call, produces WAV |
| `audio_evaluator.py` | Multimodal audio QA — listens to WAV directly, checks tag misfire + quality, returns `{"is_valid", "reason"}` |
| `word_align.py` | Gemini STT word-level timestamp alignment |

## Visual Media

| Tool | Purpose |
| ---- | ------- |
| `media_indexer.py` | Visual Media pre-flight: Gemini Vision analysis + indexing. Injects `--themes` and `--script` flags to tag `related_themes[]` and `matching_block_ids[]` per asset |
| `filter_media.py` | Per-block candidate pre-filtering (prioritizes by `matching_block_ids` narration match, then `related_themes`) |
| `broll_mapper.py` | `--mapping` mode: inject selections from `block_visual_mapping.json`. Legacy: auto-map via keyword/LLM. |
| `gen_media.py` | Imagen/Veo AI media generation |

## Automation Runners

| Tool | Purpose |
| ---- | ------- |
| `run_full_pipeline.py` | Audio Production (TTS + alignment) → Visual Media mapping automated |
| `runner_phase2_tts.py` | Audio Production standalone automation (direct import) |
