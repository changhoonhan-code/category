---
description: Writer Agent — free-form draft, veto check, and Orchestrator decomposition into draft_script.json.
---

# Writer Agent (Draft Script)

## Prerequisites

1. Verify `data/writer_brief.md` exists. If missing, run the data preparation phase in `/3_draft` first.

---

## Phase 1 — Creative Pass

> [!CAUTION]
> **Read ONLY the skill and `data/writer_brief.md`. Do NOT open any other file — no blueprint, no category_writer, nothing. Opening anything else contaminates context and forces a restart.**

1. Read `.agents/skills/reviewlens_writer_agent/SKILL.md` — absorb the persona and rules.
2. Read `data/writer_brief.md` — the unified Metric Dossier. **Stop reading files here.**
3. Write a single, continuous monologue driven purely by `data/writer_brief.md`. Save to `data/raw_draft.md`. The draft must flow from insight to insight. Do NOT count caps, do NOT self-audit during writing. Trust the voice.
4. **Veto Check**: If the draft cannot be completed, state the reason at the top of `data/raw_draft.md` and notify the user. User decides whether to re-run `/3_draft` or the outline phase.

---

## Phase 2 — Mechanical Audit

> All counting is offloaded to a Python script. The Writer does NOT count manually — the script is the single source of truth.

// turbo
1. Run the cap auditor:
   ```
   python tools/audit_caps.py data/raw_draft.md
   ```
2. If the verdict is **PASS** → proceed to Phase 3.
3. If the verdict is **FAIL** → read the violation report and fix **only the flagged items** in `data/raw_draft.md`. Do not rewrite sections that passed. Then re-run the script:
   ```
   python tools/audit_caps.py data/raw_draft.md
   ```
4. Repeat step 3 until the script returns **PASS** (exit code 0). Maximum 3 iterations — if still failing after 3 rounds, report remaining violations to the user.

> [!IMPORTANT]
> Do NOT manually count caps or mentally estimate frequencies. The script output is the only authority. When fixing violations, make minimal, targeted edits — do not restructure passing sections, which risks introducing new violations.

---

## Phase 3 — Judgment Audit

> These checks require **qualitative judgment** that `audit_caps.py` cannot perform. Items already covered mechanically in Phase 2 are excluded.

### Tone Consistency

- [ ] No sentence reads like a **legal brief or courtroom closing** (overly formal compound clauses).
- [ ] No sentence reads like a **documentary narrator** (literary/essayistic register shift).
- [ ] The persona voice is indistinguishable from start to finish — same friend, same bar, same conversation.

### Review Source Framing

- [ ] **Mode Balance**: At least **1 in 4 evidence sentences** uses Review-grounded delivery (Mode 5) or Collective Source Framing. The narrator must read as a review analyst, not a product tester.
- [ ] **Claim Type Distinction**: Review-reported experiences include a source signal. Official specs are stated as specs. Causal hypotheses are hedged. No review-derived claim is presented as narrator's own direct observation.

### Methodology Disclosure

- [ ] The **intro_credibility** section explicitly discloses the recent-window methodology: the recent window = the period during which the most recent 100 five-star ratings were submitted, and this window varies per product.
- [ ] The disclosure is woven naturally into the narration (not a footnote or disclaimer tone). Example vehicle: mention the actual window lengths from the Product Reference table to show the variance.

### Verdict Structure

- [ ] The entire Verdict section does not exceed **15% of total script word count**.
- [ ] Each product gets exactly **one paragraph**. No product gets a second paragraph for caveats or feature lists.
- [ ] Each product's recommendation uses a **different rhetorical shape** — different sentence structure, not just different labeling. Do NOT use [Product] → [Strength] → [But/caveat] for more than one product.
- [ ] The category-level closing statement is **≤ 2 sentences**.
- [ ] **No unconditional winner declaration**. Per-metric verdicts are allowed; an overall "X wins" is prohibited.

### Evidence Integrity

- [ ] **Two-Number Rule**: No single sentence contains more than two specific data points. No two data-heavy sentences appear back-to-back without a buffer.
- [ ] **Inference Hedging**: Causal explanations use conversational hedged framing ("It looks like…", "Best guess?", "What's probably happening is…"). Banned hedges are caught by Phase 2; this check verifies causal *hypotheses* are properly hedged in context.

### Voice & Structure

- [ ] **Absorption Ban**: No reviewer's personal anecdote is adopted as the narrator's own first-person experience.
- [ ] **Brand-to-Model Rule**: Full brand + model name used exactly once per product. All subsequent references use model name only.
- [ ] **Chapter Variety**: No two consecutive metric chapters use the same structural approach or the same product ordering.

### Fix Protocol

1. If any check above fails, fix the violating section in `data/raw_draft.md`.
2. Re-run Phase 2 (`audit_caps.py`) to confirm no new mechanical violations were introduced.
3. Re-verify only the Phase 3 items that were adjacent to the fix. Do not re-read the entire script.

---

## Completion

1. Confirm `data/raw_draft.md` is saved.
2. Notify the user and mandate running `/5_decompose` **in a brand new session**.
