"""
Filter summary.json for agent-specific profiles — reduces token cost by providing
each agent only the fields it needs from the master data source.

Usage:
    python tools/filter_summary.py --profile architect
    python tools/filter_summary.py --profile writer --output data/summary_writer.json

Profiles: architect, writer, data_validator, tone_editor, broll
"""
import argparse
import json
import os
import sys

from config import DATAS_DIR

# ── Profile Definitions ─────────────────────────────────────────────────────
# Each profile specifies which fields to INCLUDE from summary.json.
# - product_data_fields: [] means omit product_data entirely
# - evidence_quote_fields: [] means omit evidence_quotes entirely
# - filter_has_media_only: True means keep only quotes where has_media == True

PROFILES = {
    "architect": {
        "product_data_fields": [
            "product_name", "reviews_analyzed_count", "top_praised_themes",
        ],
        "theme_fields": [
            "theme_name", "mention_count", "mention_percent",
            "sentiment_distribution", "is_trending", "recent_mention_count",
        ],
        "evidence_quote_fields": [],
    },
    "writer": {
        "product_data_fields": [
            "product_name", "all_time_rating_count", "all_time_rating_avg",
            "recent_review_count", "recent_review_rating_avg",
            "recent_period_text", "recent_days", "reviews_analyzed_count",
            "all_time_rating_distribution", "recent_review_rating_distribution",
            "top_praised_themes", "population_gap", "population_gap_percent",
        ],
        "theme_fields": [
            "theme_name", "mention_count", "mention_percent",
            "sentiment_distribution", "is_trending", "recent_mention_count",
            "temporal_pattern", "root_cause", "purchase_guidance",
            "affected_user_profile",
        ],
        "evidence_quote_fields": [
            "text", "sentiment", "star_rating", "review_id",
            "review_date", "helpful_count", "is_humorous",
            "selection_reason", "has_media",
        ],
    },
    "data_validator": {
        "product_data_fields": [
            "product_name", "all_time_rating_count", "all_time_rating_avg",
            "recent_review_count", "recent_review_rating_avg",
            "recent_period_text", "recent_days", "reviews_analyzed_count",
            "all_time_rating_distribution", "recent_review_rating_distribution",
        ],
        "theme_fields": [
            "theme_name", "mention_count", "mention_percent",
            "sentiment_distribution", "is_trending", "recent_mention_count",
        ],
        "evidence_quote_fields": [
            "text", "star_rating", "review_id", "review_date",
            "helpful_count", "is_humorous", "selection_reason", "has_media",
        ],
    },
    # DEPRECATED: Use filter_category.py --profile tone_editor instead.
    # 피봇 후 Tone Editor는 category_analysis.json 축소본(category_tone_editor.json)을 사용합니다.
    # 이 프로파일은 구(summary.json) 기반이며 더 이상 사용되지 않습니다.
    "tone_editor": {
        "product_data_fields": [],
        "theme_fields": [
            "theme_name", "is_trending", "recent_mention_count",
        ],
        "evidence_quote_fields": [
            "text", "is_humorous", "review_id",
        ],
    },

    "broll": {
        "product_data_fields": [],
        "theme_fields": [
            "theme_name",
        ],
        "evidence_quote_fields": [
            "review_id", "has_media", "media_info",
            "media_paths", "media_descriptions",
        ],
        "filter_has_media_only": True,
    },

}


def filter_summary(data: dict, profile: dict) -> dict:
    """Apply a filter profile to summary.json data."""
    result = {}

    # Filter product_data
    pd_fields = profile.get("product_data_fields", [])
    if pd_fields and "product_data" in data:
        result["product_data"] = {
            k: v for k, v in data["product_data"].items() if k in pd_fields
        }

    # Filter themes
    theme_fields = set(profile.get("theme_fields", []))
    eq_fields = set(profile.get("evidence_quote_fields", []))
    filter_has_media = profile.get("filter_has_media_only", False)

    result["themes"] = []
    for theme in data.get("themes", []):
        filtered_theme = {
            k: v for k, v in theme.items()
            if k in theme_fields and k != "evidence_quotes"
        }

        if eq_fields and "evidence_quotes" in theme:
            quotes = theme["evidence_quotes"]
            if filter_has_media:
                quotes = [q for q in quotes if q.get("has_media", False)]
            filtered_theme["evidence_quotes"] = [
                {k: v for k, v in q.items() if k in eq_fields}
                for q in quotes
            ]

        result["themes"].append(filtered_theme)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: Filter summary.json for agent-specific profiles"
    )
    parser.add_argument(
        "--profile", required=True, choices=list(PROFILES.keys()),
        help="Agent profile name"
    )
    parser.add_argument(
        "--input", default=os.path.join(DATAS_DIR, "summary.json"),
        help="Source summary.json path (default: data/summary.json)"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output path (default: data/summary_{profile}.json)"
    )
    args = parser.parse_args()

    if args.output is None:
        args.output = os.path.join(DATAS_DIR, f"summary_{args.profile}.json")

    if not os.path.exists(args.input):
        print(json.dumps({"error": f"File not found: {args.input}"}))
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    filtered = filter_summary(data, PROFILES[args.profile])

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    # Machine-parseable result to stdout
    original_size = os.path.getsize(args.input)
    filtered_json = json.dumps(filtered, ensure_ascii=False, indent=2)
    filtered_size = len(filtered_json.encode("utf-8"))
    reduction = round(100 * (1 - filtered_size / original_size), 1)

    print(json.dumps({
        "profile": args.profile,
        "output": args.output,
        "original_bytes": original_size,
        "filtered_bytes": filtered_size,
        "reduction_pct": reduction,
    }), file=sys.stdout)

    print(f"[filter_summary] {args.profile}: {original_size:,} -> {filtered_size:,} bytes ({reduction}% reduction)", file=sys.stderr)


if __name__ == "__main__":
    main()
