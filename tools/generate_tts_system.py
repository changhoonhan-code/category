"""
generate_tts_system.py

Phase 2 Step 0.5 -- TTS System Prompt Base Generator.

시스템 프롬프트 템플릿을 읽어 동적 플레이스홀더를
category_analysis.json의 실제 데이터로 치환한 뒤
tmp/tts_system_base.txt로 출력한다.

치환 대상 플레이스홀더:
  - {{TOTAL_REVIEWS}}  : 전 제품 리뷰 수 합산
  - {{CATEGORY_NAME}}  : 카테고리명 (예: "earbuds over $200")
  - {{PRODUCT_COUNT}}  : 분석 대상 제품 수
  - {{PRODUCT_LIST}}   : 제품명 자연어 리스트 (Oxford comma)

이 스크립트의 존재 이유:
  - LLM 에이전트가 거대한 category_analysis.json을 콘텍스트에
    로드하지 않아도 되도록 자동화
  - 키 이름 변동(total_reviews vs reviews_analyzed_count 등)에
    대한 결정론적 폴백 처리
"""

import argparse
import json
import sys
from pathlib import Path

# category_analysis.json에서 리뷰 수를 읽을 때 사용할 키 우선순위
# 스키마가 변경되더라도 폴백 체인으로 안전하게 처리
REVIEW_COUNT_KEYS = [
    "total_reviews",           # 워크플로우 문서 기준 키
    "all_time_rating_count",   # 현재 실제 데이터 키
    "reviews_analyzed_count",  # 분석된 리뷰 수 (최소 폴백)
]


def get_review_count(product: dict) -> int:
    """제품 데이터에서 리뷰 수를 추출한다. 우선순위 키 체인을 순회."""
    for key in REVIEW_COUNT_KEYS:
        value = product.get(key)
        if value is not None:
            return int(value)
    return 0


def build_product_list(products: list) -> str:
    """제품명 리스트를 Oxford comma 형식의 자연어 문자열로 변환한다.

    예시:
      1개: "Bose QuietComfort Ultra Earbuds (2nd Gen)"
      2개: "Bose QuietComfort Ultra Earbuds (2nd Gen) and Samsung Galaxy Buds 3 Pro"
      3개: "Bose QuietComfort Ultra Earbuds (2nd Gen), Samsung Galaxy Buds 3 Pro, and Beats Powerbeats Pro 2"
    """
    names = [p.get("product_name", "Unknown Product") for p in products]
    if len(names) == 1:
        return names[0]
    elif len(names) == 2:
        return f"{names[0]} and {names[1]}"
    else:
        return ", ".join(names[:-1]) + ", and " + names[-1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate TTS system prompt base with dynamic data injected."
    )
    parser.add_argument(
        "--template",
        default=".agents/skills/reviewlens_narration_agent/assets/system_prompt_template.txt",
        help="Path to system_prompt_template.txt",
    )
    parser.add_argument(
        "--category",
        default="data/category_analysis.json",
        help="Path to category_analysis.json",
    )
    parser.add_argument(
        "--output",
        default="tmp/tts_system_base.txt",
        help="Output path (default: tmp/tts_system_base.txt)",
    )
    args = parser.parse_args()

    template_path = Path(args.template)
    category_path = Path(args.category)
    output_path = Path(args.output)

    # 템플릿 파일 존재 확인
    if not template_path.exists():
        print(f"ERROR: Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    # 카테고리 분석 파일 존재 확인
    if not category_path.exists():
        print(f"ERROR: Category analysis not found: {category_path}", file=sys.stderr)
        print("Run /run_data first.", file=sys.stderr)
        sys.exit(1)

    # 카테고리 분석 데이터 로드
    with open(category_path, "r", encoding="utf-8") as f:
        category_data = json.load(f)

    products = category_data.get("products", [])
    if not products:
        print("ERROR: No products found in category_analysis.json", file=sys.stderr)
        sys.exit(1)

    # 동적 데이터 추출
    total_reviews = sum(get_review_count(p) for p in products)
    category_name = category_data.get("category_name", "unknown category")
    product_count = len(products)
    product_list = build_product_list(products)

    if total_reviews == 0:
        print("WARNING: Total review count is 0. Check category_analysis.json keys.", file=sys.stderr)

    # 사용된 키 식별 (로그용)
    used_key = "unknown"
    for key in REVIEW_COUNT_KEYS:
        if products[0].get(key) is not None:
            used_key = key
            break

    # 템플릿 읽기 및 플레이스홀더 치환
    template_text = template_path.read_text(encoding="utf-8")
    output_text = template_text
    output_text = output_text.replace("{{TOTAL_REVIEWS}}", f"{total_reviews:,}")
    output_text = output_text.replace("{{CATEGORY_NAME}}", category_name)
    output_text = output_text.replace("{{PRODUCT_COUNT}}", str(product_count))
    output_text = output_text.replace("{{PRODUCT_LIST}}", product_list)

    # 미치환 플레이스홀더 경고
    import re
    remaining = re.findall(r"\{\{[A-Z_]+\}\}", output_text)
    if remaining:
        print(f"WARNING: Unreplaced placeholders found: {remaining}", file=sys.stderr)

    # 출력 디렉토리 생성 및 파일 쓰기
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_text, encoding="utf-8")

    # 결과 요약 출력
    print(f"TTS system prompt base generated: {output_path}")
    print(f"  Category: {category_name}")
    print(f"  Products: {product_count} ({product_list})")
    print(f"  Total reviews: {total_reviews:,} (key: {used_key})")
    print(f"  Template: {template_path}")


if __name__ == "__main__":
    main()
