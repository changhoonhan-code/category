"""
Filter Data CLI Tool — Fetches scene-specific reviews for the Showrunner.
"""
import argparse
import glob
import json
import os
import sys

import pandas as pd

def build_media_index(movies_glob: str, photos_glob: str) -> set:
    """Builds a simple set of review_ids that have media."""
    has_media = set()
    for path in glob.glob(movies_glob) + glob.glob(photos_glob):
        try:
            with open(path, "r", encoding="utf-8") as f:
                m = json.load(f)
            if isinstance(m, list):
                m = m[0] if m else {}
            rid = m.get("review_id")
            if rid:
                has_media.add(rid)
        except Exception:
            pass
    return has_media

def main():
    parser = argparse.ArgumentParser(description="ReviewLens: Filter reviews by theme.")
    parser.add_argument("--theme", type=str, required=True, help="Canonical theme name to filter by")
    parser.add_argument("--input-csv", type=str, default="data/buying_guide_extracted.csv")
    parser.add_argument("--input-dir", type=str, default="one_product")
    args = parser.parse_args()

    if not os.path.exists(args.input_csv):
        print(json.dumps({"error": f"File not found: {args.input_csv}"}))
        sys.exit(1)

    df = pd.read_csv(args.input_csv)
    
    if "canonical_theme" not in df.columns:
        print(json.dumps({"error": "CSV missing canonical_theme column"}))
        sys.exit(1)

    filtered = df[df["canonical_theme"] == args.theme]
    
    if filtered.empty:
        print(json.dumps([]))
        return

    media_set = build_media_index(
        os.path.join(args.input_dir, "movies", "*_meta.json"),
        os.path.join(args.input_dir, "photos", "*_meta.json")
    )

    results = []
    for _, row in filtered.iterrows():
        rid = str(row.get("review_id", ""))
        results.append({
            "review_id": rid,
            "core_aspect": str(row.get("core_aspect", "")),
            "sentiment": str(row.get("sentiment", "")),
            "evidence_quote": str(row.get("evidence_quote", "")),
            "user_profile": str(row.get("user_profile", "")),
            "time_context": str(row.get("time_context", "")),
            "has_media": rid in media_set
        })

    # Sort so that media-attached and longer quotes appear first
    results.sort(key=lambda x: (x["has_media"], len(x["evidence_quote"])), reverse=True)

    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
