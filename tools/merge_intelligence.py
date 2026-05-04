import json
import logging
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, model_validator, ValidationError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)


# -- Pydantic: resolution_hypothesis 조건부 필드 검증 --
# within_product일 때 product_id 필수, cross_product일 때 product_ids 필수.
# LLM이 키 이름을 혼동하거나 누락하면 여기서 즉시 잡아냄.
class ResolutionHypothesis(BaseModel):
    type: Literal["within_product", "cross_product"]
    product_id: Optional[str] = None
    product_ids: Optional[list[str]] = None
    hypothesis: str

    @model_validator(mode="after")
    def check_conditional_fields(self):
        if self.type == "within_product" and not self.product_id:
            raise ValueError(
                "within_product type requires 'product_id' field"
            )
        if self.type == "cross_product" and not self.product_ids:
            raise ValueError(
                "cross_product type requires 'product_ids' field"
            )
        return self

def main():
    screened_path = Path("data/category_screened.json")
    results_path = Path("data/intelligence_results.json")
    output_path = Path("data/category_analysis.json")

    if not screened_path.exists():
        logger.error(f"Missing {screened_path}")
        return
    if not results_path.exists():
        logger.error(f"Missing {results_path}")
        return

    with open(screened_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    # -- theme_assessments를 Pydantic으로 검증 후 맵 구성 --
    theme_assess_map = {}
    validation_errors = 0
    for ta in results.get("theme_assessments", []):
        theme_name = ta.get("theme_name", "UNKNOWN")
        # resolution_hypotheses 각 항목을 Pydantic 모델로 검증
        validated_hypotheses = []
        for i, h in enumerate(ta.get("resolution_hypotheses", [])):
            try:
                validated = ResolutionHypothesis(**h)
                validated_hypotheses.append(validated.model_dump())
            except ValidationError as e:
                validation_errors += 1
                logger.error(
                    f"Schema violation in theme '{theme_name}', "
                    f"hypothesis[{i}]: {e.errors()[0]['msg']} "
                    f"(raw data: {json.dumps(h, ensure_ascii=False)[:120]})"
                )
                # 검증 실패한 hypothesis는 건너뜀 (파이프라인 중단 방지)
        ta["resolution_hypotheses"] = validated_hypotheses
        theme_assess_map[theme_name] = ta

    if validation_errors:
        logger.warning(
            f"{validation_errors} hypothesis(es) failed validation and were skipped"
        )

    # "product_a (Product Name)" 포맷 방어 처리
    uniq_assess_map = {}
    for u in results.get("unique_assessments", []):
        clean_pid = u["product_id"].split()[0]
        uniq_assess_map[f"{clean_pid}_{u['theme_name']}"] = u

    # 1. Process common_themes
    matched_count = 0
    unmatched_count = 0
    for ct in data.get("common_themes", []):
        ta = theme_assess_map.get(ct["theme_name"])
        if ta:
            ct["category_pattern"] = ta.get("category_pattern", "")
            if "category_pattern_type" in ta:
                ct["category_pattern_type"] = ta["category_pattern_type"]
            hypotheses = ta.get("resolution_hypotheses", [])
            for cp in ct.get("contradiction_pairs", []):
                cp_type = cp.get("type")
                match_text = ""
                for h in hypotheses:
                    if h.get("type") != cp_type:
                        continue
                    if cp_type == "within_product" and h.get("product_id") == cp.get("product_id"):
                        match_text = h.get("hypothesis")
                        break
                    elif cp_type == "cross_product":
                        h_pids = h.get("product_ids") or []
                        cp_pids = cp.get("product_ids") or []
                        if set(h_pids) == set(cp_pids):
                            match_text = h.get("hypothesis")
                            break
                cp["resolution_hypothesis"] = match_text
                # 매칭 실패 경고 (silent failure 방지)
                if match_text:
                    matched_count += 1
                else:
                    unmatched_count += 1
                    product_ref = cp.get("product_id") or cp.get("product_ids")
                    logger.warning(
                        f"No matching hypothesis for {cp_type} contradiction "
                        f"in theme '{ct['theme_name']}' "
                        f"(product: {product_ref})"
                    )

    # 2. Process unique_strengths
    for us in data.get("unique_strengths", []):
        key = f"{us['product_id']}_{us['theme_name']}"
        ua = uniq_assess_map.get(key)
        if ua:
            us["why_unique"] = ua.get("why_unique", "")
            us["recommended_use_case"] = ua.get("recommended_use_case", "")

    # 3. Process category_intelligence
    data["category_intelligence"] = results.get("category_intelligence")

    # 4. Process product_narrative_anchors (zero-strength products)
    # -- Category Analyst가 needs_narrative_anchor 제품에 대해 생성한 포지셔닝 데이터를
    # -- products 배열에 merge하여 Blueprint Designer가 standout_mapping에 활용 가능하도록 함
    anchor_map = {}
    for anchor in results.get("product_narrative_anchors", []):
        clean_pid = anchor.get("product_id", "").split()[0]
        anchor_map[clean_pid] = anchor

    anchors_merged = 0
    for product in data.get("products", []):
        pid = product.get("product_id")
        if pid in anchor_map:
            a = anchor_map[pid]
            product["narrative_anchor"] = {
                "narrative_position": a.get("narrative_position", ""),
                "recommended_use_case": a.get("recommended_use_case", ""),
                "data_basis": a.get("data_basis", []),
            }
            anchors_merged += 1
            logger.info(f"Narrative anchor merged for {pid}")

    if anchor_map and anchors_merged == 0:
        logger.warning(
            f"product_narrative_anchors present ({len(anchor_map)}) "
            f"but none matched product_ids in data"
        )

    # Write final output (this should be fully compatible with legacy category_analysis.json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"Final category analysis saved to {output_path}")
    logger.info(
        f"Merge summary: {matched_count} hypotheses matched, "
        f"{unmatched_count} unmatched, "
        f"{validation_errors} validation errors"
    )

if __name__ == "__main__":
    main()
