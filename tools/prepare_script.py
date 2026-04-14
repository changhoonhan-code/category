"""
Phase 1-B 변환 도구 — Tone Editor 직후, Head Writer 직전에 실행.

draft_script.json(DV + Tone Editor의 critique_log 포함)을 정제하여
Head Writer가 바로 읽을 수 있는 깨끗한 script_output.json을 생성한다.

기능:
  1. critique_log 추출 → 터미널에 에디터별 요약 출력
  2. critique_log 및 작업용 임시 필드 제거
  3. Root 필드 정제 (category_name, products, video_question 등 carry-through)
  4. script_output.json 저장

Usage:
    python tools/prepare_script.py
    python tools/prepare_script.py --input data/draft_script.json --output data/script_output.json
"""
import argparse
import json
import os
import sys
from collections import Counter

from config import DATAS_DIR

# ── 기본 경로 ──────────────────────────────────────────────────────────────
DEFAULT_INPUT = os.path.join(DATAS_DIR, "draft_script.json")
DEFAULT_OUTPUT = os.path.join(DATAS_DIR, "script_output.json")

# ── Head Writer에 전달해야 하는 Root 필드 목록 ──────────────────────────────
# 이 목록에 없는 root-level 키는 작업용 임시 필드로 간주하여 제거
ALLOWED_ROOT_KEYS = {
    "category_name",
    "products",
    "video_question",
    "excluded_themes",
    "teaser_payoff_map",
    "scenes",
}

# ── 제거 대상 필드 (명시적 블랙리스트) ──────────────────────────────────────
BLACKLISTED_ROOT_KEYS = {
    "critique_log",
    "phase_completion",
    "editor_notes",
    "assembler_metadata",
}


def print_critique_log_summary(critique_log: list) -> None:
    """
    critique_log 배열을 에디터별로 그룹핑하여 터미널에 요약 출력.
    Final Assembler가 담당하던 기능을 이 도구가 승계.
    """
    if not critique_log:
        print("[prepare_script] critique_log가 비어 있습니다. 에디터들이 수정 사항을 발견하지 못했습니다.", file=sys.stderr)
        return

    # 에디터별 fix count
    editor_counts = Counter(entry.get("editor", "Unknown") for entry in critique_log)

    print("\n" + "=" * 60, file=sys.stderr)
    print("  📋 CRITIQUE LOG SUMMARY (Phase 1-B Steps 1-2)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # 에디터별 출력
    for editor, count in editor_counts.most_common():
        print(f"\n  [{editor}] — {count} fix(es)", file=sys.stderr)
        # 해당 에디터의 fix_type별 세부 카운트
        type_counts = Counter(
            entry.get("fix_type", "Unknown")
            for entry in critique_log
            if entry.get("editor") == editor
        )
        for fix_type, type_count in type_counts.most_common():
            print(f"    • {fix_type}: {type_count}", file=sys.stderr)

    print(f"\n  Total: {len(critique_log)} fix(es) across {len(editor_counts)} editor(s)", file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)


def prepare_script(data: dict) -> dict:
    """
    draft_script.json 데이터를 정제하여 script_output.json 구조로 변환.

    1. critique_log 추출 및 요약 출력
    2. 허용된 root 키만 유지 (블랙리스트 + 화이트리스트 방식)
    3. 정제된 dict 반환
    """
    # ── critique_log 추출 및 출력 ──
    critique_log = data.get("critique_log", [])
    print_critique_log_summary(critique_log)

    # ── Root 필드 정제 ──
    # 허용 목록에 있는 키만 유지
    result = {}
    for key in ALLOWED_ROOT_KEYS:
        if key in data:
            result[key] = data[key]

    # 누락된 필수 키 경고
    missing_keys = ALLOWED_ROOT_KEYS - set(result.keys())
    if missing_keys:
        print(
            f"[prepare_script] ⚠️ WARNING: 필수 root 키 누락: {sorted(missing_keys)}",
            file=sys.stderr,
        )

    return result


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: draft_script.json → script_output.json 변환 (critique_log 정제)"
    )
    parser.add_argument(
        "--input", default=DEFAULT_INPUT,
        help=f"입력 draft_script.json 경로 (기본: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT,
        help=f"출력 script_output.json 경로 (기본: {DEFAULT_OUTPUT})"
    )
    args = parser.parse_args()

    # 입력 파일 확인
    if not os.path.exists(args.input):
        print(json.dumps({"error": f"File not found: {args.input}"}))
        sys.exit(1)

    # 데이터 로드
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 변환 실행
    result = prepare_script(data)

    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    # 저장
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # ── 실행 결과 요약 ──
    original_size = os.path.getsize(args.input)
    output_size = os.path.getsize(args.output)
    reduction = round(100 * (1 - output_size / original_size), 1) if original_size > 0 else 0

    print(json.dumps({
        "status": "success",
        "input": args.input,
        "output": args.output,
        "original_bytes": original_size,
        "output_bytes": output_size,
        "reduction_pct": reduction,
        "critique_log_entries": len(data.get("critique_log", [])),
    }), file=sys.stdout)

    print(
        f"[prepare_script] ✅ {args.output} saved "
        f"({original_size:,} → {output_size:,} bytes, {reduction}% reduction)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
