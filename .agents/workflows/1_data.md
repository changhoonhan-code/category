---
description: Data Extraction & Analysis tools only - no agent skills required
---

# Data Extraction & Analysis

This workflow processes raw data from the `products/` directory using analysis tools to generate structured data in the `data/` directory.

## CLI Tools

> **Tool-Only Step**: This step runs as a pure Python automation script and does not require agent skills.

| Tool | Purpose |
| ---- | ------- |
| `absa.py` | Aspect-Based Sentiment Analysis on reviews |
| `data_bridge.py` | Consolidate analysis results into unified JSON + summary |
| `cross_product_analyzer.py` | Generate category intelligence dataset |

## Prerequisite Check

Verify the existence of the multi-product directory structure:

- `products/product_a/`
- `products/product_b/`
- `products/product_c/`

> [!WARNING]
> If the `products/` directory is empty or missing, output a **warning message** to the user.

## Execution Procedure

### Data Extraction

1. Run the batch extraction script: `python tools/phase0_loop_runner.py`
2. This script loops through each product in `products/`, executing:
   - `absa.py` and `data_bridge.py` to generate `data/products/<product_id>/summary.json`.

### Cross-Product Match

1. Execute the `python tools/cross_product_analyzer.py` tool.
2. The tool automatically generates `data/category_candidates.json`.

## Completion Criteria

- `data/category_candidates.json` successfully saved.
- Inform the user that the next step is `/2_plan`.
