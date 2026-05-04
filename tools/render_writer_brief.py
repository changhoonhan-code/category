"""
Render Writer Brief — Materials Dossier generator.

Merges `data/category_writer.json` + `data/comparison_outline.json`
+ `data/hook_tactical_brief.json` into a single `data/writer_brief.md`
for the Writer Agent.

2-Part structure:
  Part 1: The Story — prose editorial brief describing the narrative arc
  Part 2: Data Library — reference material organized by topic for lookup

The Writer reads this dossier as raw materials, not as a structural template.
Scene/block ordering lives in comparison_outline.json for downstream tools only.

Usage:
    python tools/render_writer_brief.py
"""
import argparse
import json
import os
import sys

# -- Windows cp949 encoding fix
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import DATAS_DIR


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _build_products_map(writer_data):
    """product_id → full name mapping."""
    return {p["product_id"]: p.get("product_name", p["product_id"])
            for p in writer_data.get("products", [])}


def _build_short_names(writer_data):
    """product_id → brand-only short name for table headers."""
    m = {}
    for p in writer_data.get("products", []):
        name = p.get("product_name", p["product_id"])
        m[p["product_id"]] = name.split()[0] if name else p["product_id"]
    return m


def _extract_blueprint_directive(notes):
    """Extract the [Blueprint] narrative directive from outline scene notes."""
    marker = "narrative_directive: [Blueprint] "
    if marker not in notes:
        return ""
    start = notes.index(marker) + len(marker)
    end_marker = " | [Metric]"
    tail = notes[start:]
    if end_marker in tail:
        end = start + tail.index(end_marker)
    else:
        end = len(notes)
    return notes[start:end].strip()


def _build_narrative_angles(outline_data):
    """Build theme_name → narrative angle mapping from outline scenes."""
    angles = {}
    for scene in outline_data.get("scenes", []):
        directive = _extract_blueprint_directive(scene.get("notes", ""))
        if directive:
            for theme in scene.get("assigned_themes", []):
                angles[theme] = directive
    return angles


# ═══════════════════════════════════════════════════════════════════════════════
# Part 0: Product Reference
# ═══════════════════════════════════════════════════════════════════════════════

def render_product_reference(writer_data):
    """Render horizontal product reference table."""
    lines = []
    cat_name = writer_data.get("category_name", "Category")
    lines.append(f"# {cat_name} — Writer Dossier\n")
    lines.append("## Quick Reference\n")

    lines.append("| ID | Name | Sales | All-Time | Recent | Gap | Window |")
    lines.append("|----|------|-------|----------|--------|-----|--------|")

    trap_ids = []
    for p in writer_data.get("products", []):
        pid = p.get("product_id", "")
        name = p.get("product_name", "")
        sales = p.get("sold_last_month", "N/A")
        at = p.get("all_time_rating_avg", "N/A")
        rr = p.get("recent_review_rating_avg", "N/A")
        gap = p.get("population_gap", "N/A")
        window = p.get("recent_days", "N/A")
        window_str = f"{window} days" if isinstance(window, (int, float)) else str(window)
        lines.append(f"| {pid} | {name} | {sales} | {at} | {rr} | {gap} | {window_str} |")

        tc = p.get("trap_candidate", {})
        if tc and tc.get("is_trap"):
            trap_ids.append(pid)

    if trap_ids:
        if len(trap_ids) == len(writer_data.get("products", [])):
            lines.append(f"\nAll {len(trap_ids)} flagged as trap candidates.")
        else:
            lines.append(f"\nTrap candidates: {', '.join(trap_ids)}.")

    lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Part 1: The Story (prose editorial brief)
# ═══════════════════════════════════════════════════════════════════════════════

def render_the_story(outline_data, writer_data, hook_brief_data, products_map):
    """Generate an editorial prose brief describing the narrative arc.

    No scene numbers, no block IDs, no structural boxes — just the story
    the Writer needs to tell, written as an editor's letter.
    """
    lines = []
    lines.append("## The Story\n")

    # -- Video question as the guiding investigation
    vq = outline_data.get("video_question", "")
    if vq:
        lines.append(f"> {vq}\n")

    # -- Product names
    products = writer_data.get("products", [])
    names = [p.get("product_name", "") for p in products]
    if len(names) > 2:
        names_str = ", ".join(names[:-1]) + f", and {names[-1]}"
    elif len(names) == 2:
        names_str = f"{names[0]} and {names[1]}"
    else:
        names_str = names[0] if names else "the products"

    lines.append(
        f"Three products — {names_str} — "
        f"all bestsellers, all 4+ star ratings, all hiding something.\n"
    )

    # -- Theme data lookup (used by both hook and landscape sections)
    themes_map = {t["theme_name"]: t for t in writer_data.get("common_themes", [])}

    # -- Hook contradiction entry point (prose summary, not raw data)
    if hook_brief_data:
        rec = hook_brief_data.get("recommended_pick", {})
        candidates = hook_brief_data.get("ranked_candidates", [])
        picked = next((c for c in candidates if c.get("rank") == rec.get("rank", 1)), None)
        if picked:
            hook_theme = picked.get("theme_name", "")
            hook_pids = picked.get("product_ids", [])
            hook_pnames = [products_map.get(p, p) for p in hook_pids]

            # Extract spread from theme data for a concise summary
            hook_theme_data = themes_map.get(hook_theme, {})
            hook_rankings = hook_theme_data.get("rankings", [])
            hook_ratios = [r.get("positive_ratio", 0) for r in hook_rankings]
            hook_spread = round((max(hook_ratios) - min(hook_ratios)) * 100, 1) if hook_ratios else 0

            lines.append(
                f"The entry point is {hook_theme} — a {hook_spread}-point satisfaction gap "
                f"between {' and '.join(hook_pnames)}. "
                f"One sustains multi-session use; the other collapses systematically. "
                f"The collapse is community-validated and accelerating.\n"
            )

    # -- Theme landscape: differentiators vs universal weaknesses
    assigned = []
    for scene in outline_data.get("scenes", []):
        for t in scene.get("assigned_themes", []):
            if t not in assigned:
                assigned.append(t)

    diffs = [t for t in assigned if themes_map.get(t, {}).get("category_pattern_type") == "differentiator"]
    weaknesses = [t for t in assigned if themes_map.get(t, {}).get("category_pattern_type") == "universal_weakness"]

    # -- Build concise thread descriptions (no raw data)
    thread_parts = []
    for tn in diffs:
        theme = themes_map.get(tn, {})
        rankings = theme.get("rankings", [])
        ratios = [r.get("positive_ratio", 0) for r in rankings]
        spread = round((max(ratios) - min(ratios)) * 100, 1) if ratios else 0
        thread_parts.append(f"{tn} ({spread}pp spread)")

    diff_str = ""
    if thread_parts:
        diff_str = f"The clear differentiators — {', '.join(thread_parts)} — reveal where these products genuinely diverge."

    weak_str = ""
    if weaknesses:
        uw_names = " and ".join(weaknesses)
        weak_str = (
            f" {uw_names} {'are' if len(weaknesses) > 1 else 'is'} "
            f"category-wide {'failures' if len(weaknesses) > 1 else 'failure'} "
            f"where no product earns a majority-positive experience."
        )

    if diff_str or weak_str:
        lines.append(
            f"The comparison spans {len(assigned)} performance dimensions. "
            f"{diff_str}{weak_str}\n"
        )

    # -- Trap gradient
    trap_products = [p for p in products if p.get("trap_candidate", {}).get("is_trap")]
    if trap_products:
        gaps = sorted(
            [(p.get("product_name", ""), p.get("population_gap", 0)) for p in trap_products],
            key=lambda x: -x[1]
        )
        gap_strs = [f"{name} ({gap})" for name, gap in gaps]
        lines.append(
            f"All {'three' if len(trap_products) == 3 else len(trap_products)} carry trap-candidate flags — "
            f"high sales masking deteriorating satisfaction. "
            f"Severity gradient: {', '.join(gap_strs)}.\n"
        )

    # -- Closing principle
    lines.append(
        "The verdict is conditional. No unconditional winner exists in this category.\n"
    )

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Part 2: Data Library
# ═══════════════════════════════════════════════════════════════════════════════

def _render_contradiction_pair(pair, products_map):
    """Render a single contradiction pair in ✅/❌/💡 format."""
    lines = []
    pair_type = pair.get("type", "unknown")

    if pair_type == "within_product":
        pid = pair.get("product_id", "unknown")
        pname = products_map.get(pid, pid)
        lines.append(f"\n{pname} (within):")
    else:
        pids = pair.get("product_ids", [])
        pnames = [products_map.get(p, p) for p in pids]
        lines.append(f"\n{' vs '.join(pnames)} (cross):")

    pq = pair.get("positive_quote", {})
    nq = pair.get("negative_quote", {})

    if pq and pq.get("text"):
        star = f"{pq.get('star_rating', '?')}★" if pq.get("star_rating") else ""
        lines.append(f'✅ "{pq["text"]}" ({star})')
    if nq and nq.get("text"):
        star = f"{nq.get('star_rating', '?')}★" if nq.get("star_rating") else ""
        lines.append(f'❌ "{nq["text"]}" ({star})')

    hyp = pair.get("resolution_hypothesis")
    if hyp:
        lines.append(f"💡 {hyp}")

    return "\n".join(lines)


def render_hook_material(hook_brief_data, products_map):
    """Render Hook raw materials — contradiction, seeds, tease candidates."""
    if not hook_brief_data:
        return ""

    lines = []
    lines.append("### Hook Material\n")

    # -- Selected Contradiction
    rec = hook_brief_data.get("recommended_pick", {})
    candidates = hook_brief_data.get("ranked_candidates", [])
    picked = next((c for c in candidates if c.get("rank") == rec.get("rank", 1)), None)

    if picked:
        theme = picked.get("theme_name", "")
        pids = picked.get("product_ids", [])
        pnames = [products_map.get(p, p) for p in pids]
        drama = picked.get("drama_signals", "")
        score = picked.get("drama_score", "")

        lines.append(f"**Contradiction**: {theme} ({' vs '.join(pnames)})")
        lines.append(f"- Drama score: {score}")
        if drama:
            lines.append(f"- Drama signals: {drama}")
        lines.append("")

    # -- Scenario Seeds
    seeds = hook_brief_data.get("scenario_seeds", [])
    if seeds:
        lines.append("**Scenario Seeds**:\n")
        for seed in seeds:
            lines.append(f"- {seed}")
        lines.append("")

    # -- Tease Candidates
    tease = hook_brief_data.get("stage3_tease_candidates", [])
    if tease:
        lines.append("**Tease Candidates**:\n")
        for t in tease:
            name = t.get("theme_name", "")
            reason = t.get("reason", "")
            lines.append(f"- **{name}**: {reason}")
        lines.append("")

    lines.append("---\n")
    return "\n".join(lines)


def render_metric_entries(writer_data, outline_data, products_map, short_names):
    """Render all metric theme entries as Data Library reference sections.

    Each entry has: Angle hint (from Blueprint) → Numbers → Evidence → Anchors.
    """
    lines = []
    themes_map = {t["theme_name"]: t for t in writer_data.get("common_themes", [])}
    angles = _build_narrative_angles(outline_data)

    # Preserve outline theme order
    assigned = []
    for scene in outline_data.get("scenes", []):
        for t in scene.get("assigned_themes", []):
            if t not in assigned:
                assigned.append(t)

    for theme_name in assigned:
        theme = themes_map.get(theme_name)
        if not theme:
            continue

        pattern_type = theme.get("category_pattern_type", "unknown")
        lines.append(f"### {theme_name}\n")

        # -- Narrative angle (one-line Blueprint hint)
        angle = angles.get(theme_name, "")
        if angle:
            lines.append(f"> **Angle**: {angle}\n")

        # -- Category pattern
        cat_pattern = theme.get("category_pattern", "")
        if cat_pattern:
            lines.append(f"**Pattern** ({pattern_type}): {cat_pattern}\n")

        # -- The Spread table
        rankings = theme.get("rankings", [])
        if rankings:
            header_cols = [""]
            for r in rankings:
                pid = r.get("product_id", "")
                header_cols.append(short_names.get(pid, pid))

            lines.append("| " + " | ".join(header_cols) + " |")
            lines.append("|" + "|".join(["---"] * len(header_cols)) + "|")

            mention_row = ["Mentions"] + [str(r.get("mention_count", 0)) for r in rankings]
            lines.append("| " + " | ".join(mention_row) + " |")

            pos_row = ["Positive"] + [f"{r.get('positive_ratio', 0) * 100:.1f}%" for r in rankings]
            lines.append("| " + " | ".join(pos_row) + " |")

            ratios = [r.get("positive_ratio", 0) for r in rankings]
            spread_pp = round((max(ratios) - min(ratios)) * 100, 1) if ratios else 0
            min_mentions = min(r.get("mention_count", 0) for r in rankings)
            sig = "statistically significant" if min_mentions >= 50 else f"lowest product has only {min_mentions} mentions"
            lines.append(f"\n{spread_pp}pp gap. All products {min_mentions}+ mentions — {sig}.\n")

        # -- Contradiction Evidence
        c_pairs = theme.get("contradiction_pairs", [])
        if c_pairs:
            lines.append("**Evidence**:\n")
            for pair in c_pairs:
                lines.append(_render_contradiction_pair(pair, products_map))
            lines.append("")

        # -- Best Evidence anchors
        be = theme.get("best_evidence")
        if be:
            fp = be.get("first_place")
            lp = be.get("last_place")
            if fp or lp:
                lines.append("**Anchors**:\n")
                if fp:
                    fp_name = products_map.get(fp.get("product_id", ""), "?")
                    fq = fp.get("quote", {})
                    if fq and fq.get("text"):
                        lines.append(f"- **High end** ({fp_name}): \"{fq['text']}\"")
                if lp:
                    lp_name = products_map.get(lp.get("product_id", ""), "?")
                    lq = lp.get("quote", {})
                    if lq and lq.get("text"):
                        lines.append(f"- **Low end** ({lp_name}): \"{lq['text']}\"")
                lines.append("")

        lines.append("---\n")

    return "\n".join(lines)


def render_landmine_arsenal(writer_data, products_map):
    """Render per-product landmine data — weak metrics + trap flags."""
    lines = []
    products = writer_data.get("products", [])
    common_themes = {t.get("theme_name"): t for t in writer_data.get("common_themes", [])}

    lines.append("### Landmine Arsenal\n")

    for p in products:
        pid = p.get("product_id")
        pname = products_map.get(pid, pid)
        trap = p.get("trap_candidate", {})
        trap_flag = " · TRAP" if trap.get("is_trap") else ""
        gap = p.get("population_gap", "N/A")

        worst = []
        for tname, tdata in common_themes.items():
            for r in tdata.get("rankings", []):
                if r.get("product_id") == pid and r.get("positive_ratio", 1) < 0.3:
                    worst.append(f"{tname} ({r['positive_ratio']*100:.0f}%)")

        lines.append(f"**{pname}**{trap_flag} — gap {gap}")
        if worst:
            lines.append(f"- Weak: {', '.join(worst)}")
        lines.append("")

    lines.append("---\n")
    return "\n".join(lines)


def render_category_intelligence(writer_data):
    """Render Category Intelligence section."""
    lines = []
    ci = writer_data.get("category_intelligence", {})
    if not ci:
        return ""

    lines.append("### Category Intelligence\n")

    maturity = ci.get("maturity_assessment", "")
    if maturity:
        lines.append(f"**Maturity**: {maturity}\n")

    buy = ci.get("buy_in_category", "")
    if buy:
        lines.append(f"**Buy if**: {buy}\n")

    avoid = ci.get("avoid_category", "")
    if avoid:
        lines.append(f"**Avoid if**: {avoid}\n")

    uw = ci.get("universal_weaknesses", [])
    if uw:
        lines.append("**Universal Weaknesses**:\n")
        for w in uw:
            tname = w.get("theme_name", "")
            why = w.get("why_universal", "")
            lines.append(f"- **{tname}**: {why}")
        lines.append("")

    us = ci.get("universal_strengths", [])
    if us:
        lines.append("**Universal Strengths**:\n")
        for s in us:
            tname = s.get("theme_name", "")
            why = s.get("why_universal", "")
            lines.append(f"- **{tname}**: {why}")
        lines.append("")

    lines.append("---\n")
    return "\n".join(lines)


def render_unique_strengths(writer_data, products_map):
    """Render unique strengths data."""
    us_list = writer_data.get("unique_strengths", [])
    if not us_list:
        return ""

    lines = []
    lines.append("### Standout Data\n")

    for us in us_list:
        pid = us.get("product_id", "")
        pname = products_map.get(pid, pid)
        theme = us.get("theme_name", "")
        ratio = us.get("positive_ratio", 0)
        why = us.get("why_unique", "")
        use_case = us.get("recommended_use_case", "")

        lines.append(f"**{pname} — {theme}** ({ratio * 100:.1f}%)")
        if why:
            lines.append(f"- {why}")
        if use_case:
            lines.append(f"- Use case: {use_case}")

        bq = us.get("best_quote")
        if bq and bq.get("text"):
            lines.append(f'- Quote: "{bq["text"]}"')
        lines.append("")

    lines.append("---\n")
    return "\n".join(lines)


def render_analyst_notebook(writer_data):
    """Render Analyst's Notebook entries."""
    notebook = writer_data.get("analyst_notebook", [])
    if not notebook:
        return ""

    lines = []
    lines.append("### Analyst's Notebook\n")
    for entry in notebook:
        title = entry.get("title", "Untitled")
        obs = entry.get("observation", "")
        lines.append(f"**{title}**")
        lines.append(obs)
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Main Assembly
# ═══════════════════════════════════════════════════════════════════════════════

def render_brief(writer_data, outline_data, hook_brief_data=None):
    """Assemble the full writer dossier.

    Part 1: The Story — prose editorial arc (no structural boxes)
    Part 2: Data Library — reference material for lookup
    """
    products_map = _build_products_map(writer_data)
    short_names = _build_short_names(writer_data)

    parts = [
        render_product_reference(writer_data),
        render_the_story(outline_data, writer_data, hook_brief_data, products_map),
        "---\n\n## Data Library\n",
        render_hook_material(hook_brief_data, products_map),
        render_metric_entries(writer_data, outline_data, products_map, short_names),
        render_landmine_arsenal(writer_data, products_map),
        render_category_intelligence(writer_data),
        render_unique_strengths(writer_data, products_map),
        render_analyst_notebook(writer_data),
    ]
    return "\n".join(part for part in parts if part)


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: Render writer dossier from JSON inputs"
    )
    parser.add_argument(
        "--writer", default=os.path.join(DATAS_DIR, "category_writer.json"),
        help="Path to category_writer.json"
    )
    parser.add_argument(
        "--outline", default=os.path.join(DATAS_DIR, "comparison_outline.json"),
        help="Path to comparison_outline.json"
    )
    parser.add_argument(
        "--hook", default=os.path.join(DATAS_DIR, "hook_tactical_brief.json"),
        help="Path to hook_tactical_brief.json"
    )
    parser.add_argument(
        "--output", default=os.path.join(DATAS_DIR, "writer_brief.md"),
        help="Output path for writer_brief.md"
    )
    args = parser.parse_args()

    for path, label in [(args.writer, "Writer data"), (args.outline, "Outline")]:
        if not os.path.exists(path):
            print(f"ERROR: {label} not found: {path}", file=sys.stderr)
            sys.exit(1)

    hook_brief_data = None
    if os.path.exists(args.hook):
        hook_brief_data = load_json(args.hook)
    else:
        print(f"WARNING: Hook brief not found: {args.hook} — Hook Material will be empty", file=sys.stderr)

    writer_data = load_json(args.writer)
    outline_data = load_json(args.outline)

    brief_content = render_brief(writer_data, outline_data, hook_brief_data)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(brief_content)

    size = len(brief_content.encode("utf-8"))
    section_count = brief_content.count("### ")
    hook_status = "with Hook Data" if hook_brief_data else "NO Hook Data"
    print(f"render_writer_brief.py: Generated {args.output} ({size:,} bytes, {section_count} sections, {hook_status})")


if __name__ == "__main__":
    main()
