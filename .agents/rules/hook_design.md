---
trigger: manual
---

# Hook Design Rules (Category Comparison)

> Shared by: Orchestrator, Blueprint Designer. Writer-facing voice rules absorbed into `reviewlens_writer_agent/SKILL.md §4 Hook`. Data-specific directives (scenario seeds, contradiction pick, tease themes) injected into `writer_brief.md` via `render_writer_brief.py`.

## Core Principle: The Relatable Scenario

The Hook is the primary mechanism for breaking out of the narrow niche. It must capture viewers who have NO interest in the specific products being compared.

> **Niche-Piercing Question Test**: "Would someone with zero interest in this category still be curious?"

### Relatable Scenario Guidance

Stage 1 requires a universally relatable observation. The following positive patterns define what a good Relatable Scenario looks like:

| Pattern | Description | Example Seed |
|---|---|---|
| **Observable Behavior** | Something the viewer has witnessed or done themselves — no imagination required | "You've seen someone yank out an earbud mid-conversation and shove it back in wrong" |
| **Category-Wide Frustration** | A complaint so common it transcends any single product | "That moment three months in when the thing you loved starts falling apart" |
| **Counterintuitive Common Sense** | A widely-held assumption that the data disproves | "The most expensive option should be the best — that's how it works, right?" |
| **Purchase Moment Doubt** | The universal hesitation at the point of purchase | "Staring at a 4.5-star rating and still not trusting it" |

**Absolute Prohibitions**:
- ❌ Fiction Scenarios — must obey `narrative_standards.md §3` (1st Person Observer Rule)
- ❌ Product/brand references in Stage 1 — ZERO tolerance

> The Orchestrator provides data-specific `scenario_seeds` in `data/hook_tactical_brief.json` before Blueprint Designer runs. These seeds are pre-vetted against the prohibitions above.

## Mandatory 2-Block Architecture

The ReviewLens pipeline enforces a strict **2-Block Hook** to ensure mechanical density checking.

> **Stage Composition Flexibility**: The 2-block structure is fixed. However, the internal
> stage composition is flexible across the 2 blocks:
> - Block 1 handles Stage 1+2, and Block 2 handles Stage 3 (default split).
> - Alternatively, Block 1 handles Stage 1, and Block 2 handles Stage 2+3.
> - The Writer determines the optimal stage split based on the contradiction's data density.

### Block 1: `hook_contradiction`
- **Stage 1 (First Half)**: Lead with a universally relatable observation or question. **ZERO product/brand references.**
  - *Prohibition Check*: `narrative_standards.md §3` applies. Scenario must be derivable from real user frustrations.
- **Stage 2 (Second Half)**: Immediately drop the core contradiction.
  - *Data Application*: The product name(s) should only appear in the dependent clause of the contradiction reveal.

### Block 2: `hook_curiosity_loop`
- **Stage 3**: Plant the seeds for the upcoming comparison.
  - Tease 2-3 specific themes that explain the contradiction.
  - Inject a subtle `category_intelligence` hint to establish authority.
  - Hand off smoothly to the `intro_credibility` scene.

## Contradiction Selection: Composite Drama Scoring

> Replaces rigid type-based priority. The Orchestrator computes drama scores in `data/hook_tactical_brief.json` and ranks candidates. Blueprint Designer selects from the ranked list.

### Drama Assessment Criteria

The Orchestrator reads the data and makes a qualitative judgment based on these signals:

| Type | Key Signals | High Drama Indicators |
|---|---|---|
| **Cross-Product** | `positive_ratio` gap between products, `mention_count` per product | Gap > 30%p with 50+ mentions each = strong. Gap < 15%p or low mentions = weak |
| **Within-Product** | Star rating polarity (5★ vs 1★), `helpful_count` on quotes | High helpful_count (50+) means community-validated outrage. Low helpful = anecdotal |
| **Expectation Gap** | `population_gap`, `sold_last_month` | Gap ≥ 0.7 with 10K+ sales = mass-market deception. Gap < 0.3 = noise |

### Selection Rules

1. **Primary**: Select the candidate with the strongest overall drama potential regardless of type
2. **Tiebreak**: If two candidates feel equally strong, apply type preference: Cross-Product > Within-Product > Expectation Gap
3. **Override**: Blueprint Designer may override the Orchestrator's recommendation with documented `selection_rationale` explaining why an alternative is narratively stronger

## Stage 3: Curiosity Loop Tactics

> The Orchestrator pre-selects `stage3_tease_candidates` in `data/hook_tactical_brief.json`.

### Tease Theme Selection Criteria

| Criterion | Measurement | Priority |
|---|---|---|
| **Counterintuitiveness** | Theme where the spread defies price or brand expectations | Highest |
| **Breadth** | Theme affecting 3+ products (category-level pattern) | High |
| **Early Placement** | Flag themes that should appear early in `selected_themes` for faster Hook payoff | Supporting |

### Curiosity Loop Structure Rules

1. Each tease = one **open loop** (an unanswered "why?" or "how?")
2. Exactly 2-3 open loops — fewer feels thin, more overwhelms
3. **Spoiler Prevention**: Tease the existence of a pattern, never reveal the answer. "Battery tells two very different stories" ✅ vs "Product A's battery fails after 3 months" ❌
4. The `category_intelligence` hint must be a **credential signal** — one data point that proves the narrator has done deep analysis (e.g., "and there's a pattern in the recent reviews that none of them want you to see")

## Hook Time Budget

> The Orchestrator assigns `time_budget` in `data/hook_tactical_brief.json` based on data complexity.

| Data Complexity | Stage 1 | Stage 2 | Stage 3 | Total |
|:---:|:---:|:---:|:---:|:---:|
| **Simple** (single stat contradiction) | ~8 sec | ~10 sec | ~12 sec | ~30 sec |
| **Complex** (multi-product data) | ~6 sec | ~14 sec | ~10 sec | ~30 sec |
| **Dramatic** (strong contradiction, high drama score) | ~10 sec | ~12 sec | ~8 sec | ~30 sec |

- **Simple**: Contradiction is self-explanatory → less setup, more tease time
- **Complex**: Multiple data points need to land → more Stage 2 time
- **Dramatic**: Contradiction is visceral → build Stage 1 tension longer, Stage 3 tease can be brief because the contradiction itself sustains curiosity

> These are directional targets. The Writer converts them to word counts using `narrative_standards.md §6` pacing profiles.

## Output Schema: `data/hook_tactical_brief.json`

> Consumed by: Blueprint Designer (strategic selection), `build_outline.py` (time budget + scenario seeds injection into outline notes).

```jsonc
{
  // Top 3 contradiction candidates ranked by drama potential
  "ranked_candidates": [
    {
      "rank": 1,
      "type": "cross_product | within_product | expectation_gap",
      "theme_name": "string — source theme from common_themes",
      "product_ids": ["string"],           // affected product(s)
      "drama_signals": "string — qualitative rationale: which signals drove this ranking",
      "drama_score": "high | medium | low" // overall drama assessment
    }
    // ... up to 3 entries
  ],

  // Orchestrator's top pick — Blueprint Designer starts here, may override
  "recommended_pick": {
    "rank": 1,
    "override_note": "string — why this candidate was recommended over #2/#3"
  },

  // 2-3 themes suitable for Stage 3 curiosity loop teasers
  "stage3_tease_candidates": [
    {
      "theme_name": "string — from common_themes",
      "reason": "string — counterintuitiveness / breadth / early placement rationale",
      "suggest_early_placement": true  // flag per §Stage 3 criteria
    }
  ],

  // 2-3 relatable scenario seeds vetted against prohibitions
  "scenario_seeds": [
    "string — one-sentence scenario seed matching §Relatable Scenario Guidance patterns"
  ],

  // Data complexity classification + per-stage time allocation
  "data_complexity": "simple | complex | dramatic",
  "time_budget": {
    "stage1_sec": 8,   // per §Hook Time Budget table
    "stage2_sec": 10,
    "stage3_sec": 12,
    "rationale": "string — why this complexity class was chosen"
  }
}
```