"""
Product Map — category_analysis.json에서 product_id → product_name 매핑 추출.

에이전트가 나레이션의 제품명을 product_id로 변환할 때 사용.
stdout으로 JSON을 출력하므로 에이전트가 바로 소비 가능.

Usage:
    python tools/product_map.py
    python tools/product_map.py --source data/category_analysis.json
"""
import argparse
import json
import sys
from pathlib import Path

from config import DATAS_DIR

DEFAULT_SOURCE = Path(DATAS_DIR) / "category_analysis.json"
DEFAULT_OUTPUT = Path(DATAS_DIR) / "product_map.json"


def main():
    parser = argparse.ArgumentParser(
        description="Extract product ID → name mapping from category_analysis.json"
    )
    parser.add_argument(
        "--source", default=str(DEFAULT_SOURCE),
        help=f"Source file (default: {DEFAULT_SOURCE})"
    )
    parser.add_argument(
        "--output", default=str(DEFAULT_OUTPUT),
        help=f"Output file (default: {DEFAULT_OUTPUT})"
    )
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(json.dumps({"error": f"File not found: {source}"}), file=sys.stderr)
        sys.exit(1)

    with source.open("r", encoding="utf-8") as f:
        data = json.load(f)

    product_map = {
        p["product_id"]: p["product_name"]
        for p in data.get("products", [])
    }

    # 파일 저장
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(product_map, f, ensure_ascii=False, indent=2)

    # stdout 출력 (에이전트 소비용)
    print(json.dumps(product_map, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
