---
description: Data Step 2 — Analyze. Cross-product loading and comparative matching.
---

# /analyze

> **Tool-Only Step**: This step runs as a pure Python automation script and does not require agent skills.

1. Execute the `python tools/cross_product_analyzer.py` tool (performs the Load -> Match sequence).
2. The tool automatically generates `data/category_analysis.json`, which is the final merged comparative dataset for the category.
3. Upon completion, execute `/blueprint` to begin the Script Writing stage.

