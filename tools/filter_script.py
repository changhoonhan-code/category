"""
Filter script_output.json for agent-specific profiles — reduces token cost by providing
each agent only the fields it needs from the master script.

Usage:
    python tools/filter_script.py --profile narration
    python tools/filter_script.py --profile narration --output tmp/script_narration.json
    python tools/filter_script.py --profile narration --scenes hook,category_rating_overview
    python tools/filter_script.py --profile narration --group 2a

Profiles: narration

--scenes 옵션: 쉼표 구분 scene_id 리스트. 지정하면 해당 씬만 포함.
    미지정 시 전체 씬 유지 (기존 동작과 동일).
--group 옵션: Hybrid 4-Group 실행을 위한 자동 씬 분류.
    1=Opening(hook+rating_overview), 2a=Theme Front(첫 3개), 2b=Theme Back(나머지), 3=Closing(standout+verdict).
    --group 지정 시 --scenes는 무시되며, 출력 경로도 자동 설정된다.
"""
import argparse
import json
import os
import sys

from config import DATAS_DIR, TMP_DIR

# ── Profile Definitions ─────────────────────────────────────────────────────
# Each profile specifies which fields to INCLUDE from script_output.json.
# - root_fields: top-level keys to preserve (besides "scenes", which is always kept)
# - block_fields: per-block keys to preserve (scenes[].blocks[])
# scene_id is always preserved regardless of block_fields.

PROFILES = {
    "narration": {
        "root_fields": ["category_name", "products", "video_question"],
        # directing_hint: 톤 에이전트가 블록별로 작성한 연기 분위기 힌트 (나레이션 에이전트가 참조)
        "block_fields": ["block_id", "narration", "bgm_mood", "pacing_profile", "directing_hint"],
    },
}

# ── Group Definitions ────────────────────────────────────────────────────────
# Hybrid 4-Group 실행을 위한 자동 씬 분류 로직.
# 스크립트의 scene_id를 읽어 그룹별로 자동 할당한다.
VALID_GROUPS = ["1", "2a", "2b", "3"]


def resolve_group_scenes(data: dict, group: str) -> list[str]:
    """그룹 ID에 따라 scene_id 리스트를 자동으로 결정한다.

    Args:
        data: script_output.json 원본 데이터
        group: 그룹 ID ("1", "2a", "2b", "3")

    Returns:
        해당 그룹에 포함될 scene_id 리스트
    """
    all_scene_ids = [s["scene_id"] for s in data.get("scenes", [])]

    # theme_ 접두사를 가진 씬만 추출
    theme_scenes = [sid for sid in all_scene_ids if sid.startswith("theme_")]
    # theme이 아닌 씬 중 hook/category_rating_overview가 아닌 나머지 (standout, verdict 등)
    closing_scenes = [
        sid for sid in all_scene_ids
        if sid not in ("hook", "category_rating_overview")
        and not sid.startswith("theme_")
    ]

    if group == "1":
        # Opening: Hook + Rating Overview
        return ["hook", "category_rating_overview"]
    elif group == "2a":
        # Theme Front: 첫 3개 theme 씬
        return theme_scenes[:3]
    elif group == "2b":
        # Theme Back: 나머지 theme 씬
        return theme_scenes[3:]
    elif group == "3":
        # Closing: standout, verdict 등 나머지 전부
        return closing_scenes
    else:
        print(f"[filter_script] Unknown group: '{group}'. Valid: {VALID_GROUPS}")
        sys.exit(1)


def filter_script(data: dict, profile: dict, scenes: list[str] | None = None) -> dict:
    """Apply a filter profile to script_output.json data.

    Args:
        data: script_output.json 원본 데이터
        profile: 에이전트 프로필 (root_fields, block_fields)
        scenes: 포함할 scene_id 리스트 (None이면 전체 씬 유지)
    """
    result = {}

    # 루트 필드 필터링
    for key in profile.get("root_fields", []):
        if key in data:
            result[key] = data[key]

    block_fields = set(profile.get("block_fields", []))
    result["scenes"] = []
    for scene in data.get("scenes", []):
        # 씬 필터링: --scenes 지정 시 해당 scene_id만 포함
        if scenes and scene["scene_id"] not in scenes:
            continue
        filtered_scene = {
            "scene_id": scene["scene_id"],
            "blocks": [],
        }
        for block in scene.get("blocks", []):
            filtered_block = {k: v for k, v in block.items() if k in block_fields}
            filtered_scene["blocks"].append(filtered_block)
        result["scenes"].append(filtered_scene)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: Filter script_output.json for agent-specific profiles"
    )
    parser.add_argument(
        "--profile", required=True, choices=list(PROFILES.keys()),
        help="Agent profile name"
    )
    parser.add_argument(
        "--input", default=os.path.join(DATAS_DIR, "script_output.json"),
        help="Source script_output.json path (default: data/script_output.json)"
    )
    parser.add_argument(
        "--scenes", default=None,
        help="Comma-separated scene_ids to include (default: all scenes). "
             "Example: --scenes hook,category_rating_overview"
    )
    parser.add_argument(
        "--group", default=None, choices=VALID_GROUPS,
        help="Auto-group for Hybrid 4-Group execution. "
             "1=Opening, 2a=Theme Front, 2b=Theme Back, 3=Closing. "
             "Overrides --scenes and auto-sets output path."
    )
    parser.add_argument(
        "--output", default=None,
        help="Output path (default: tmp/script_{profile}.json)"
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(json.dumps({"error": f"File not found: {args.input}"}))
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    # --group 옵션이 지정된 경우: 자동 씬 분류 + 출력 경로 자동 설정
    if args.group:
        scenes_filter = resolve_group_scenes(data, args.group)
        if not scenes_filter:
            print(f"[filter_script] Warning: Group '{args.group}' resolved to 0 scenes.")
            sys.exit(1)
        # --group 사용 시 출력 경로 자동 설정 (명시적 --output이 없는 경우)
        if args.output is None:
            args.output = os.path.join(TMP_DIR, f"script_{args.profile}_group{args.group}.json")
        print(
            f"[filter_script] Group '{args.group}' resolved to scenes: {scenes_filter}",
            file=sys.stderr,
        )
    else:
        # 기존 --scenes 옵션 파싱: 쉼표 구분 scene_id 리스트
        scenes_filter = args.scenes.split(",") if args.scenes else None

    # 출력 경로 폴백: --group이나 --output 모두 미지정 시 기본 경로 사용
    if args.output is None:
        args.output = os.path.join(TMP_DIR, f"script_{args.profile}.json")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    filtered = filter_script(data, PROFILES[args.profile], scenes=scenes_filter)

    # 씬 필터링 적용 시 포함된 씬/블록 수 표시
    if scenes_filter:
        total_blocks = sum(len(s.get("blocks", [])) for s in filtered.get("scenes", []))
        print(
            f"[filter_script] Scene filter: {len(filtered['scenes'])} scenes, "
            f"{total_blocks} blocks (from {len(scenes_filter)} requested scene_ids)",
            file=sys.stderr,
        )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    original_size = os.path.getsize(args.input)
    filtered_json = json.dumps(filtered, ensure_ascii=False, indent=2)
    filtered_size = len(filtered_json.encode("utf-8"))
    reduction = round(100 * (1 - filtered_size / original_size), 1)

    print(json.dumps({
        "profile": args.profile,
        "output": args.output,
        "original_bytes": original_size,
        "filtered_bytes": filtered_size,
        "reduction_pct": reduction,
    }), file=sys.stdout)

    print(
        f"[filter_script] {args.profile}: {original_size:,} -> {filtered_size:,} bytes "
        f"({reduction}% reduction)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
