---
description: Data Step 1 — Extract. Single-product ABSA extraction and Bridge.
---

# /extract

> **Tool-Only Step**: This step runs as a pure Python automation script and does not require agent skills.

1. Run the batch extraction script: `python tools/phase0_loop_runner.py`
2. This script loops through each product in `products/`, executing `absa.py` and `data_bridge.py` to generate `data/products/<product_id>/summary.json`.
3. Upon completion, execute the next step: `/analyze`.
