---
trigger: manual
---

# Orchestrator Conduct

## Agent Autonomy

Agents own qualitative judgment: theme selection, narrative framing,
tone calibration, and creative direction.
Python scripts act solely as dumb, deterministic executors; all structural
judgment criteria and constraints must be injected from the centralized JSON contract.

## Subagent Delegation

- Trust the SKILL.md — do NOT repeat its rules in the Task prompt.
  Pass only data context (file paths, parameters).
- One agent = one role. If a step mixes judgment and verification,
  propose splitting before executing.
- If a workflow step overloads an agent, flag it to the User first.
