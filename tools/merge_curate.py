"""
Quote Curator Merge Tool -- LLM 출력을 원본 draft_script.json에 안전하게 병합하는 도구.

Quote Curator가 수정한 경량 뷰(curate_patch.json)를 원본에 병합한다.
evidence_quotes, headline, title 필드만 교체하며, narration 등 원본 필드는 보존된다.

Usage:
    python tools/merge_curate.py
    python tools/merge_curate.py --original data/draft_script.json --edited data/curate_patch.json
"""
import argparse
import json
import os
import sys

from config import DATAS_DIR, contracts

# ── 기본 경로 ──────────────────────────────────────────────────────────────
DEFAULT_ORIGINAL = os.path.join(DATAS_DIR, "draft_script.json")
DEFAULT_EDITED = os.path.join(DATAS_DIR, "curate_patch.json")

# ── 병합 대상 필드 — pipeline_contracts.json에서 로드 ─────────────────
MERGEABLE_FIELDS = set(contracts()["merge"]["curate_mergeable_fields"])

def merge_scripts(original: dict, edited: dict) -> tuple[dict, int]:
    changes = 0

    # Scene 단위 병합 (headline 처리를 위해)
    edited_scenes = {s["scene_id"]: s for s in edited.get("scenes", [])}

    for scene in original.get("scenes", []):
        sid = scene.get("scene_id")
        if sid in edited_scenes:
            edited_scene = edited_scenes[sid]
            
            # headline 병합
            if "headline" in MERGEABLE_FIELDS and "headline" in edited_scene:
                if scene.get("headline") != edited_scene["headline"]:
                    scene["headline"] = edited_scene["headline"]
                    changes += 1

            # Block 단위 병합
            edited_blocks = {b["block_id"]: b for b in edited_scene.get("blocks", [])}
            for block in scene.get("blocks", []):
                bid = block.get("block_id")
                if bid in edited_blocks:
                    edited_block = edited_blocks[bid]
                    for field in ["evidence_quotes", "title"]:
                        if field in MERGEABLE_FIELDS and field in edited_block:
                            if block.get(field) != edited_block[field]:
                                block[field] = edited_block[field]
                                changes += 1

    return original, changes


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens Quote Curator: LLM 수정본 → 원본 안전 병합"
    )
    parser.add_argument(
        "--original", default=DEFAULT_ORIGINAL,
        help=f"원본 draft_script.json (기본: {DEFAULT_ORIGINAL})"
    )
    parser.add_argument(
        "--edited", default=DEFAULT_EDITED,
        help=f"LLM 수정본 curate_patch.json (기본: {DEFAULT_EDITED})"
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

    # ── 저장 ──
    with open(args.original, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    # ── 실행 요약 ──
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  Quote Curator Merge Complete", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    print(f"  Changes applied:        {changes}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    print(json.dumps({
        "status": "success",
        "changes": changes,
        "output": args.original,
    }))


if __name__ == "__main__":
    main()
