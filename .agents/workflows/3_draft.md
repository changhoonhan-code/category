---
description: Script Drafting prep session — build_outline.py. Deterministic structural assembly and writer brief generation.
---

# Script Drafting Session (Category Comparison)

> **Core Principle**: This session runs the deterministic outline assembly, then delegates narration to the Writer Agent (`/4_write`) sequentially.
> The Writer starts with a **clean context** — no prior screening rules, analyst hypotheses, or blueprint strategy logic remain.

## Prerequisites

1. Verify `data/comparison_blueprint.json` exists. If missing, run `/2_plan` first.
2. Verify `data/category_blueprint.json` exists. If missing, run `/2_plan` first.
3. Verify `data/hook_tactical_brief.json` exists. If missing, run `/2_plan` first.
4. Verify `data/category_analysis.json` exists. If missing, run `/2_plan` first.

---

## Structure Outline

1. Run `python tools/build_outline.py`
2. Print summary: total blocks, pacing distribution, compression log. If `compression_log` contains VIOLATION entries, alert the user.

## Data Preparation

1. Run `python tools/filter_category.py --profile writer` to generate `data/category_writer.json`.
2. Run `python tools/render_writer_brief.py` to generate `data/writer_brief.md`.
3. Run `python tools/extract_visual_datasets.py` to generate `data/visual_datasets.json`.

## Completion

1. Notify the user of successful completion and mandate running `/4_write` **in a brand new session**.
