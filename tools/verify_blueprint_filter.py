"""
Blueprint 필터 무결성 검증 스크립트.
category_analysis.json과 category_blueprint.json을 비교하여
핵심 데이터가 손실 없이 보존되었는지 확인.
"""
import json
import sys


def main():
    with open("data/category_analysis.json", "r", encoding="utf-8") as f:
        original = json.load(f)
    with open("data/category_blueprint.json", "r", encoding="utf-8") as f:
        filtered = json.load(f)

    errors = []

    # CHECK 1: product_count 보존
    if filtered.get("product_count") != original.get("product_count"):
        errors.append("product_count mismatch")

    # CHECK 2: products 핵심 필드 보존
    for i, op in enumerate(original.get("products", [])):
        fp = filtered["products"][i]
        for key in ["product_id", "product_name", "sold_last_month", "population_gap",
                     "all_time_rating_avg", "all_time_rating_count",
                     "recent_review_rating_avg", "recent_review_count",
                     "reviews_analyzed_count"]:
            if fp.get(key) != op.get(key):
                errors.append(f"products[{i}].{key} mismatch")
        if fp.get("trap_candidate") != op.get("trap_candidate"):
            errors.append(f"products[{i}].trap_candidate mismatch")

    # CHECK 3: 제거된 필드 확인
    for bad_root in ["category_name", "dataset_snapshot", "previous_snapshot", "delta"]:
        if bad_root in filtered:
            errors.append(f"root.{bad_root} should be removed")
    for i, fp in enumerate(filtered.get("products", [])):
        for bad_key in ["product_category", "summary_path", "recent_period_text", "recent_days"]:
            if bad_key in fp:
                errors.append(f"products[{i}].{bad_key} should be removed")

    # CHECK 4: common_themes 수 보존
    if len(filtered["common_themes"]) != len(original["common_themes"]):
        errors.append("common_themes count mismatch")

    # CHECK 5: rankings 수치 보존
    for i, ot in enumerate(original["common_themes"]):
        ft = filtered["common_themes"][i]
        if ft["theme_name"] != ot["theme_name"]:
            errors.append(f"theme[{i}] name mismatch")
        if ft["category_pattern_type"] != ot["category_pattern_type"]:
            errors.append(f"theme[{i}] pattern_type mismatch")
        if len(ft["rankings"]) != len(ot["rankings"]):
            errors.append(f"theme[{i}] rankings count mismatch")
        for j, or_ in enumerate(ot["rankings"]):
            fr_ = ft["rankings"][j]
            for key in ["rank", "product_id", "mention_count", "positive_ratio",
                         "positive_count", "negative_count"]:
                if fr_.get(key) != or_.get(key):
                    errors.append(f"theme[{i}].rankings[{j}].{key} mismatch")

    # CHECK 6: contradiction_pairs 수 보존 + quote text 보존 + 메타 제거 확인
    for i, ot in enumerate(original["common_themes"]):
        ft = filtered["common_themes"][i]
        if len(ft["contradiction_pairs"]) != len(ot["contradiction_pairs"]):
            errors.append(f"theme[{i}] contradiction_pairs count mismatch")
        for j, op_ in enumerate(ot["contradiction_pairs"]):
            fp_ = ft["contradiction_pairs"][j]
            # quote text 보존
            for side in ["positive_quote", "negative_quote"]:
                oq = op_.get(side)
                fq = fp_.get(side)
                if oq and fq:
                    if fq.get("text") != oq.get("text"):
                        errors.append(f"theme[{i}].cp[{j}].{side}.text mismatch")
                    # 제거된 필드 확인
                    for bad_key in ["sentiment", "review_date", "selection_reason",
                                    "has_media", "media_info"]:
                        if bad_key in fq:
                            errors.append(f"theme[{i}].cp[{j}].{side}.{bad_key} should be removed")
            # resolution_hypothesis 보존
            if fp_.get("resolution_hypothesis") != op_.get("resolution_hypothesis"):
                errors.append(f"theme[{i}].cp[{j}].resolution_hypothesis mismatch")

    # CHECK 7: unique_strengths 보존
    if len(filtered["unique_strengths"]) != len(original["unique_strengths"]):
        errors.append("unique_strengths count mismatch")
    for i, ous in enumerate(original["unique_strengths"]):
        fus = filtered["unique_strengths"][i]
        for key in ["product_id", "theme_name", "positive_ratio", "mention_count",
                     "why_unique", "recommended_use_case"]:
            if fus.get(key) != ous.get(key):
                errors.append(f"unique_strengths[{i}].{key} mismatch")

    # CHECK 8: category_intelligence 완전 보존
    if filtered["category_intelligence"] != original["category_intelligence"]:
        errors.append("category_intelligence mismatch")

    # 결과 출력
    if errors:
        print(f"FAIL: {len(errors)} errors found")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("PASS: All 8 checks passed. Data integrity verified.")


if __name__ == "__main__":
    main()
