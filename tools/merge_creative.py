"""
Creative Director Phase 4 -- LLM 출력을 원본 draft_script.json에 안전하게 병합하는 도구.

Phase 3(LLM — Creative Director)가 생성한 구조적 패치를
원본에 block_id 기준으로 병합한다.
evidence_quotes, narration, root 메타데이터 등은 원본 그대로 보존된다.

CD는 narration 텍스트를 수정하지 않는다. Writer Agent가 prose의 유일한 소유자다.

병합 규칙:
  - narration: 수정 불가 — block_patches 없음
  - evidence_quotes 내 is_humorous: quote_patches로 review_id 기준 패치
  - block_annotations: 루트에 저장 (다운스트림 generate_briefing.py가 소비)
  - critique_log: Phase 3 로그를 기존 로그에 추가 (Writer Agent가 소비하는 플래그)
  - 금지 필드 (directing_hint, pacing_profile, title, headline, narration): 무시

Usage:
    python tools/merge_creative.py
    python tools/merge_creative.py --original data/draft_script.json --edited tmp/script_creative_edited.json
"""
import argparse
import json
import os
import re
import sys

from config import DATAS_DIR, TMP_DIR, contracts

# ── 기본 경로 ──────────────────────────────────────────────────────────────
DEFAULT_ORIGINAL = os.path.join(DATAS_DIR, "draft_script.json")
DEFAULT_EDITED = os.path.join(TMP_DIR, "script_creative_edited.json")

# ── pipeline_contracts.json에서 동적 로드 ─────────────────────────────────
_merge = contracts()["merge"]
_annotations = contracts().get("annotations", {})

FORBIDDEN_NEW_FIELDS = set(_merge["creative_forbidden_fields"])
QUOTE_PATCH_FIELD = _merge["creative_quote_patch_field"]
ANNOTATION_REQUIRED = set(_annotations.get("required_fields", []))


# ── block_id 인덱스 구축 ──────────────────────────────────────────────────
def _build_edited_index(edited: dict) -> dict:
    """CD 출력에서 block_id 기반 인덱스를 구축한다.

    CD는 block_patches를 출력하지 않는다 (narration 소유권 없음).
    이 함수는 향후 확장을 위해 빈 dict를 반환하며 유지된다.
    """
    return {}


def _build_quote_patch_index(edited: dict) -> dict:
    """LLM 출력에서 quote_patches를 (block_id, review_id) 기반 인덱스로 구축한다."""
    index = {}
    for qp in edited.get("quote_patches", []):
        bid = qp.get("block_id")
        rid = qp.get("review_id")
        if bid and rid:
            index[(bid, rid)] = qp
    return index


def merge_scripts(original: dict, edited: dict) -> tuple[dict, int, list[str]]:
    """CD 패치를 원본에 병합한다.

    CD는 narration을 수정하지 않는다. 병합 대상:
      - quote_patches: evidence_quotes 내 is_humorous 플래그
      - critique_log_additions: Writer Agent 수정을 위한 플래그
      - block_annotations: 구조 메타데이터

    Args:
        original: tone 단계 직전의 원본 draft_script.json
        edited: Phase 3 CD가 생성한 패치 (quote_patches + annotations + critique_log_additions)

    Returns:
        (merged_script, changes_count, [])
    """
    changes = 0
    quote_patches = _build_quote_patch_index(edited)

    # ── evidence_quotes 내 is_humorous 패치 ──
    for scene in original["scenes"]:
        for block in scene["blocks"]:
            bid = block["block_id"]
            for quote in block.get("evidence_quotes", []):
                rid = quote.get("review_id")
                key = (bid, rid)
                if key in quote_patches:
                    patch = quote_patches[key]
                    if QUOTE_PATCH_FIELD in patch:
                        old_val = quote.get(QUOTE_PATCH_FIELD)
                        new_val = patch[QUOTE_PATCH_FIELD]
                        if old_val != new_val:
                            quote[QUOTE_PATCH_FIELD] = new_val
                            changes += 1

    # ── critique_log 병합 ──
    llm_logs = edited.get("critique_log_additions", [])
    if llm_logs:
        if "critique_log" not in original:
            original["critique_log"] = []
        original["critique_log"].extend(llm_logs)
        print(
            f"[merge_creative] Phase 3 critique_log {len(llm_logs)}건 추가",
            file=sys.stderr,
        )

    # ── block_annotations 저장 ──
    annotations = edited.get("block_annotations", [])
    if annotations:
        # 유효성 검증: 필수 필드 존재 확인
        valid_annotations = []
        for ann in annotations:
            missing = ANNOTATION_REQUIRED - set(ann.keys())
            if missing:
                print(
                    f"[merge_creative] WARNING: annotation에 필수 필드 누락 "
                    f"(block_id={ann.get('block_id', '?')}): {missing}",
                    file=sys.stderr,
                )
            else:
                valid_annotations.append(ann)

        original["block_annotations"] = valid_annotations
        print(
            f"[merge_creative] {len(valid_annotations)} block annotations 저장",
            file=sys.stderr,
        )

    return original, changes, []


def validate_integrity(script: dict) -> list[str]:
    """병합 후 무결성 검증.

    다운스트림 (prepare_script.py) 계약을 확인한다.
    """
    errors = []

    # critique_log 존재 (Writer Agent 수정 플래그 추적용)
    if "critique_log" not in script:
        errors.append("critique_log 배열이 없음")

    # 필수 root 필드 (scenes만 필수; category_name/products는 post-curate 단계에서 추가됨)
    required_root = {"scenes"}
    for key in required_root:
        if key not in script:
            errors.append(f"필수 root 키 '{key}' 누락")

    # 블록별 필수 필드
    for scene in script.get("scenes", []):
        if "scene_id" not in scene:
            errors.append("scene에 scene_id 누락")
        for block in scene.get("blocks", []):
            bid = block.get("block_id", "UNKNOWN")
            if "narration" not in block:
                errors.append(f"블록 '{bid}'에 narration 누락")
            if "evidence_quotes" not in block:
                errors.append(f"블록 '{bid}'에 evidence_quotes 누락")
            # 'pacing' 또는 'pacing_profile' 둘 다 허용 (build_outline.py 버전에 따라 다름)
            if "pacing_profile" not in block and "pacing" not in block:
                errors.append(f"블록 '{bid}'에 pacing_profile 누락")

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens Creative Director Phase 4: LLM 수정본 → 원본 안전 병합"
    )
    parser.add_argument(
        "--original", default=DEFAULT_ORIGINAL,
        help=f"원본 draft_script.json (기본: {DEFAULT_ORIGINAL})"
    )
    parser.add_argument(
        "--edited", default=DEFAULT_EDITED,
        help=f"LLM 수정본 경량 JSON (기본: {DEFAULT_EDITED})"
    )
    args = parser.parse_args()

    # ── 입력 파일 확인 ──
    for path, label in [(args.original, "original"), (args.edited, "edited")]:
        if not os.path.exists(path):
            print(json.dumps({"error": f"File not found: {path} ({label})"}))
            sys.exit(1)

    # ── 데이터 로드 ──
    with open(args.original, "r", encoding="utf-8") as f:
        original = json.load(f)
    with open(args.edited, "r", encoding="utf-8") as f:
        edited = json.load(f)

    # ── 병합 실행 ──
    merged, changes, number_violations = merge_scripts(original, edited)

    # ── 숫자 보존 검증 ──
    if number_violations:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"  NUMBER PRESERVATION CHECK FAILED", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        for v in number_violations:
            print(f"  - {v}", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)
        print(
            f"[merge_creative] WARNING: {len(number_violations)} narration(s) have "
            f"altered numbers. Merge continues but review is strongly recommended.",
            file=sys.stderr,
        )

    # ── 무결성 검증 ──
    integrity_errors = validate_integrity(merged)

    if integrity_errors:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"  INTEGRITY CHECK FAILED", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        for err in integrity_errors:
            print(f"  - {err}", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)
        sys.exit(1)

    # ── 저장 ──
    with open(args.original, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    # ── 실행 요약 ──
    annotation_count = len(merged.get("block_annotations", []))
    print(f"{'='*60}", file=sys.stderr)
    print(f"  Creative Director Phase 4 (Merge) Complete", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    print(f"  Quote flag changes:       {changes}", file=sys.stderr)
    print(f"  Block annotations:        {annotation_count}", file=sys.stderr)
    print(f"  Integrity errors:         {len(integrity_errors)}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    print(json.dumps({
        "status": "success",
        "quote_flag_changes": changes,
        "block_annotations": annotation_count,
        "integrity_errors": len(integrity_errors),
        "output": args.original,
    }))


if __name__ == "__main__":
    main()
