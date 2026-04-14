---
description: Visual Media Step 2 — Generation. AI media (image/video) generation for missing scenes.
---

# /gen

> **Tool-Only / Agent Collab**: Execute generation tools.

1. Based on the empty slot requirements or generation prompts left by the B-roll Agent, execute tools like `python tools/gen_media.py` to procure missing images.
2. Finalize and assemble `data/script_with_media.json`.
3. Completion of this step marks the end of the entire pipeline, indicating that the payload is fully ready for rendering.
