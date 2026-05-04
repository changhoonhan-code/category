"""
Search Quotes — On-demand review quote retrieval for the Quote Curator agent.

Queries the full theme_analysis.json per product to find impactful evidence
quotes that match a given canonical theme and sentiment.

Usage:
    python tools/search_quotes.py --product product_a --theme "Active Noise Cancellation"
    python tools/search_quotes.py --product product_a --theme "Battery Life" --sentiment Positive --limit 7
    python tools/search_quotes.py --product product_a --theme "Audio Quality" --exclude R1JDQN4V9EWNO8,R1BFDEG7QXHOJM

Output: JSON array of enriched quote objects with highlight_phrases and impact_score.
"""
import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ── Default paths ────────────────────────────────────────────────────────────
DEFAULT_DATA_DIR = Path("data/products")
DEFAULT_RAW_DIR = Path("products")
DEFAULT_CLUSTER_MAP = Path("data/intermediate/theme_clusters.json")


# ── Theme cluster mapping ────────────────────────────────────────────────────

def load_cluster_map(cluster_path: Path) -> Dict[str, Dict[str, List[str]]]:
    """
    Build a lookup: canonical_name -> { product_id: [original_theme_names] }

    Returns:
        {
            "Audio Quality": {
                "product_a": ["Audio Quality", "Bass Performance"],
                "product_b": ["Audio Clarity"],
                ...
            }
        }
    """
    if not cluster_path.exists():
        return {}

    with cluster_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    result: Dict[str, Dict[str, List[str]]] = {}
    for cluster in data.get("clusters", []):
        canonical = cluster.get("canonical_name", "")
        members_by_product: Dict[str, List[str]] = {}
        for member in cluster.get("members", []):
            pid = member.get("product_id", "")
            otn = member.get("original_theme_name", "")
            members_by_product.setdefault(pid, []).append(otn)
        result[canonical] = members_by_product

    return result


def resolve_theme_names(
    canonical_theme: str,
    product_id: str,
    cluster_map: Dict[str, Dict[str, List[str]]],
) -> List[str]:
    """
    Given a canonical theme name (e.g., "Audio Quality") and a product_id,
    return the list of original theme names to search in theme_analysis.json.

    Falls back to exact match if cluster map doesn't have the mapping.
    """
    if canonical_theme in cluster_map:
        product_themes = cluster_map[canonical_theme].get(product_id, [])
        if product_themes:
            return product_themes

    # Fallback: use canonical name as-is (might match directly)
    return [canonical_theme]


# ── Review CSV enrichment ────────────────────────────────────────────────────

def load_review_csv(csv_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load cleaned_reviews.csv into a lookup by review_id.

    Returns:
        { "R3DUQ7DK7KVDZJ": { "rating": 5, "helpful": 12, "date": "2025-11-27",
                               "has_media": true, "media_info": [...] } }
    """
    if not csv_path.exists():
        return {}

    result: Dict[str, Dict[str, Any]] = {}
    with csv_path.open("r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = row.get("review_id", "").strip()
            if not rid:
                continue

            # Parse images/media
            images_raw = row.get("images", "[]")
            movie_url = row.get("movie_url", "").strip()
            try:
                images = json.loads(images_raw) if images_raw else []
            except (json.JSONDecodeError, TypeError):
                images = []

            has_media = bool(images) or bool(movie_url)
            media_info = []
            if images:
                media_info.extend([{"type": "image", "url": img} for img in images[:3]])
            if movie_url:
                media_info.append({"type": "video", "url": movie_url})

            # Parse helpful count
            helpful_str = row.get("helpful", "0").strip()
            try:
                helpful = int(helpful_str) if helpful_str else 0
            except ValueError:
                helpful = 0

            result[rid] = {
                "star_rating": int(row.get("rating", 0) or 0),
                "helpful_count": helpful,
                "review_date": row.get("date", "").strip(),
                "has_media": has_media,
                "media_info": media_info,
            }

    return result


# ── Impact scoring ───────────────────────────────────────────────────────────

def compute_impact_score(
    helpful_count: int,
    has_media: bool,
    review_date: str,
    reference_date: Optional[datetime] = None,
) -> float:
    """
    score = (helpful_count × 2) + (has_media × 5) + (recency × 3)
    recency = max(0, 1 - days_ago / 365)
    """
    ref = reference_date or datetime.now()

    # Recency calculation
    recency = 0.0
    if review_date:
        try:
            rd = datetime.strptime(review_date, "%Y-%m-%d")
            days_ago = (ref - rd).days
            recency = max(0.0, 1.0 - days_ago / 365.0)
        except ValueError:
            pass

    score = (helpful_count * 2) + (5 if has_media else 0) + (recency * 3)
    return round(score, 2)


# ── Main search logic ────────────────────────────────────────────────────────

def search_quotes(
    product_id: str,
    canonical_theme: str,
    sentiment: Optional[str] = None,
    limit: int = 10,
    exclude_ids: Optional[Set[str]] = None,
    cluster_map_path: Path = DEFAULT_CLUSTER_MAP,
    data_dir: Path = DEFAULT_DATA_DIR,
    raw_dir: Path = DEFAULT_RAW_DIR,
) -> List[Dict[str, Any]]:
    """
    Search theme_analysis.json for quotes matching the given criteria.
    Enrich with CSV data, score, extract highlights, and return top results.
    """
    exclude = exclude_ids or set()

    # ── 1. Load cluster map and resolve theme names ──────────────────────────
    cluster_map = load_cluster_map(cluster_map_path)
    theme_names = resolve_theme_names(canonical_theme, product_id, cluster_map)

    # ── 2. Load theme_analysis.json ──────────────────────────────────────────
    analysis_path = data_dir / product_id / "theme_analysis.json"
    if not analysis_path.exists():
        print(json.dumps({"error": f"File not found: {analysis_path}"}),
              file=sys.stderr)
        return []

    with analysis_path.open("r", encoding="utf-8") as f:
        analysis = json.load(f)

    # ── 3. Collect matching quotes ───────────────────────────────────────────
    theme_names_lower = {t.lower() for t in theme_names}
    raw_quotes: List[Dict[str, Any]] = []

    for theme_obj in analysis.get("themes", []):
        tn = theme_obj.get("theme", "")
        if tn.lower() not in theme_names_lower:
            continue

        for eq in theme_obj.get("evidence_quotes", []):
            rid = eq.get("review_id", "")
            if rid in exclude:
                continue

            eq_sentiment = eq.get("sentiment", "")
            if sentiment and eq_sentiment.lower() != sentiment.lower():
                continue

            raw_quotes.append({
                "review_id": rid,
                "text": eq.get("evidence_quote", ""),
                "sentiment": eq_sentiment,
                "core_aspect": eq.get("core_aspect", ""),
                "user_profile": eq.get("user_profile"),
                "compared_to": eq.get("compared_to"),
                "source_theme": tn,
            })

    # ── 4. Enrich with CSV data ──────────────────────────────────────────────
    csv_path = raw_dir / product_id / "cleaned_reviews.csv"
    csv_data = load_review_csv(csv_path)

    enriched: List[Dict[str, Any]] = []
    for q in raw_quotes:
        rid = q["review_id"]
        csv_row = csv_data.get(rid, {})

        star_rating = csv_row.get("star_rating", 0)
        helpful_count = csv_row.get("helpful_count", 0)
        review_date = csv_row.get("review_date", "")
        has_media = csv_row.get("has_media", False)
        media_info = csv_row.get("media_info", [])

        impact = compute_impact_score(helpful_count, has_media, review_date)

        enriched.append({
            "text": q["text"],
            "sentiment": q["sentiment"],
            "star_rating": star_rating,
            "review_id": rid,
            "review_date": review_date,
            "helpful_count": helpful_count,
            "impact_score": impact,
            "selection_reason": "supplementary",
            "has_media": has_media,
            "media_info": media_info,
            "product_id": product_id,
            "core_aspect": q["core_aspect"],
            "user_profile": q["user_profile"],
        })

    # ── 5. Sort by impact score (descending) and return top N ────────────────
    enriched.sort(key=lambda x: -x["impact_score"])

    return enriched[:limit]


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: Search quotes from theme_analysis.json for Quote Curator"
    )
    parser.add_argument(
        "--product", required=True,
        help="Product ID (e.g., product_a)"
    )
    parser.add_argument(
        "--theme", required=True,
        help="Canonical theme name (e.g., 'Active Noise Cancellation')"
    )
    parser.add_argument(
        "--sentiment", default=None,
        help="Filter by sentiment: Positive, Negative, or Neutral"
    )
    parser.add_argument(
        "--limit", type=int, default=10,
        help="Maximum number of quotes to return (default: 10)"
    )
    parser.add_argument(
        "--exclude", default="",
        help="Comma-separated review_ids to exclude (deduplication)"
    )
    parser.add_argument(
        "--cluster-map", default=str(DEFAULT_CLUSTER_MAP),
        help=f"Path to theme_clusters.json (default: {DEFAULT_CLUSTER_MAP})"
    )
    parser.add_argument(
        "--data-dir", default=str(DEFAULT_DATA_DIR),
        help=f"Path to data/products/ directory (default: {DEFAULT_DATA_DIR})"
    )
    parser.add_argument(
        "--raw-dir", default=str(DEFAULT_RAW_DIR),
        help=f"Path to products/ directory with CSVs (default: {DEFAULT_RAW_DIR})"
    )
    args = parser.parse_args()

    exclude_ids = set(args.exclude.split(",")) if args.exclude else set()

    results = search_quotes(
        product_id=args.product,
        canonical_theme=args.theme,
        sentiment=args.sentiment,
        limit=args.limit,
        exclude_ids=exclude_ids,
        cluster_map_path=Path(args.cluster_map),
        data_dir=Path(args.data_dir),
        raw_dir=Path(args.raw_dir),
    )

    # Summary to stderr
    print(
        f"[search_quotes] {args.product} / {args.theme}"
        f" → {len(results)} quotes returned (limit={args.limit})",
        file=sys.stderr,
    )

    # JSON output to stdout
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
