#!/usr/bin/env python3
"""
audit_caps.py — Mechanical Cap Auditor for raw_draft.md

Counts all capped patterns defined in SKILL.md §2-3 and 4_write.md Self-Audit.
Outputs a PASS/FAIL report with exact locations for each violation.

Usage:
    python tools/audit_caps.py data/raw_draft.md
    python tools/audit_caps.py data/raw_draft.md --json   # JSON output to stdout

Exit codes:
    0 = all caps pass
    1 = one or more caps violated
"""

import re
import sys
import json
from pathlib import Path
from collections import Counter


# ── Configuration ──────────────────────────────────────────────────────────

# Sentence-initial conjunctions: ≤ 3 each
CONJUNCTION_CAP = 3
CONJUNCTIONS = ["But", "And", "Now", "So"]

# Intensifier adverbs: ≤ 2 each
INTENSIFIER_CAP = 2
INTENSIFIERS = [
    "genuinely", "actually", "literally", "absolutely",
    "dramatically", "quietly", "fundamentally", "randomly", "silently",
]

# Price-point appeal: ≤ 1
PRICE_APPEAL_CAP = 1
PRICE_PATTERNS = [
    r"at this price",
    r"for a product at this price",
    r"at this price point",
    r"for (?:a product|something|\w+) (?:at|costing) (?:this|that) (?:price|much)",
]

# Fraction format: ≤ 2
FRACTION_CAP = 2
FRACTION_PATTERN = r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:out of|in)\s+(\d+|ten|five|every|twenty)\b"

# Contrastive reframe: ≤ 2
CONTRASTIVE_CAP = 2
CONTRASTIVE_PATTERN = r"That(?:'s| is) not .{3,60}?\.\s+That(?:'s| is) .{3,60}?\."

# Mention-count + ratio combo: ≤ 1
MENTION_RATIO_CAP = 1
MENTION_RATIO_PATTERN = r"\b\d+\s+(?:people|owners|buyers|reviewers|users)\s+mentioned\b.*?\b\d+\s*%"

# Banned phrases (zero tolerance) — synced with narrative_standards.md §5
BANNED_PHRASES = [
    # Passive data attribution / Robotic phrasing
    "The data shows", "According to the results", "According to the analysis",
    "The numbers indicate", "In conclusion",
    "Conversely", "Interestingly", "It is worth noting",
    "Let's dive in", "Without further ado",
    # Banned hedges (Inference Hedging)
    "The pattern suggests", "This points to",
    # Lazy transitions
    "Moving on to", "Furthermore", "Now let's look at",
    # Vague quantifiers
    "Many users", "Some buyers", "A lot of", "Most people",
    "Many owners", "Some users", "Some reviewers", "Many buyers",
    # Report-style framing
    "Let us examine", "Upon analysis", "The findings suggest",
    # Disengaged observer
    "One observes that",
    # Emotional filler
    "It's important to note", "Needless to say",
    "At the end of the day", "Picture this",
    # AI hype jargon
    "Game-changer", "Revolutionary", "Delve", "Dive deep",
    "Testament", "Unveil",
    # Vertical rankings (unconditional winner declarations)
    "Best overall", "The clear winner", "Ranked number one",
    "The champion is", "The obvious choice",
    # YouTuber CTAs
    "Subscribe", "hit the bell", "like and share",
    "before you spend your money",
    # Solo narrator pronouns (must use 1st-person plural)
    "I analyzed", "I found", "I read", "my data shows",
    "I discovered", "I noticed",
    # Academic / Technical jargon
    "Orthogonal", "Horizontal differentiation", "Cohort",
    "Sentiment polarity", "Categorical imperative", "Demographics",
    # Courtroom drama
    "Crime scene", "Damning evidence", "Indictment", "Prosecution",
]

# "Here's the [noun]" pattern — all variants banned
HERES_PATTERN = r"Here's the \w+"

# Standalone "Next" as sentence opener + "Then the [X]" lazy transition
LAZY_TRANSITION_PATTERNS = [
    r"(?<=[.!?]\s)Next[,.]",        # "Next," or "Next." as sentence opener
    r"^Next[,.]",                    # At start of text
    r"(?<=[.!?]\s)Then the \w+",     # "Then the [X]" as transition
]

# Formulaic recap pattern: "While the X was…, let's look at…"
FORMULAIC_RECAP_PATTERN = r"(?:While|With) (?:the |those |that ).{10,60}?,\s*(?:let's|let us|now)"

# Raw decimal percentages (Numeric Exile): zero tolerance
DECIMAL_PERCENT_PATTERN = r"\b\d+\.\d+\s*%"

# Sentence opener diversity: no single pattern > 20%
OPENER_DIVERSITY_CAP = 0.20

# Individual attribution cap: ≤ 3 (specific person as subject)
INDIVIDUAL_ATTRIBUTION_CAP = 3
INDIVIDUAL_ATTRIBUTION_PATTERN = r"\b(?:One|A single|A particular)\s+(?:buyer|reviewer|owner|user|person|customer)\b"

# Collective source framing phrases (used for cadence & reinforcement checks)
COLLECTIVE_SOURCE_PATTERNS = [
    r"\b(?:buyers|owners|reviewers|users|customers)\s+(?:keep|are|report|say|describe|mention|complain|note)",
    r"\b(?:the reviews?|the feedback|review after review)\b",
    r"\bwhat (?:owners|buyers|reviewers|users) are (?:reporting|saying|describing)\b",
    r"\bbased on what (?:owners|buyers|reviewers|users)\b",
    r"\b(?:we pulled|we analyzed|we read|our data|our analysis|across .{0,20}reviews)\b",
    r"\bthe (?:reviews|feedback) (?:paint|tell|show|reveal|point)\b",
]


# ── Helpers ────────────────────────────────────────────────────────────────

def load_text(path: str) -> str:
    """Load file, skip metadata headers but preserve ### block tags."""
    text = Path(path).read_text(encoding="utf-8")
    lines = text.split("\n")
    # Strip top-level headers (# and ##) but keep ### block tags as structural markers
    content_lines = [l for l in lines if (not l.startswith("#") or l.startswith("### ")) and l.strip()]
    return "\n".join(content_lines)


def split_sentences(text: str) -> list[str]:
    """
    Split text into sentences. Handles common abbreviations
    and avoids splitting on decimal points.
    """
    # Protect common abbreviations
    protected = text
    for abbr in ["Mr.", "Ms.", "Dr.", "vs.", "e.g.", "i.e.", "etc."]:
        protected = protected.replace(abbr, abbr.replace(".", "<DOT>"))
    # Protect decimal numbers
    protected = re.sub(r"(\d)\.([\d])", r"\1<DOT>\2", protected)

    # Split on sentence-ending punctuation followed by space + capital letter
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'])', protected)

    # Restore dots
    return [s.replace("<DOT>", ".").strip() for s in sentences if s.strip()]


def find_occurrences(text: str, pattern: str, flags: int = 0) -> list[dict]:
    """Find all regex matches with surrounding context."""
    results = []
    for m in re.finditer(pattern, text, flags):
        start = max(0, m.start() - 30)
        end = min(len(text), m.end() + 30)
        context = text[start:end].replace("\n", " ")
        results.append({
            "match": m.group(),
            "context": f"…{context}…",
            "position": m.start(),
        })
    return results


# ── Audit Checks ───────────────────────────────────────────────────────────

def audit_conjunction_openers(sentences: list[str]) -> list[dict]:
    """Check sentence-initial conjunctions against caps."""
    results = []
    for conj in CONJUNCTIONS:
        hits = [s for s in sentences if re.match(rf"^{conj}\b", s)]
        passed = len(hits) <= CONJUNCTION_CAP
        results.append({
            "rule": f"Sentence-initial \"{conj}\"",
            "cap": CONJUNCTION_CAP,
            "found": len(hits),
            "passed": passed,
            "samples": [s[:80] + "…" if len(s) > 80 else s for s in hits],
        })
    return results


def audit_intensifiers(text: str) -> list[dict]:
    """Check intensifier adverb frequency."""
    results = []
    words = re.findall(r"\b\w+\b", text.lower())
    for adv in INTENSIFIERS:
        count = words.count(adv)
        if count > 0:
            # Get contexts
            contexts = find_occurrences(text, rf"\b{adv}\b", re.IGNORECASE)
            results.append({
                "rule": f"Intensifier \"{adv}\"",
                "cap": INTENSIFIER_CAP,
                "found": count,
                "passed": count <= INTENSIFIER_CAP,
                "samples": [c["context"] for c in contexts[:5]],
            })
    return results


def audit_intensifier_clusters(text: str) -> list[dict]:
    """Check for 3+ distinct intensifiers in one paragraph."""
    results = []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for i, para in enumerate(paragraphs):
        para_lower = para.lower()
        found_intensifiers = [adv for adv in INTENSIFIERS if re.search(rf"\b{adv}\b", para_lower)]
        if len(found_intensifiers) >= 3:
            results.append({
                "rule": "Intensifier cluster (3+ distinct in one paragraph)",
                "cap": 2,
                "found": len(found_intensifiers),
                "passed": False,
                "samples": [f"Paragraph {i+1}: {', '.join(found_intensifiers)}"],
            })
    return results


def audit_banned_phrases(text: str) -> list[dict]:
    """Check for zero-tolerance banned phrases."""
    results = []
    for phrase in BANNED_PHRASES:
        hits = find_occurrences(text, re.escape(phrase), re.IGNORECASE)
        if hits:
            results.append({
                "rule": f"Banned phrase \"{phrase}\"",
                "cap": 0,
                "found": len(hits),
                "passed": False,
                "samples": [h["context"] for h in hits[:3]],
            })
    # Check "Here's the [noun]" pattern
    hits = find_occurrences(text, HERES_PATTERN, re.IGNORECASE)
    if hits:
        results.append({
            "rule": "Banned pattern \"Here's the [noun]\"",
            "cap": 0,
            "found": len(hits),
            "passed": False,
            "samples": [h["context"] for h in hits[:3]],
        })
    # Check lazy transition regex patterns ("Next,", "Then the [X]")
    for pat in LAZY_TRANSITION_PATTERNS:
        hits = find_occurrences(text, pat, re.IGNORECASE)
        if hits:
            results.append({
                "rule": f"Banned lazy transition pattern",
                "cap": 0,
                "found": len(hits),
                "passed": False,
                "samples": [h["context"] for h in hits[:3]],
            })
    # Check formulaic recap pattern ("While the X was…, let's…")
    hits = find_occurrences(text, FORMULAIC_RECAP_PATTERN, re.IGNORECASE)
    if hits:
        results.append({
            "rule": "Banned formulaic recap (\"While/With the X…, let's/now…\")",
            "cap": 0,
            "found": len(hits),
            "passed": False,
            "samples": [h["context"] for h in hits[:3]],
        })
    return results


def audit_decimal_percentages(text: str) -> list[dict]:
    """Check Numeric Exile — no raw decimal percentages."""
    hits = find_occurrences(text, DECIMAL_PERCENT_PATTERN)
    results = []
    if hits:
        results.append({
            "rule": "Numeric Exile (raw decimal %)",
            "cap": 0,
            "found": len(hits),
            "passed": False,
            "samples": [h["context"] for h in hits[:5]],
        })
    return results


def audit_price_appeal(text: str) -> list[dict]:
    """Check price-point appeal cap."""
    all_hits = []
    for pat in PRICE_PATTERNS:
        all_hits.extend(find_occurrences(text, pat, re.IGNORECASE))
    # Deduplicate by position
    seen_pos = set()
    unique_hits = []
    for h in all_hits:
        if h["position"] not in seen_pos:
            seen_pos.add(h["position"])
            unique_hits.append(h)
    return [{
        "rule": "Price-point appeal (\"at this price\" etc.)",
        "cap": PRICE_APPEAL_CAP,
        "found": len(unique_hits),
        "passed": len(unique_hits) <= PRICE_APPEAL_CAP,
        "samples": [h["context"] for h in unique_hits[:3]],
    }]


def audit_fractions(text: str) -> list[dict]:
    """Check fraction format cap."""
    hits = find_occurrences(text, FRACTION_PATTERN, re.IGNORECASE)
    return [{
        "rule": "Fraction format (\"N out of M\")",
        "cap": FRACTION_CAP,
        "found": len(hits),
        "passed": len(hits) <= FRACTION_CAP,
        "samples": [h["context"] for h in hits[:5]],
    }]


def audit_contrastive_reframe(text: str) -> list[dict]:
    """Check contrastive reframe pattern cap."""
    hits = find_occurrences(text, CONTRASTIVE_PATTERN, re.IGNORECASE)
    return [{
        "rule": "Contrastive reframe (\"That's not X. That's Y.\")",
        "cap": CONTRASTIVE_CAP,
        "found": len(hits),
        "passed": len(hits) <= CONTRASTIVE_CAP,
        "samples": [h["context"] for h in hits[:3]],
    }]


def audit_mention_ratio(text: str) -> list[dict]:
    """Check mention-count + ratio combo cap."""
    hits = find_occurrences(text, MENTION_RATIO_PATTERN, re.IGNORECASE)
    return [{
        "rule": "Mention-count + ratio combo",
        "cap": MENTION_RATIO_CAP,
        "found": len(hits),
        "passed": len(hits) <= MENTION_RATIO_CAP,
        "samples": [h["context"] for h in hits[:3]],
    }]


def audit_sentence_opener_diversity(sentences: list[str]) -> list[dict]:
    """Check that no single opener pattern exceeds 20% of sentences."""
    if not sentences:
        return []

    # Extract first 3 words as opener pattern
    openers = Counter()
    for s in sentences:
        words = s.split()
        if len(words) >= 3:
            # Normalize any capitalized proper noun (2+ chars) to [Product]
            # This catches brand/model names generically without hardcoding
            opener = " ".join(words[:3])
            normalized = re.sub(r"\b[A-Z][a-zA-Z]{1,}(?:\s+[A-Z][a-zA-Z]*)*\b", "[Product]", opener).strip()
            openers[normalized] += 1

    total = len(sentences)
    threshold = total * OPENER_DIVERSITY_CAP
    results = []

    for pattern, count in openers.most_common(5):
        if count > threshold:
            results.append({
                "rule": f"Sentence opener diversity — \"{pattern}\"",
                "cap": f"≤ {OPENER_DIVERSITY_CAP*100:.0f}% ({int(threshold)} of {total})",
                "found": count,
                "passed": False,
                "samples": [f"{count}/{total} sentences ({count/total*100:.1f}%)"],
            })

    if not results:
        top_pattern, top_count = openers.most_common(1)[0] if openers else ("N/A", 0)
        results.append({
            "rule": "Sentence opener diversity",
            "cap": f"≤ {OPENER_DIVERSITY_CAP*100:.0f}%",
            "found": f"{top_count}/{total} ({top_count/total*100:.1f}%)" if total > 0 else "0",
            "passed": True,
            "samples": [f"Most common: \"{top_pattern}\" — {top_count}/{total}"],
        })

    return results


def audit_bridge_phrase_repeats(sentences: list[str]) -> list[dict]:
    """Check that no identical transition/bridge phrase is used > 2 times."""
    # Extract leading phrases (first 4+ words that look like transitions)
    transition_starters = Counter()
    for s in sentences:
        words = s.split()
        if len(words) >= 4:
            # Check first 4 words as potential bridge
            starter = " ".join(words[:4]).rstrip(".,;:—")
            transition_starters[starter] += 1

    results = []
    for phrase, count in transition_starters.most_common():
        if count > 2:
            results.append({
                "rule": f"Bridge phrase repeat — \"{phrase}…\"",
                "cap": 2,
                "found": count,
                "passed": False,
                "samples": [f"Used {count} times"],
            })

    return results


def audit_individual_attribution(text: str) -> list[dict]:
    """Check individual attribution cap (≤ 3 per script)."""
    hits = find_occurrences(text, INDIVIDUAL_ATTRIBUTION_PATTERN, re.IGNORECASE)
    return [{
        "rule": "Individual attribution (\"One buyer/reviewer…\")",
        "cap": INDIVIDUAL_ATTRIBUTION_CAP,
        "found": len(hits),
        "passed": len(hits) <= INDIVIDUAL_ATTRIBUTION_CAP,
        "samples": [h["context"] for h in hits[:5]],
    }]


def _count_source_hits(text: str) -> int:
    """Count total collective source framing matches in a text segment."""
    total = 0
    seen_positions = set()
    for pat in COLLECTIVE_SOURCE_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            if m.start() not in seen_positions:
                seen_positions.add(m.start())
                total += 1
    return total


def audit_review_source_cadence(text: str) -> list[dict]:
    """Check that collective source framing appears in each third of the script."""
    total_len = len(text)
    if total_len < 100:
        return []
    third = total_len // 3
    segments = [
        ("Opening third", text[:third]),
        ("Middle third", text[third:2*third]),
        ("Final third", text[2*third:]),
    ]

    empty_segments = []
    for label, segment in segments:
        count = _count_source_hits(segment)
        if count == 0:
            empty_segments.append(label)

    passed = len(empty_segments) == 0
    return [{
        "rule": "Review Source Cadence (source framing in each script third)",
        "cap": "≥ 1 per third",
        "found": f"{3 - len(empty_segments)}/3 thirds covered",
        "passed": passed,
        "samples": [f"Missing in: {', '.join(empty_segments)}"] if empty_segments else ["All thirds covered"],
    }]


def audit_scale_reinforcement(text: str) -> list[dict]:
    """Check periodic scale reinforcement — review source anchored in opening, mid, and near verdict."""
    total_len = len(text)
    if total_len < 100:
        return []
    third = total_len // 3
    segments = [
        ("Opening", text[:third]),
        ("Mid-script", text[third:2*third]),
        ("Near verdict", text[2*third:]),
    ]

    scale_pattern = r"\b(?:\d[,\d]*\s+(?:\w+\s+)?reviews?|thousands? of (?:\w+\s+)?reviews?|hundreds? of (?:\w+\s+)?reviews?|over \d[,\d]*\s+(?:\w+\s+)?(?:reviews?|ratings?|buyers?|owners?))\b"
    empty_segments = []
    for label, segment in segments:
        hits = re.findall(scale_pattern, segment, re.IGNORECASE)
        if not hits:
            empty_segments.append(label)

    # Opening is mandatory; allow 1 miss in mid or verdict
    passed = len(empty_segments) <= 1
    if "Opening" in empty_segments:
        passed = False

    return [{
        "rule": "Periodic Scale Reinforcement (review count anchoring)",
        "cap": "Opening mandatory + ≥ 1 of mid/verdict",
        "found": f"{3 - len(empty_segments)}/3 segments anchored",
        "passed": passed,
        "samples": [f"Missing in: {', '.join(empty_segments)}"] if empty_segments else ["All segments anchored"],
    }]


# ── Main ───────────────────────────────────────────────────────────────────

def run_audit(filepath: str) -> dict:
    """Run all audits and return structured report."""
    text = load_text(filepath)
    sentences = split_sentences(text)

    all_results = []

    # Mechanical caps
    all_results.extend(audit_conjunction_openers(sentences))
    all_results.extend(audit_intensifiers(text))
    all_results.extend(audit_intensifier_clusters(text))
    all_results.extend(audit_banned_phrases(text))
    all_results.extend(audit_decimal_percentages(text))
    all_results.extend(audit_price_appeal(text))
    all_results.extend(audit_fractions(text))
    all_results.extend(audit_contrastive_reframe(text))
    all_results.extend(audit_mention_ratio(text))
    all_results.extend(audit_sentence_opener_diversity(sentences))
    all_results.extend(audit_bridge_phrase_repeats(sentences))

    # Review source framing (narrative_standards.md audit fixes)
    all_results.extend(audit_individual_attribution(text))
    all_results.extend(audit_review_source_cadence(text))
    all_results.extend(audit_scale_reinforcement(text))

    violations = [r for r in all_results if not r["passed"]]
    passes = [r for r in all_results if r["passed"]]

    return {
        "file": filepath,
        "total_sentences": len(sentences),
        "checks_run": len(all_results),
        "passed": len(passes),
        "failed": len(violations),
        "verdict": "PASS" if not violations else "FAIL",
        "violations": violations,
        "passes": passes,
    }


def print_report(report: dict) -> None:
    """Print human-readable report to stderr."""
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  AUDIT CAPS REPORT — {report['file']}", file=sys.stderr)
    print(f"  Sentences: {report['total_sentences']}  |  "
          f"Checks: {report['checks_run']}  |  "
          f"Pass: {report['passed']}  |  "
          f"Fail: {report['failed']}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    if report["violations"]:
        print(f"\n  ❌ VIOLATIONS ({report['failed']})\n", file=sys.stderr)
        for v in report["violations"]:
            cap_str = v["cap"] if isinstance(v["cap"], str) else f"≤ {v['cap']}"
            print(f"  [{v['found']} / {cap_str}]  {v['rule']}", file=sys.stderr)
            for sample in v["samples"][:3]:
                print(f"      → {sample}", file=sys.stderr)
            print(file=sys.stderr)

    if report["passes"]:
        print(f"  ✅ PASSED ({report['passed']})\n", file=sys.stderr)
        for p in report["passes"]:
            cap_str = p["cap"] if isinstance(p["cap"], str) else f"≤ {p['cap']}"
            print(f"  [{p['found']} / {cap_str}]  {p['rule']}", file=sys.stderr)

    print(f"\n{'='*60}", file=sys.stderr)
    verdict_icon = "✅" if report["verdict"] == "PASS" else "❌"
    print(f"  {verdict_icon} FINAL VERDICT: {report['verdict']}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/audit_caps.py <raw_draft.md> [--json]", file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[1]
    json_mode = "--json" in sys.argv

    if not Path(filepath).exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(2)

    report = run_audit(filepath)
    print_report(report)

    if json_mode:
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))

    sys.exit(0 if report["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
