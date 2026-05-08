"""
Extract Visual Datasets — writer_brief.md에서 시각화 가능한 모든 수치 데이터를
chart-ready JSON으로 추출.

Input:  data/category_writer.json, data/category_analysis.json
Output: data/visual_datasets.json

Usage:
    python tools/extract_visual_datasets.py
"""
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import DATAS_DIR


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract(data, analysis_data=None):
    from datetime import datetime, timedelta

    products_map = {p["product_id"]: p["product_name"] for p in data.get("products", [])}
    short_names = {pid: name.split()[0] for pid, name in products_map.items()}

    # Pre-compute collected_through for review window calculation
    collected_through = None
    if analysis_data:
        collected_through = analysis_data.get("dataset_snapshot", {}).get("collected_through")

    result = {}

    # ── 1. Product Overview ──
    result["product_overview"] = []
    for p in data.get("products", []):
        entry = {
            "product_id": p["product_id"],
            "name": products_map[p["product_id"]],
            "short_name": short_names[p["product_id"]],
            "sold_last_month": p.get("sold_last_month"),
            "all_time_rating": p.get("all_time_rating_avg"),
            "recent_rating": p.get("recent_review_rating_avg"),
            "population_gap": p.get("population_gap"),
            "recent_days": p.get("recent_days"),
            "recent_review_count": p.get("recent_review_count"),
            "reviews_analyzed_count": p.get("reviews_analyzed_count"),
            "is_trap": p.get("trap_candidate", {}).get("is_trap", False),
        }
        # Recent review window dates
        recent_days = p.get("recent_days")
        if collected_through and recent_days is not None:
            end_date = datetime.strptime(collected_through, "%Y-%m-%d")
            start_date = end_date - timedelta(days=recent_days)
            entry["window_start"] = start_date.strftime("%Y-%m-%d")
            entry["window_end"] = collected_through
        result["product_overview"].append(entry)

    # ── 2. Theme Spread Tables ──
    result["theme_spreads"] = []
    for theme in data.get("common_themes", []):
        rankings = theme.get("rankings", [])
        ratios = [r.get("positive_ratio", 0) for r in rankings]
        spread_pp = round((max(ratios) - min(ratios)) * 100, 1) if ratios else 0
        min_mentions = min((r.get("mention_count", 0) for r in rankings), default=0)

        theme_entry = {
            "theme_name": theme["theme_name"],
            "pattern_type": theme.get("category_pattern_type"),
            "spread_pp": spread_pp,
            "min_mentions": min_mentions,
            "products": [],
        }
        for r in rankings:
            theme_entry["products"].append({
                "product_id": r["product_id"],
                "short_name": short_names.get(r["product_id"], r["product_id"]),
                "mention_count": r.get("mention_count", 0),
                "positive_count": r.get("positive_count", 0),
                "negative_count": r.get("negative_count", 0),
                "positive_ratio": r.get("positive_ratio", 0),
                "positive_pct": round(r.get("positive_ratio", 0) * 100, 1),
            })
        result["theme_spreads"].append(theme_entry)

    # ── 3. Landmine Heatmap ──
    result["landmine_heatmap"] = []
    for p in data.get("products", []):
        pid = p["product_id"]
        weak_themes = []
        for theme in data.get("common_themes", []):
            for r in theme.get("rankings", []):
                if r["product_id"] == pid and r.get("positive_ratio", 1) < 0.3:
                    weak_themes.append({
                        "theme_name": theme["theme_name"],
                        "positive_pct": round(r["positive_ratio"] * 100, 1),
                    })
        result["landmine_heatmap"].append({
            "product_id": pid,
            "name": products_map[pid],
            "short_name": short_names[pid],
            "population_gap": p.get("population_gap"),
            "is_trap": p.get("trap_candidate", {}).get("is_trap", False),
            "weak_themes": weak_themes,
            "weak_count": len(weak_themes),
        })

    # ── 4. Standout Data ──
    result["standout_data"] = []
    for us in data.get("unique_strengths", []):
        result["standout_data"].append({
            "product_id": us["product_id"],
            "short_name": short_names.get(us["product_id"], us["product_id"]),
            "theme_name": us["theme_name"],
            "positive_ratio": us.get("positive_ratio", 0),
            "positive_pct": round(us.get("positive_ratio", 0) * 100, 1),
            "mention_count": us.get("mention_count", 0),
        })

    # ── 5. Cross-Product Gap Rankings ──
    gaps = []
    for theme in data.get("common_themes", []):
        rankings = theme.get("rankings", [])
        if len(rankings) < 2:
            continue
        sorted_r = sorted(rankings, key=lambda x: x.get("positive_ratio", 0), reverse=True)
        best = sorted_r[0]
        worst = sorted_r[-1]
        gap_pp = round((best["positive_ratio"] - worst["positive_ratio"]) * 100, 1)
        gaps.append({
            "theme_name": theme["theme_name"],
            "pattern_type": theme.get("category_pattern_type"),
            "gap_pp": gap_pp,
            "best_product": short_names.get(best["product_id"], best["product_id"]),
            "best_pct": round(best["positive_ratio"] * 100, 1),
            "worst_product": short_names.get(worst["product_id"], worst["product_id"]),
            "worst_pct": round(worst["positive_ratio"] * 100, 1),
        })
    result["cross_product_gaps"] = sorted(gaps, key=lambda x: -x["gap_pp"])

    # ── 6. Trap Severity ──
    result["trap_severity"] = []
    for p in data.get("products", []):
        if not p.get("trap_candidate", {}).get("is_trap"):
            continue
        # Count negative themes (positive_ratio < 0.5)
        neg_count = 0
        total_themes = len(data.get("common_themes", []))
        for theme in data.get("common_themes", []):
            for r in theme.get("rankings", []):
                if r["product_id"] == p["product_id"] and r.get("positive_ratio", 0) < 0.5:
                    neg_count += 1
        result["trap_severity"].append({
            "product_id": p["product_id"],
            "short_name": short_names[p["product_id"]],
            "all_time_rating": p.get("all_time_rating_avg"),
            "recent_rating": p.get("recent_review_rating_avg"),
            "population_gap": p.get("population_gap"),
            "negative_themes": neg_count,
            "total_themes": total_themes,
        })
    result["trap_severity"] = sorted(result["trap_severity"], key=lambda x: -x["population_gap"])

    # ── 7. Dataset Snapshot (from category_analysis.json) ──
    if analysis_data:
        snapshot = analysis_data.get("dataset_snapshot", {})
        result["dataset_snapshot"] = {
            "collected_through": snapshot.get("collected_through"),
            "total_reviews_analyzed": snapshot.get("total_reviews_analyzed"),
            "product_count": snapshot.get("product_count"),
        }

    return result


def main():
    input_path = os.path.join(DATAS_DIR, "category_writer.json")
    analysis_path = os.path.join(DATAS_DIR, "category_analysis.json")
    output_path = os.path.join(DATAS_DIR, "visual_datasets.json")

    if not os.path.exists(input_path):
        print(f"ERROR: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    data = load_json(input_path)
    analysis_data = load_json(analysis_path) if os.path.exists(analysis_path) else None
    datasets = extract(data, analysis_data)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(datasets, f, ensure_ascii=False, indent=2)

    size = os.path.getsize(output_path)
    print(f"extract_visual_datasets.py: {output_path} ({size:,} bytes)")
    print(f"  Datasets: {len(datasets)} categories")
    for key, val in datasets.items():
        print(f"  - {key}: {len(val)} entries")


if __name__ == "__main__":
    main()
