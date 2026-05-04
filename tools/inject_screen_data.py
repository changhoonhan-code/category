import json
import os
from pathlib import Path

def get_theme_for_scene(scene):
    return scene.get("scene_subject")

def main():
    base_dir = Path("d:/GEMINI/data")
    category_file = base_dir / "category_analysis.json"
    outline_file = base_dir / "comparison_outline.json"
    script_file = base_dir / "script_output.json"

    if not (category_file.exists() and outline_file.exists() and script_file.exists()):
        print("Required files not found. Check data directory.")
        return

    with open(category_file, "r", encoding="utf-8") as f:
        category_data = json.load(f)
    
    with open(outline_file, "r", encoding="utf-8") as f:
        outline_data = json.load(f)

    with open(script_file, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    # 1. Map scene_id to theme_name from outline
    scene_to_theme = {}
    for scene in outline_data.get("scenes", []):
        if "scene_subject" in scene:
            scene_to_theme[scene["scene_id"]] = scene["scene_subject"]

    # 2. Map theme_name to rankings
    theme_rankings = {}
    for theme in category_data.get("common_themes", []):
        theme_name = theme.get("theme_name")
        if theme_name:
            theme_rankings[theme_name] = theme.get("rankings", [])

    # 3. Loop through script blocks (nested in scenes)
    for scene in script_data.get("scenes", []):
        for block in scene.get("blocks", []):
            block_id = block.get("block_id", "")
            scene_id = scene.get("scene_id", "")
            screen_data = []

            # theme_ranking — Phase 2B 4-template 블록 접미사 전체 매칭
            theme_suffixes = [
                "_showdown", "_fallout", "_context",   # Template A: Direct Confrontation
                "_diagnosis", "_spectrum",              # Template B: Structural Analysis
                "_baseline",                            # Template C: Value Proof
                "_profiles", "_tradeoff",               # Template D: Use-Case Split
            ]
            if any(suffix in block_id for suffix in theme_suffixes):
                theme_name = scene_to_theme.get(scene_id)
                if theme_name and theme_name in theme_rankings:
                    # Remove insight_level if present
                    chart_data = []
                    for rank in theme_rankings[theme_name]:
                        rank_copy = dict(rank)
                        rank_copy.pop("insight_level", None)
                        chart_data.append(rank_copy)
                    
                    screen_data.append({
                        "data_type": "theme_ranking",
                        "theme_name": theme_name,
                        "chart_data": chart_data
                    })
            
            # product_overview
            elif block_id.startswith("rating_overview_"):
                chart_data = []
                for prod in category_data.get("products", []):
                    # Extract relevant fields
                    prod_data = {
                        "product_id": prod.get("product_id"),
                        "product_name": prod.get("product_name"),
                        "all_time_rating_avg": prod.get("all_time_rating_avg"),
                        "all_time_rating_count": prod.get("all_time_rating_count"),
                        "recent_review_rating_avg": prod.get("recent_review_rating_avg"),
                        "recent_review_count": prod.get("recent_review_count"),
                        "population_gap": prod.get("population_gap"),
                        "sold_last_month": prod.get("sold_last_month", "N/A")
                    }
                    chart_data.append(prod_data)
                    
                screen_data.append({
                    "data_type": "product_overview",
                    "chart_data": chart_data
                })

            # single_stat
            elif block_id.startswith("hook_") or block_id.startswith("verdict_"):
                dataset_snapshot = category_data.get("dataset_snapshot", {})
                total_reviews = dataset_snapshot.get("total_reviews_analyzed", 0)
                screen_data.append({
                    "data_type": "single_stat",
                    "label": "Total Reviews Analyzed",
                    "value": total_reviews,
                    "unit": "reviews"
                })
            
            block["screen_data"] = screen_data

    with open(script_file, "w", encoding="utf-8") as f:
        json.dump(script_data, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully injected screen_data into {script_file}")

if __name__ == "__main__":
    main()
