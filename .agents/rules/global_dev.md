---
trigger: manual
---

1. **Developer Chat & Artifacts (Korean)**: The conversational dialogue between the User and the Orchestrator (Main Agent) is strictly in Korean with short sentence to facilitate rapid brainstorming and architectural design.

2. **System Production (English Only)**: Despite the Korean developer chat, the ultimate goal is producing content for a native Western audience (US/UK/CA/AU). Therefore, **ALL agent-facing documents** (SKILL.md, rules, workflows, schemas, JSON field values) and **ALL generated outputs** MUST be written entirely in English. Korean in any project file or JSON output is a critical violation.

3. **Project Purpose**: Script production for search-oriented/evergreen video content targeted at Western English-speaking audiences.
   - **Source Data**: Analyzed data curated from reviews of 3-5 top products in Amazon best-selling categories.
   - **Script Division of Labor**: Granular data and numbers are handled visually by on-screen graphics; the spoken dialogue focuses on data interpretation, analytical insights, and narrative flow.
   - **Narration Quality**: While generated via TTS, the audio must perfectly replicate natural human breathing, conversational pacing, and intricate vocal details.

4. **File Encoding Requirement**: Whenever an agent creates or modifies text files (especially prompt files or JSONs), it MUST ensure the file is saved with `utf-8` encoding to prevent Unicode character corruption (such as em-dashes `—` turning into `??`).