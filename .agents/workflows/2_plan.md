---
description: Script Planning session — Unified Screen + Intelligence + Blueprint Designer. Data screening → Strategic analysis → Structural blueprint.
---

# Script Planning Session (Category Comparison)

> **Core Principle**: This session runs Screening, Intelligence, and Blueprint sequentially.
> Order: Data Screening + Hook Analysis (Orchestrator) → Intelligence (sub-agent) → Strategic Blueprint.
> The output `comparison_blueprint.json` is the contract file consumed by `/run_draft`.

## Prerequisites

1. Verify `data/category_candidates.json` exists. If missing, run `/run_data` first.

---

## Phase 1 — Unified Screen + Hook Tactical Brief (Orchestrator)

> **Executor**: The Orchestrator (you), NOT a sub-agent.
> **Input**: `data/category_blueprint.json` (generated below)
> **Outputs**: `data/screen_decisions.json` + `data/hook_tactical_brief.json`
> **Authority**: `hook_design.md` §Contradiction Selection, §Stage 3 Tactics, §Hook Time Budget

1. Run `python tools/filter_category.py --profile blueprint --input data/category_candidates.json` to generate `data/category_blueprint.json`.
2. Read `data/category_blueprint.json` and perform a **unified judgment pass**:

   ### Part A: Data Screening (accept/reject)

   For each cross_product contradiction pair within every theme, evaluate:
   - **Statistical significance**: Is `ratio_gap` meaningful (>5%)? Is `mention_count` reliable (>3)?
   - **Narrative value**: Does this gap provoke a "Why?" from the viewer?
   - **Horizontal framing**: Does it contribute to differentiation, not vertical ranking?

   For each unique_strength candidate:
   - Is `ratio_gap` large enough to be called "unique"?
   - Is `mention_count` too low (≤3), suggesting coincidence?

   **Strategic exception**: A pair with weak statistics MAY be accepted if it has high drama potential for the Hook. Document the override rationale.

   ### Part B: Hook Tactical Brief

   **a) Contradiction Assessment** — Scan all `common_themes[].contradiction_pairs` and `products[].population_gap`. For each candidate, assess drama potential:
   - **Cross-Product**: How large is the `positive_ratio` gap? Is `mention_count` credible?
   - **Within-Product**: How extreme is the sentiment polarity? Do quotes have high `helpful_count`?
   - **Expectation Gap**: How severe is `population_gap`? Is `sold_last_month` high?
   - Rank the top 3 candidates by drama potential. Document rationale.

   **b) Stage 3 Tease Candidates** — From ~10 `common_themes`, select 2-3 tease themes:
   - Prioritize counterintuitive patterns (leader defies price/brand expectations)
   - Prefer themes affecting 3+ products (category-level)
   - Flag which themes should appear early in `selected_themes` ordering

   **c) Scenario Seeds** — Based on the top contradiction, generate 2-3 Relatable Scenario seeds:
   - Must pass the Fiction Scenario prohibition (no "Picture yourself...")
   - Must match one of the 4 positive patterns in `hook_design.md` §Relatable Scenario Guidance
   - Must be derivable from actual user frustrations visible in the data

   **d) Time Budget** — Classify data complexity (simple/complex/dramatic) and assign per-stage seconds per `hook_design.md` §Hook Time Budget.

3. Save screening output as `data/screen_decisions.json`.
   ```json
   {
     "cross_product_decisions": [
       { "theme_name": "...", "product_ids": ["...", "..."], "decision": "accept", "rationale": "..." }
     ],
     "unique_strength_decisions": [
       { "theme_name": "...", "product_id": "...", "decision": "accept", "rationale": "..." }
     ]
   }
   ```
4. Save tactical output as `data/hook_tactical_brief.json`.

## Phase 2 — Screen Merge + Intelligence

1. Run screen merge:
   ```bash
   python tools/merge_screen.py
   ```
   - Output: `data/category_screened.json`

2. Run `python tools/filter_category.py --profile intelligence --input data/category_screened.json`
   - Output: `data/category_intelligence.json`
3. Read `reviewlens_category_intelligence/SKILL.md` and execute the Category Intelligence Agent.
   - Input: `data/category_intelligence.json`
   - Output: `data/intelligence_results.json`
4. Run `python tools/merge_intelligence.py`
   - Output: `data/category_analysis.json`
5. **Analyst's Notebook** (Orchestrator — not a sub-agent):
   Read `data/category_analysis.json`, cross-reference review volume asymmetry, five-star velocity, unique strength distribution, narrative anchors. Write `analyst_notebook[]` array directly into `data/category_analysis.json` with `insight_id`, `title`, `observation`, `data_points`, `narration_hint`.

---

## Phase 3 — Blueprint Designer (Strategic Blueprint)

1. Read `reviewlens_blueprint_designer/SKILL.md` and absorb all rules.
2. Load authority references (section scoping is defined in SKILL.md's authority table):
   - `.agents/rules/narrative_standards.md`
   - `.agents/rules/hook_design.md`
3. Read `data/category_blueprint.json` (already generated in Phase 1).
4. Read `data/hook_tactical_brief.json` — the Orchestrator's data-driven tactical recommendations.
5. Execute strategic decisions:
   - `video_question` design
   - Hook Contradiction selection — **start from the tactical brief's ranked candidates**, override only with documented rationale
   - Theme Curation (reduce 10 common_themes to 4-5)
   - Standout Mapping
   - Verdict Strategy formulation
6. Save as `data/comparison_blueprint.json`
7. Self-Check (Required Pre-Output Verification)
    1. ☐ Does `video_question` contain zero product names, brand names, or category names?
    2. ☐ Is `selected_hook_contradiction.selection_rationale` recorded with specific detail?
    3. ☐ If overriding the tactical brief's `recommended_pick`, is the override rationale documented?
    4. ☐ Is the `selected_themes` count within the dynamic cap enforced by `build_outline.py`?
    5. ☐ Do all `selected_themes` have both `narrative_directive` and `selection_rationale`?
    6. ☐ Does each `narrative_directive` instruct a narration approach matching its `category_pattern_type`?
    7. ☐ Is the theme that serves as the Hook contradiction's payoff included in `selected_themes`?
    8. ☐ Are all entries in `excluded_themes` accompanied by qualitative exclusion justification?
    9. ☐ Are all buy_if/skip_if themes in `verdict_sources` included in `selected_themes`?
    10. ☐ Are there zero vertical ranking expressions ("1st", "last place", "the best") anywhere?
    11. ☐ Does every `selected_themes[]` entry have a valid `narrative_weight` (`"heavy"` | `"standard"` | `"light"`)?
    12. ☐ Is `"light"` never assigned to a `differentiator` or `mixed` theme?

---

## Completion

1. Confirm `data/comparison_blueprint.json` has been saved successfully.
2. Notify the user: **run `/run_draft` to continue with outline assembly and narration drafting.** This can be run in the same session or a new one.
