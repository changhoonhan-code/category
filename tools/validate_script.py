"""
Phase 1-B 최종 게이트 — Head Writer 완료 직후, Phase 2 진입 직전에 실행.

script_output.json의 스키마 무결성을 결정론적으로 검증한다.
PASS 시 Phase 2 (Narration) 진입 허용. FAIL 시 에러 상세를 터미널에 출력.

검증 항목:
  - Root 필수 필드 존재 여부
  - Products 배열 구조
  - Block 필수 필드 (block_id, narration, bgm_mood, pacing_profile, evidence_quotes)
  - Block ID 유일성
  - EvidenceQuote 필수 필드 + product_id 참조 무결성
  - bgm_mood / pacing_profile 값 검증
  - 금지 필드 잔류 여부

Usage:
    python tools/validate_script.py
    python tools/validate_script.py --input data/script_output.json
"""
import argparse
import json
import os
import sys

from config import DATAS_DIR

# ── 기본 경로 ──────────────────────────────────────────────────────────────
DEFAULT_INPUT = os.path.join(DATAS_DIR, "script_output.json")

# ── 검증 상수 ──────────────────────────────────────────────────────────────
# Root 레벨 필수 키
REQUIRED_ROOT_KEYS = {"category_name", "products", "video_question", "excluded_themes", "teaser_payoff_map", "scenes"}

# Block 레벨 필수 키
REQUIRED_BLOCK_KEYS = {"block_id", "narration", "bgm_mood", "pacing_profile", "evidence_quotes", "directing_hint"}

# EvidenceQuote 필수 키
REQUIRED_QUOTE_KEYS = {"product_id", "highlight_phrase", "star_rating", "review_id", "selection_reason"}

# bgm_mood 허용 값
VALID_BGM_MOODS = {"Bright", "Dark", "Tense", "Neutral", "Triumphant", "Silence"}

# pacing_profile 허용 값
VALID_PACING_PROFILES = {"breathe", "standard", "dense"}

# 금지 필드 (잔류 시 에러)
FORBIDDEN_ROOT_KEYS = {"critique_log", "phase_completion", "editor_notes", "assembler_metadata"}

# Products 배열 내 필수 키
REQUIRED_PRODUCT_KEYS = {"product_id", "product_name"}


class ValidationError:
    """검증 에러 하나를 표현하는 데이터 클래스."""
    def __init__(self, level: str, location: str, message: str):
        self.level = level  # "ERROR" | "WARNING"
        self.location = location  # 예: "root", "scene[0].block[1]", "scene[0].block[1].evidence_quotes[0]"
        self.message = message

    def __str__(self):
        icon = "❌" if self.level == "ERROR" else "⚠️"
        return f"  {icon} [{self.level}] {self.location}: {self.message}"


def validate_script(data: dict) -> list[ValidationError]:
    """
    script_output.json 데이터를 검증하고 에러 목록을 반환.
    에러가 비어 있으면 PASS.
    """
    errors: list[ValidationError] = []

    # ── 1. Root 필수 키 검증 ──
    for key in REQUIRED_ROOT_KEYS:
        if key not in data:
            errors.append(ValidationError("ERROR", "root", f"필수 키 '{key}' 누락"))

    # ── 2. 금지 필드 잔류 검증 ──
    for key in FORBIDDEN_ROOT_KEYS:
        if key in data:
            errors.append(ValidationError("ERROR", "root", f"금지 필드 '{key}' 잔류 — prepare_script.py가 제거했어야 함"))

    # ── 3. Products 배열 검증 ──
    products = data.get("products", [])
    valid_product_ids = set()

    if not isinstance(products, list) or len(products) == 0:
        errors.append(ValidationError("ERROR", "root.products", "products 배열이 비어 있거나 존재하지 않음"))
    else:
        for i, product in enumerate(products):
            loc = f"products[{i}]"
            for key in REQUIRED_PRODUCT_KEYS:
                if key not in product:
                    errors.append(ValidationError("ERROR", loc, f"필수 키 '{key}' 누락"))
            if "product_id" in product:
                valid_product_ids.add(product["product_id"])

    # ── 4. Scenes + Blocks 검증 ──
    scenes = data.get("scenes", [])
    all_block_ids = []

    if not isinstance(scenes, list) or len(scenes) == 0:
        errors.append(ValidationError("ERROR", "root.scenes", "scenes 배열이 비어 있거나 존재하지 않음"))
    else:
        for si, scene in enumerate(scenes):
            scene_loc = f"scenes[{si}]"

            # scene_id 존재 확인
            if "scene_id" not in scene:
                errors.append(ValidationError("ERROR", scene_loc, "scene_id 누락"))

            blocks = scene.get("blocks", [])
            if not isinstance(blocks, list) or len(blocks) == 0:
                errors.append(ValidationError("WARNING", scene_loc, "blocks 배열이 비어 있음"))
                continue

            for bi, block in enumerate(blocks):
                block_id = block.get("block_id", f"UNKNOWN_{si}_{bi}")
                block_loc = f"scenes[{si}].blocks[{bi}] ({block_id})"

                # ── 4a. Block 필수 키 검증 ──
                for key in REQUIRED_BLOCK_KEYS:
                    if key not in block:
                        errors.append(ValidationError("ERROR", block_loc, f"필수 키 '{key}' 누락"))

                # block_id 수집 (중복 검사용)
                all_block_ids.append(block_id)

                # ── 4b. bgm_mood 값 검증 ──
                bgm = block.get("bgm_mood")
                if bgm is not None and bgm not in VALID_BGM_MOODS:
                    errors.append(ValidationError("ERROR", block_loc, f"bgm_mood '{bgm}' 유효하지 않음 — 허용: {VALID_BGM_MOODS}"))

                # ── 4c. pacing_profile 값 검증 ──
                pacing = block.get("pacing_profile")
                if pacing is not None and pacing not in VALID_PACING_PROFILES:
                    errors.append(ValidationError("ERROR", block_loc, f"pacing_profile '{pacing}' 유효하지 않음 — 허용: {VALID_PACING_PROFILES}"))

                # ── 4d. evidence_quotes 검증 ──
                quotes = block.get("evidence_quotes", [])
                if not isinstance(quotes, list):
                    errors.append(ValidationError("ERROR", block_loc, "evidence_quotes가 배열이 아님"))
                    continue

                for qi, quote in enumerate(quotes):
                    quote_loc = f"{block_loc}.evidence_quotes[{qi}]"

                    # 필수 키 검증
                    for key in REQUIRED_QUOTE_KEYS:
                        if key not in quote:
                            errors.append(ValidationError("ERROR", quote_loc, f"필수 키 '{key}' 누락"))

                    # product_id 참조 무결성
                    qpid = quote.get("product_id")
                    if qpid is not None and valid_product_ids and qpid not in valid_product_ids:
                        errors.append(ValidationError("ERROR", quote_loc, f"product_id '{qpid}'가 root products[]에 없음 — 유효: {sorted(valid_product_ids)}"))

                    # star_rating 범위 검증
                    sr = quote.get("star_rating")
                    if sr is not None and (not isinstance(sr, (int, float)) or sr < 1 or sr > 5):
                        errors.append(ValidationError("ERROR", quote_loc, f"star_rating '{sr}' 범위 초과 — 허용: 1-5"))

                    # is_humorous가 block 레벨에 있으면 경고
                if "is_humorous" in block:
                    errors.append(ValidationError("ERROR", block_loc, "is_humorous가 block 레벨에 존재 — quote 레벨에만 허용"))

    # ── 5. Block ID 유일성 검증 ──
    seen_ids = set()
    for bid in all_block_ids:
        if bid in seen_ids:
            errors.append(ValidationError("ERROR", f"block_id '{bid}'", "중복 block_id 발견"))
        seen_ids.add(bid)

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: script_output.json 스키마 무결성 검증 (Phase 2 진입 게이트)"
    )
    parser.add_argument(
        "--input", default=DEFAULT_INPUT,
        help=f"검증할 script_output.json 경로 (기본: {DEFAULT_INPUT})"
    )
    args = parser.parse_args()

    # 입력 파일 확인
    if not os.path.exists(args.input):
        print(json.dumps({"error": f"File not found: {args.input}"}))
        sys.exit(1)

    # 데이터 로드
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 검증 실행
    errors = validate_script(data)

    # ── 결과 출력 ──
    error_count = sum(1 for e in errors if e.level == "ERROR")
    warning_count = sum(1 for e in errors if e.level == "WARNING")

    # Block 수 카운트
    total_blocks = sum(
        len(scene.get("blocks", []))
        for scene in data.get("scenes", [])
    )

    print("\n" + "=" * 60, file=sys.stderr)
    if error_count == 0:
        print("  ✅ VALIDATION PASSED — Phase 2 진입 가능", file=sys.stderr)
    else:
        print("  ❌ VALIDATION FAILED — 아래 에러를 수정하세요", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    print(f"\n  파일: {args.input}", file=sys.stderr)
    print(f"  씬 수: {len(data.get('scenes', []))}", file=sys.stderr)
    print(f"  블록 수: {total_blocks}", file=sys.stderr)
    print(f"  제품 수: {len(data.get('products', []))}", file=sys.stderr)
    print(f"  에러: {error_count} / 경고: {warning_count}", file=sys.stderr)

    if errors:
        print("\n  --- 상세 ---\n", file=sys.stderr)
        for err in errors:
            print(str(err), file=sys.stderr)

    print("\n" + "=" * 60 + "\n", file=sys.stderr)

    # Machine-parseable JSON 출력
    print(json.dumps({
        "status": "PASS" if error_count == 0 else "FAIL",
        "input": args.input,
        "scenes": len(data.get("scenes", [])),
        "blocks": total_blocks,
        "products": len(data.get("products", [])),
        "errors": error_count,
        "warnings": warning_count,
    }), file=sys.stdout)

    # FAIL 시 exit code 1
    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
