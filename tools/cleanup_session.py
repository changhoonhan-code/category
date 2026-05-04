"""
세션 정리 도구 — 파이프라인 단계별로 이전 세션의 임시 파일을 안전하게 삭제한다.
크로스 플랫폼(Windows/Linux/Mac) 안전 동작을 보장하며,
파일이 존재하지 않아도 에러 없이 조용히 넘어간다.

Usage:
    python tools/cleanup_session.py --stage audio
"""
import argparse
import glob
import json
import os
import sys

from config import TMP_DIR

# ── 단계별 정리 대상 정의 ────────────────────────────────────────────────────
# 각 stage 키에 대해:
#   "files"      — 정확한 파일명 리스트 (TMP_DIR 기준 상대 경로)
#   "globs"      — 와일드카드 패턴 리스트 (TMP_DIR 기준)
#   "init_files" — 삭제 후 빈 상태로 재생성할 파일 목록
#                  각 항목은 {"name": "파일명", "content": 초기 내용} 형태
#                  downstream QA가 파일 존재를 기대하는 경우에 사용
STAGE_TARGETS = {
    "audio": {
        "files": [
            "scene_handoff.json",
            "prompt_audit_report.json",
        ],
        "globs": [
            "tts_prompt_*.txt",
        ],
    },
}


def cleanup(stage: str) -> dict:
    """지정된 stage에 해당하는 임시 파일을 삭제하고 필요한 파일을 초기화한다.

    Returns:
        삭제 결과 요약 dict (deleted: 삭제된 파일 수, skipped: 미존재 파일 수,
                            initialized: 초기화된 파일 수)
    """
    targets = STAGE_TARGETS.get(stage)
    if targets is None:
        print(f"[cleanup] Unknown stage: '{stage}'. Available: {list(STAGE_TARGETS.keys())}")
        sys.exit(1)

    deleted = 0
    skipped = 0

    # 개별 파일 삭제
    for filename in targets.get("files", []):
        filepath = os.path.join(TMP_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            deleted += 1
            print(f"  Deleted: {filename}")
        else:
            skipped += 1

    # glob 패턴 삭제
    for pattern in targets.get("globs", []):
        full_pattern = os.path.join(TMP_DIR, pattern)
        matched = glob.glob(full_pattern)
        for filepath in matched:
            os.remove(filepath)
            deleted += 1
            print(f"  Deleted: {os.path.basename(filepath)}")
        if not matched:
            skipped += 1

    # 삭제 후 빈 상태로 재생성할 파일 초기화
    # downstream QA 단계에서 파일 존재를 기대하므로 항상 생성해둔다
    initialized = 0
    os.makedirs(TMP_DIR, exist_ok=True)
    for init_spec in targets.get("init_files", []):
        filepath = os.path.join(TMP_DIR, init_spec["name"])
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(init_spec["content"], f, ensure_ascii=False, indent=2)
        initialized += 1
        print(f"  Initialized: {init_spec['name']} (empty)")

    return {"deleted": deleted, "skipped": skipped, "initialized": initialized}


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: Session cleanup — safely remove stale temp files"
    )
    parser.add_argument(
        "--stage", required=True, choices=list(STAGE_TARGETS.keys()),
        help="Pipeline stage to clean up (e.g. 'audio')"
    )
    args = parser.parse_args()

    print(f"[cleanup] Stage: {args.stage}")
    result = cleanup(args.stage)
    print(
        f"[cleanup] Done: {result['deleted']} deleted, "
        f"{result['skipped']} skipped (not found), "
        f"{result['initialized']} initialized"
    )


if __name__ == "__main__":
    main()
