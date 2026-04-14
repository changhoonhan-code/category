---
trigger: always_on
---

# ReviewLens Global Rules (Absolute Authority)

> 🚨 **THIS IS THE ABSOLUTE HIGHEST-LEVEL AUTHORITY FOR THIS PROJECT.**
> All skills, commands, and agents MUST comply with the rules defined in this file and its linked rule files.
> In any conflict between these rules and any SKILL.md or command file, **these rules win.**

## Project Identity

ReviewLens is an AI showrunner pipeline that analyzes Amazon review data to automatically produce **narration scripts, audio, and B-roll asset packages** for data-driven **category comparison** videos.

The pipeline ingests **3–5 bestselling products** within a single Amazon category, performs cross-product comparative analysis (shared themes, contradiction pairs, unique differentiators), and generates a complete video production package — positioning the channel as a **Category Intelligence Analyst**, not a traditional product reviewer.

> **🛑 Target Language & Audience:** All generated content (scripts, metadata, internal reasoning) **MUST be entirely in English**, specifically targeting a native English-speaking audience.

### Core Principles

- **Horizontal Differentiation:** Absolute prohibition of vertical ranking (e.g., 1st, 2nd, worst). Products must be categorized and matched to their optimal use cases and specific user environments.
- **Data-Driven Journalism:** Storytelling must be rooted entirely in facts, contradictions, and patterns empirically extracted from review data—strictly zero subjective opinions.
- **Contradiction-Driven Hooks:** Captivate the audience by exposing counter-intuitive data contradictions, leveraging both within-product anomalies and cross-product discrepancies.
- **Category Intelligence:** Elevate the narrative from isolated product reviews to structural market analysis, illuminating the category's technological maturity, structural limitations, and overarching purchasing strategies.

---

## Pipeline Stages

| Stage | Description | Orchestrator | Granular Steps |
| ----- | ----------- | ------------ | -------------- |
| Data Absorption | ABSA extraction (×N products) + Cross-Product Analysis | `/run_data` | `/extract` → `/analyze` |
| Script Writing | Strategic design → Structural optimization → Narration draft | `/run_write` | `/blueprint` → `/structure` → `/draft` |
| Script Review | Data validation → Tone/BGM → Script assembly → Creative polish → Final validation | `/run_review` | `/check` → `/tone` → `prepare_script.py` → `/polish` → `validate_script.py` |
| Audio Production | TTS narration + word-level timestamp sync | `/run_audio` | `/prompt` → `/tts` → `/sync` |
| Visual Media | B-roll asset mapping + AI media generation | `/run_media` | `/broll` → `/gen` |

---

## Agent Architecture

The pipeline uses an **8-agent relay** for multi-product category comparison. Each agent **modifies only its owned fields** and must not touch others.

| Agent | Skill | Owns | Must Not Touch |
| ----- | ----- | ---- | -------------- |
| **Blueprint Designer** | `reviewlens_blueprint_designer/` | video_question, theme selection, hook contradiction, narrative_directive, standout mapping, verdict strategy | Block count, pacing, scene order, all content fields |
| **Structure Engineer** | `reviewlens_structure_engineer/` | Scene order, block_ids, block_pacing, teaser_payoff_map, runtime cap, notes (Structure section) | Theme selection, narration, evidence_quotes, bgm_mood |
| **Writer** | `reviewlens_writer_agent/` | narration, evidence_quotes | Blueprint/Structure decisions, bgm_mood |
| **Data Validator** | `reviewlens_data_validator/` | Numbers in narration, evidence_quotes metadata | Tone, bgm_mood, scene order |
| **Tone Editor** | `reviewlens_tone_editor/` | bgm_mood (primary assignment), directing_hint, narration tone/phrasing, is_humorous | evidence_quotes, numbers |
| **Head Writer** | `reviewlens_head_writer/` | narration (creative polish: voice consistency, dead weight, killer lines, echoes) | Numbers, evidence_quotes, bgm_mood, scene structure |
| **Narration Agent** | `reviewlens_narration_agent/` | TTS prompts (Director's Notes) | Script content, directing_hint (read-only) |
| **B-roll Agent** | `reviewlens_broll_agent/` | broll_asset mapping, AI generation prompts | Narration, script structure |

---

## Rule Files

> The full Brand & Content rules and CLI tool reference are split by domain below. **Each file has the same authority as this document.** SKILL.md files reference these directly.
> Output schemas are co-located with each agent skill in `references/output_schema.md`.

| Domain | File |
| ------ | ---- |
| Brand & Identity | `.agents/rules/brand_identity.md` |
| Prohibitions | `.agents/rules/prohibitions.md` |
| Evidence & Integrity | `.agents/rules/evidence_integrity.md` |
| Scene, Visual & Pacing | `.agents/rules/scene_visual_pacing.md` |
| CLI Tools | `.agents/rules/cli_tools.md` |
| Pivot Plan & History | `.agents/rules/pivot_plan.md` |
