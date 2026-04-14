---
description: Script Writing Step 1 — Blueprint Designer. Establishes strategy and Video Question.
---

# /blueprint

> **Agent Skill**: The Blueprint Designer (`reviewlens_blueprint_designer`) owns this step.

1. Read and absorb the rules defined in `reviewlens_blueprint_designer/SKILL.md`.
2. Run `python tools/filter_category.py --profile blueprint` to generate the lightweight `data/category_blueprint.json`.
3. Reference the filtered dataset in `data/category_blueprint.json` (NOT the full `data/category_analysis.json`).
4. Execute all strategic baseline decisions (Video Question, Hook Contradiction selection, Theme Curation, Standout Mapping, Verdict Strategy) and save the payload to `data/comparison_blueprint.json`.
5. Upon completion, Notify the user of successful completion and mandate running `/structure`.
