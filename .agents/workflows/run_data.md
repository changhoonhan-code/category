---
description: ReviewLens Data Absorption — /extract → /analyze
---

# Data Absorption

This workflow processes raw data from the `products/` directory using analysis tools to generate structured data in the `data/` directory.

## CLI Tools

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

### Data Extraction (`/extract`)

```bash
python tools/phase0_loop_runner.py
```

### Cross-Product Match (`/analyze`)

```bash
python tools/cross_product_analyzer.py
```

## Showrunner Actions

- **Directly read and synthesize** `data/category_analysis.json`.
- Extract key comparative contradictions and thematic clusters.
- Plan the visual **Hook** and the overall narrative structure for the category.

## Completion Criteria

- `data/category_analysis.json` successfully saved.
