---
description: Script Writing session — Blueprint Designer + Structure Engineer + Writer. Strategic framing → Structural pacing → Script drafting.
---

# Script Writing Session (Category Comparison)

> **Core Principle**: This session runs the Blueprint Designer, Structure Engineer, and Writer agents sequentially.
> Order: Strategic Decisions (What) → Structural Decisions (How) → Narration Drafting.
> The output is evaluated in a separate Review session (`/run_review`).

## Prerequisites

1. Verify `data/category_analysis.json` exists. If missing, run `/run_data` first.

## Blueprint Designer — Strategic Blueprint (`/blueprint`)

1. Read `reviewlens_blueprint_designer/SKILL.md` and absorb all rules.
2. Run `python tools/filter_category.py --profile blueprint` to generate `data/category_blueprint.json`.
3. Read `data/category_blueprint.json` — lightweight category comparative analysis data.
4. Execute strategic decisions:
   - `video_question` design
   - Hook Contradiction selection (from `contradiction_pairs`)
   - Theme Curation (reduce 10 common_themes to 4-5)
   - Standout Mapping
   - Verdict Strategy formulation
5. Save as `data/comparison_blueprint.json` (Schema: `reviewlens_blueprint_designer/references/output_schema.md`).

5. **Video Question Checkpoint**: Validate that the `video_question` passes the Product-Name-Free Sentence Test. If it contains a product name → revise and proceed.
6. **Hook Contradiction Checkpoint**: Verify that `selection_rationale` is specific and clear.

## Structure Engineer — Structural Outline (`/structure`)

1. Read `reviewlens_structure_engineer/SKILL.md` and absorb all rules.
2. Run `python tools/filter_category.py --profile structure_engineer` to generate `data/category_structure_engineer.json`.
3. Read `data/comparison_blueprint.json` — Blueprint's strategic decisions.
4. Read `data/category_structure_engineer.json` — Filtered read-only reference (selected themes only).
5. Execute structural decisions:
   - Scene Sequence Assembly (Hook → Overview → ThemeComp → Standout → Verdict)
   - Block Allocation + pacing profile assignment
   - Teaser/Payoff Design
   - Runtime Guard (enforce dynamic block caps)
6. Save as `data/comparison_outline.json` (Schema: `reviewlens_structure_engineer/references/output_schema.md`).

6. **Runtime Checkpoint**: Verify total block count is within the cap set in `scene_visual_pacing.md` §7.
7. **Pacing Distribution Checkpoint**: Verify the distribution of breathe/standard/dense values is balanced.

## Writer Agent — Draft Script (`/draft`) (3-Pass & Veto Loop)

> **Veto Loop Orchestrator Protocol**:
> 1. If the Writer outputs a JSON containing the `"structural_rejection"` root key → **immediately halt downstream handover**.
> 2. Evaluate the `veto_scope` parameter inside the rejection object:
>    - `"block_count"` → **Re-run the Structure Engineer only**, preserving the Blueprint's strategic baseline.
>    - `"theme_selection"` → **Re-run the Blueprint Designer**, as a fundamental theme replacement is required.
> 3. After the re-run agent produces the modified payload, restart the Writer.
> 4. **Maximum 2 Veto cycles**. On the 2nd Veto, forcibly approve the final outline and proceed, recording `"veto_forced_approval": true` in `draft_script.json`.

1. Read `reviewlens_writer_agent/SKILL.md` and absorb all rules.
2. Read `data/comparison_outline.json` — the structural baseline.
3. Run `python tools/filter_category.py --profile writer` to generate `data/category_writer.json`.
4. Read `data/category_writer.json` — the customized empirical data source.
5. Execute the **3-Pass Generation**:
   - **Pass 1 (Skeleton)**: Draft objective, data-driven claims only. If evidence is lacking, trigger a **Veto** (specifying `veto_scope`).
   - **Pass 2 (Muscle)**: Rewrite the Skeleton embodying the "Consumer Data Detective" persona.
   - **Pass 3 (Skin)**: Insert Visual Handoff phrases and optimize word phonetics/pacing.
6. Save the final payload to `data/draft_script.json`.

## Completion

1. Notify the user of successful completion and mandate running `/run_review` **in a brand new session**.
