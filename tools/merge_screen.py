import json
import logging
from pathlib import Path

from config import contracts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

def is_decision_accepted(decision_dict):
    c = contracts().get("screen_schema", {})
    keys = c.get("decision_keys", ["accepted", "decision"])
    # Note: JSON parsing converts unquoted true to python True, but list might contain strings
    # We will check explicitly
    valid_vals = []
    for v in c.get("accepted_values", []):
        if isinstance(v, str):
            valid_vals.append(v.lower())
        else:
            valid_vals.append(v)
            
    for k in keys:
        val = decision_dict.get(k)
        if val is True and True in valid_vals:
            return True
        if isinstance(val, str) and val.lower() in valid_vals:
            return True
    return False

def main():
    candidates_path = Path("data/category_candidates.json")
    decisions_path = Path("data/screen_decisions.json")
    output_path = Path("data/category_screened.json")

    if not candidates_path.exists():
        logger.error(f"Missing {candidates_path}")
        return
    if not decisions_path.exists():
        logger.error(f"Missing {decisions_path}")
        return

    with open(candidates_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(decisions_path, "r", encoding="utf-8") as f:
        decisions = json.load(f)

    # Build maps for O(1) lookup
    cp_decisions = {}
    theme_pattern_overrides = {}
    for d in decisions.get("cross_product_decisions", []):
        theme_name = d.get("theme_name")
        pids = tuple(sorted(d.get("product_ids", [])))
        cp_decisions[(theme_name, pids)] = d
        if d.get("override_pattern_type"):
            theme_pattern_overrides[theme_name] = d.get("override_pattern_type")

    us_decisions = {
        f"{d['product_id']}_{d['theme_name']}": d
        for d in decisions.get("unique_strength_decisions", [])
    }

    # 1. Process common_themes
    for theme in data.get("common_themes", []):
        theme_name = theme.get("theme_name")
        
        # Override pattern type if provided
        override = theme_pattern_overrides.get(theme_name)
        if override:
            theme["category_pattern_type"] = override

        # Filter contradiction pairs
        new_pairs = []
        for pair in theme.get("contradiction_pairs", []):
            if "ratio_gap" in pair:
                del pair["ratio_gap"]

            if pair.get("type") == "cross_product":
                pids = tuple(sorted(pair.get("product_ids", [])))
                decision = cp_decisions.get((theme_name, pids))
                if decision:
                    if is_decision_accepted(decision):
                        new_pairs.append(pair)
            else:
                # within_product: keep as is
                new_pairs.append(pair)
        
        theme["contradiction_pairs"] = new_pairs

    # 2. Process unique_strengths
    new_us = []
    for us in data.get("unique_strengths", []):
        key = f"{us.get('product_id')}_{us.get('theme_name')}"
        if key in us_decisions:
            decision = us_decisions[key]
            if is_decision_accepted(decision):
                if "ratio_gap" in us:
                    del us["ratio_gap"]
                new_us.append(us)
            
    data["unique_strengths"] = new_us

    # 3. Exclusive feature detection
    # -- common_themes에 없는 theme_name을 가진 unique_strength는
    # -- 해당 제품만 보유한 독점 기능 (coverage==1에서 파생)
    common_theme_names = {t.get("theme_name") for t in data.get("common_themes", [])}
    for us in data["unique_strengths"]:
        us["is_exclusive_feature"] = us.get("theme_name") not in common_theme_names

    # 4. Zero-strength product detection
    # -- accepted unique_strength가 0인 제품에 needs_narrative_anchor 플래그 추가
    # -- Category Analyst가 이 플래그를 보고 보상 서술(product_narrative_anchor) 생성
    all_product_ids = {p.get("product_id") for p in data.get("products", [])}
    products_with_strengths = {us.get("product_id") for us in data["unique_strengths"]}
    zero_strength_products = all_product_ids - products_with_strengths

    for product in data.get("products", []):
        pid = product.get("product_id")
        if pid in zero_strength_products:
            product["needs_narrative_anchor"] = True
            # -- within_product contradiction이 있는 테마 목록 집계
            within_themes = []
            for theme in data.get("common_themes", []):
                for cp in theme.get("contradiction_pairs", []):
                    if cp.get("type") == "within_product" and cp.get("product_id") == pid:
                        within_themes.append(theme.get("theme_name"))
                        break
            product["within_contradiction_themes"] = within_themes
            logger.warning(
                f"Zero-strength product detected: {pid} "
                f"(within_contradiction_themes: {within_themes})"
            )
        else:
            product["needs_narrative_anchor"] = False

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"Merged screen decisions into {output_path}")

if __name__ == "__main__":
    main()
