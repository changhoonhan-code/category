---
description: Automated Planning and Production for ReviewLens Product Reviews (Showrunner Workflow)
---
# ReviewLens: Showrunner Pipeline

This workflow is the single entry point for a Showrunner (LLM Agent) to curate the production data pipeline—from raw review data in `products/` to a fully prepared media package ready for external rendering—using Python CLI tools in `tools/` as modular assistants.

> **Core Principle**: You are the **Single Intelligence (Showrunner)** tasked with writing the script, self-critiquing, directing vocal performances, and mapping all media assets. This pipeline ends at **Visual Media** (`/run_media`), producing a complete media package that is handed off to an external Remotion rendering project.

### Strict Showrunner Rules

- **Maintain Context**: Never forget a shocking statistic found during Data Absorption when drafting Director's Notes in Audio Production.
- **Be an Active Director**: You are not a simple API router. If the results of `broll_mapper.py` are unsatisfactory, use a `browser_subagent` to search for more compelling evidence.
- **Continuous Workflow**: Automatically proceed to the next stage — **except at the mandatory session break after Script Writing** (see below).
- **Investigation Framing**: Every video is a consumer data investigation. Before proceeding past Script Writing, verify the `video_question` passes the Product-Name-Free Sentence Test (`.agents/rules/brand_identity.md` §1). If it contains a product name → halt and revise.

---

## Execution

### Session 1 — Data and Writing

Run in order:

| Stage | Command | Completion Marker |
| --- | --- | --- |
| Data Absorption | `/run_data` | `data/category_analysis.json` |
| Script Writing | `/run_write` | `data/draft_script.json` |

### Veto Intercept Check

Before signaling completion of Script Writing, check the output or `draft_script.json`. If it contains a `"structural_rejection"` root key, the Writer triggered a Veto. You must immediately execute the **Veto Loop** logic (re-run Blueprint Designer or Structure Engineer) as defined in `/run_write.md` instead of breaking the session. Only break the session when a successful draft is fully rendered.

### MANDATORY SESSION BREAK

After successful Script Writing completes, **stop immediately** and output this message to the user:

```text
Script Writing complete. draft_script.json has been saved.

⚠️  START A NEW CONVERSATION and run /run_review
     Running the review in this same session causes confirmation bias
     and defeats the purpose of the 3-agent + 2-tool relay + Head Writer polish.
```

**Do NOT proceed to Script Review in this session under any circumstances.**

### Session 2 — Review, Audio, and Media

After the user starts a fresh conversation and runs `/run_review`, the pipeline continues automatically:

| Stage | Command | Completion Marker |
| --- | --- | --- |
| Script Review | `/run_review` | `data/script_output.json` |
| Audio Production | `/run_audio` | `data/narration_audio/manifest.json` |
| Visual Media | `/run_media` | `data/block_visual_mapping.json` (Mapping Complete) |

---

## Resumption Guide

If work is interrupted, check markers in order and resume from the stage after the last found marker:

| Stage | Completion Marker | Rollback |
| --- | --- | --- |
| Data Absorption | `data/category_analysis.json` | Delete `data/products/`, `data/category_analysis.json` |
| Script Writing + Review | `data/script_output.json` | Delete `data/comparison_outline.json`, `data/draft_script.json`, `data/script_output.json` |
| Audio Production | `data/narration_audio/manifest.json` | Delete `data/narration_audio/`, `tmp/` |
| Visual Media (Mapping) | `data/block_visual_mapping.json` | Delete `data/block_visual_mapping.json`, `data/media_candidates.json` |
| Visual Media (Generation) | `data/script_with_media.json` | Delete `data/script_with_media.json`, `data/generated_media/` |
