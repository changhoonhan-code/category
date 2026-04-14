---
description: Audio Step 2 — TTS. Audio synthesis engine execution and QA.
---

# /tts

> **Tool-Only Step**: This step is executed via a Python script.

1. In the console, execute `python tools/runner_phase2_tts.py` (or the designated synthesis tool).
2. Based on the prompts, actual audio files will be generated in `data/narration_audio/`.
3. Upon completion, execute the next step: `/sync`.
