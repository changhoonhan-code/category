"""
Data Validator Phase 3 -- LLM 출력을 원본 draft_script.json에 안전하게 병합하는 도구.

Phase 2(LLM)가 경량 뷰를 수정한 결과를 원본에 block_id 기준으로 병합한다.
evidence_quotes, root 메타데이터 등은 원본 그대로 보존되어
다운스트림 무결성이 보장된다.

두 가지 LLM 출력 포맷을 지원한다:
  - block_patches (경량): 변경된 블록만 포함하는 배열 -- 출력 토큰 절감용
  - scenes (전체): 모든 scene/block을 포함하는 전체 스크립트 -- 하위 호환

병합 규칙:
  - evidence_quotes: LLM 수정 값으로 교체 (맥락 미스매칭/오류 시 LLM이 원본에서 교체 가능)
  - narration, title, headline: LLM 수정본(있을 경우)으로 교체
  - critique_log: Phase 2 로그를 기존 로그에 추가
  - root 필드: 원본 유지

Usage:
    python tools/merge_validator.py
    python tools/merge_validator.py --original data/draft_script.json --edited tmp/script_validator_edited.json
"""
import argparse
import json
import os
import sys

from config import DATAS_DIR, TMP_DIR, contracts

# ── 기본 경로 ──────────────────────────────────────────────────────────────
DEFAULT_ORIGINAL = os.path.join(DATAS_DIR, "draft_script.json")
DEFAULT_EDITED = os.path.join(TMP_DIR, "script_validator_edited.json")

# ── 병합 대상 블록 필드 — pipeline_contracts.json에서 로드 ─────────────────
MERGEABLE_BLOCK_FIELDS = set(contracts()["merge"]["validator_mergeable_fields"])

# ── 절대 생성 금지 필드 (Tone Editor 영역) ──────────────────────────────────
FORBIDDEN_NEW_FIELDS = set()


def _build_edited_index(edited: dict) -> dict:
    """LLM 출력에서 block_id 기반 인덱스를 구축한다.

    block_patches 포맷(경량)과 scenes 포맷(전체) 모두 지원.
    block_patches가 존재하면 우선 사용한다.
    """
    edited_blocks = {}

    # 경량 포맷: block_patches 배열 (변경된 블록만 포함)
    if "block_patches" in edited:
        for patch in edited["block_patches"]:
            bid = patch.get("block_id")
            if bid:
                edited_blocks[bid] = patch
        return edited_blocks

    # 하위 호환: scenes 전체 포맷
    for scene in edited.get("scenes", []):
        for block in scene.get("blocks", []):
            bid = block.get("block_id")
            if bid:
                edited_blocks[bid] = block

    return edited_blocks


def merge_scripts(original: dict, edited: dict) -> tuple[dict, int]:
    """LLM 수정본을 원본에 병합한다.

    Args:
        original: Phase 1 수정 완료된 원본 draft_script.json
        edited: Phase 2 LLM이 수정한 경량 뷰 (block_patches 또는 scenes 포맷)

    Returns:
        (merged_script, changes_count)
    """
    changes = 0

    # LLM 출력에서 block_id 기반 인덱스 구축 (두 포맷 모두 지원)
    edited_blocks = _build_edited_index(edited)
    is_patch_mode = "block_patches" in edited

    # block_id 매칭 경고 (silent failure 방지)
    original_bids = {
        b["block_id"] for s in original["scenes"] for b in s["blocks"]
    }
    edited_bids = set(edited_blocks.keys())

    unmatched = edited_bids - original_bids
    if unmatched:
        print(
            f"[merge_validator] WARNING: LLM이 원본에 없는 block_id를 출력: {sorted(unmatched)}",
            file=sys.stderr,
        )
    # block_patches 모드에서는 누락 경고를 건너뜀 (변경된 블록만 포함하는 것이 정상)
    if not is_patch_mode:
        missing_bids = original_bids - edited_bids
        if missing_bids:
            print(
                f"[merge_validator] WARNING: LLM 출력에서 누락된 block_id (원본 유지): {sorted(missing_bids)}",
                file=sys.stderr,
            )

    # block_id 기준으로 원본 블록에 LLM 수정 사항 반영
    for scene in original["scenes"]:
        for block in scene["blocks"]:
            bid = block["block_id"]
            if bid not in edited_blocks:
                continue

            edited_block = edited_blocks[bid]

            # 병합 대상 필드만 교체
            for field in MERGEABLE_BLOCK_FIELDS:
                if field in edited_block:
                    old_val = block.get(field, "")
                    new_val = edited_block[field]
                    if old_val != new_val:
                        block[field] = new_val
                        changes += 1

            # 금지 필드가 LLM 출력에 있으면 무시 (경고만)
            for field in FORBIDDEN_NEW_FIELDS:
                if field in edited_block:
                    print(
                        f"[merge_validator] WARNING: LLM이 '{field}'을 "
                        f"{bid}에 생성 시도 -- 무시됨 (Tone Editor 영역)",
                        file=sys.stderr,
                    )

    # critique_log 병합: Phase 2 로그를 기존 로그에 추가
    llm_logs = edited.get("critique_log_additions", [])
    if llm_logs:
        if "critique_log" not in original:
            original["critique_log"] = []
        original["critique_log"].extend(llm_logs)
        print(f"[merge_validator] Phase 2 critique_log {len(llm_logs)}건 추가", file=sys.stderr)

    return original, changes


def validate_integrity(script: dict) -> list[str]:
    """병합 후 무결성 검증.

    다운스트림 (Tone Editor, prepare_script.py) 계약을 확인한다.
    pre-curate 상태(evidence_quotes/pacing_profile 미존재)에서도 동작하도록
    해당 필드는 이미 존재하는 블록에서만 검증한다.
    """
    errors = []
    warnings = []

    # critique_log 존재 (Tone Editor 기대)
    if "critique_log" not in script:
        errors.append("critique_log 배열이 없음 -- Tone Editor 전제 조건 위반")

    # root 필드 — scenes는 필수, products/category_name은 post-curate에서만 존재
    if "scenes" not in script:
        errors.append("필수 root 키 'scenes' 누락")
    for key in ("category_name", "products"):
        if key not in script:
            warnings.append(f"root 키 '{key}' 누락 (post-curate 단계에서 추가 예정)")

    # 블록별 필수 필드 — evidence_quotes/pacing_profile은 하나라도 존재하면 전체 검증
    all_blocks = [
        b for s in script.get("scenes", []) for b in s.get("blocks", [])
    ]
    has_evidence = any("evidence_quotes" in b for b in all_blocks)
    has_pacing = any("pacing_profile" in b for b in all_blocks)

    for scene in script.get("scenes", []):
        if "scene_id" not in scene:
            errors.append("scene에 scene_id 누락")
        for block in scene.get("blocks", []):
            bid = block.get("block_id", "UNKNOWN")
            if "narration" not in block:
                errors.append(f"블록 '{bid}'에 narration 누락")
            if has_evidence and "evidence_quotes" not in block:
                errors.append(f"블록 '{bid}'에 evidence_quotes 누락")
            if has_pacing and "pacing_profile" not in block:
                errors.append(f"블록 '{bid}'에 pacing_profile 누락")

    # 경고 출력 (에러가 아니므로 실패시키지 않음)
    for w in warnings:
        print(f"[merge_validator] WARNING: {w}", file=sys.stderr)

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens Data Validator Phase 3: LLM 수정본 → 원본 안전 병합"
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
    merged, changes = merge_scripts(original, edited)

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
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  Data Validator Phase 3 (Merge) Complete", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    print(f"  Narration changes:      {changes}", file=sys.stderr)
    print(f"  Integrity errors:       {len(integrity_errors)}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    print(json.dumps({
        "status": "success",
        "changes": changes,
        "integrity_errors": len(integrity_errors),
        "output": args.original,
    }))


if __name__ == "__main__":
    main()
