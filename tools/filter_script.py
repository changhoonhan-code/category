"""
Filter script JSON for agent-specific profiles — reduces token cost by providing
each agent only the fields it needs from the master script.

Usage:
    python tools/filter_script.py --profile narration
    python tools/filter_script.py --profile narration --output tmp/script_narration.json
    python tools/filter_script.py --profile narration --scenes hook,intro_credibility
    python tools/filter_script.py --profile narration --group 2
    python tools/filter_script.py --profile validator

Profiles: narration, validator

--scenes 옵션: 쉼표 구분 scene_id 리스트. 지정하면 해당 씬만 포함.
    미지정 시 전체 씬 유지 (기존 동작과 동일).
--group 옵션: Sequential N-block 실행을 위한 순차 블록 분배.
    1-based 정수. 각 그룹은 BLOCKS_PER_GROUP(config.py)개 블록을 순서대로 처리.
    --group 지정 시 --scenes는 무시되며, 출력 경로도 자동 설정된다.
"""
import argparse
import json
import os
import sys

from config import DATAS_DIR, TMP_DIR

# ── Profile Definitions ─────────────────────────────────────────────────────
# 각 프로필은 스크립트 JSON에서 포함할 필드를 지정한다.
# - root_fields: 최상위 키 ("scenes"는 항상 유지)
# - scene_fields: scene-level 키 (scene_id는 항상 유지)
# - block_fields: block-level 키
# - quote_fields: evidence_quotes 내부 필드 (None이면 quotes 배열 완전 제거)
# - dynamic_fields: 필터링 시 동적으로 계산해서 블록에 추가하는 필드

PROFILES = {
    "narration": {
        "root_fields": ["category_name", "products", "video_question"],
        "scene_fields": [],
        "block_fields": ["block_id", "narration", "pacing_profile"],
        "quote_fields": None,  # quotes 완전 제거 (나레이션에 불필요)
        "dynamic_fields": [],
    },
    "validator": {
        "root_fields": ["video_question", "category_name", "products", "excluded_themes", "teaser_payoff_map"],
        "scene_fields": ["scene_type"],
        "block_fields": ["block_id", "narration", "pacing_profile", "title", "headline"],
        # CHECK 3 검증에 필요한 필드만 유지 (full metadata 제거)
        "quote_fields": ["product_id", "review_id", "highlight_phrase", "star_rating", "selection_reason"],
        "dynamic_fields": [],
    },
    "creative": {
        "root_fields": ["category_name", "products", "video_question"],
        "scene_fields": ["scene_type"],
        "block_fields": ["block_id", "narration", "pacing_profile", "is_humorous"],
        # CD가 is_humorous 태깅 + 인용구 컨텍스트 참조용
        "quote_fields": ["product_id", "highlight_phrase", "star_rating", "review_id", "selection_reason", "is_humorous"],
        "dynamic_fields": [],
    },
}

# ── 프로필별 기본 입력 파일 ──────────────────────────────────────────────────
# narration: Audio Production 이후의 script_output.json
# validator: Review Relay의 draft_script.json
INPUT_DEFAULTS = {
    "narration": os.path.join(DATAS_DIR, "script_output.json"),
    "validator": os.path.join(DATAS_DIR, "draft_script.json"),
    "creative": os.path.join(DATAS_DIR, "draft_script.json"),
}

# ── Group Definitions ────────────────────────────────────────────────────────
# Sequential N-block grouping — 스크립트 순서대로 BLOCKS_PER_GROUP개씩 분배.
# 키워드 분류 없이 순수 블록 수 기반. 그룹 ID는 1-based 정수.
from config import BLOCKS_PER_GROUP


def resolve_group_blocks(data: dict, group: int) -> list[str]:
    """그룹 번호에 따라 block_id 리스트를 순차적으로 반환한다.

    전체 블록을 스크립트 순서대로 나열한 뒤,
    BLOCKS_PER_GROUP 단위로 분할하여 해당 그룹의 블록만 반환.

    Args:
        data: script_output.json 원본 데이터
        group: 1-based 그룹 번호

    Returns:
        해당 그룹에 포함될 block_id 리스트
    """
    all_blocks = [
        block["block_id"]
        for scene in data.get("scenes", [])
        for block in scene.get("blocks", [])
    ]
    total = len(all_blocks)
    max_groups = (total + BLOCKS_PER_GROUP - 1) // BLOCKS_PER_GROUP

    if group < 1 or group > max_groups:
        print(
            f"[filter_script] ERROR: Group {group} out of range. "
            f"Total {total} blocks → {max_groups} groups (1–{max_groups}).",
            file=sys.stderr,
        )
        sys.exit(1)

    start = (group - 1) * BLOCKS_PER_GROUP
    end = min(start + BLOCKS_PER_GROUP, total)

    print(
        f"[filter_script] Group {group}/{max_groups}: blocks {start+1}–{end} of {total}",
        file=sys.stderr,
    )
    return all_blocks[start:end]


def filter_script(data: dict, profile: dict, scenes: list[str] | None = None,
                   blocks: list[str] | None = None) -> dict:
    """스크립트 JSON에 필터 프로필을 적용한다.

    Args:
        data: 스크립트 원본 데이터 (script_output.json 또는 draft_script.json)
        profile: 에이전트 프로필 (root_fields, scene_fields, block_fields, quote_fields, dynamic_fields)
        scenes: 포함할 scene_id 리스트 (None이면 전체 씬 유지)
        blocks: 포함할 block_id 리스트 (None이면 전체 블록 유지)
    """
    result = {}

    # 루트 필드 필터링
    for key in profile.get("root_fields", []):
        if key in data:
            result[key] = data[key]

    block_fields = set(profile.get("block_fields", []))
    scene_fields = set(profile.get("scene_fields", []))
    quote_fields = profile.get("quote_fields")  # None이면 quotes 완전 제거, 리스트면 해당 필드만 유지
    dynamic_fields = set(profile.get("dynamic_fields", []))
    blocks_set = set(blocks) if blocks else set()

    result["scenes"] = []
    for scene in data.get("scenes", []):
        # 씬 필터링: --scenes 지정 시 해당 scene_id만 포함
        if scenes and scene["scene_id"] not in scenes:
            continue

        # 블록 필터링: blocks 지정 시 해당 블록이 없는 씬은 건너뜀
        if blocks_set:
            scene_block_ids = {b.get("block_id") for b in scene.get("blocks", [])}
            if not scene_block_ids & blocks_set:
                continue

        # scene-level 필드 보존 (scene_id는 항상 유지)
        filtered_scene = {"scene_id": scene["scene_id"]}
        for sf in scene_fields:
            if sf in scene:
                filtered_scene[sf] = scene[sf]

        filtered_scene["blocks"] = []
        for block in scene.get("blocks", []):
            # 블록 필터링: blocks 지정 시 해당 block_id만 포함
            if blocks_set and block.get("block_id") not in blocks_set:
                continue

            # block-level 필드 필터링
            filtered_block = {k: v for k, v in block.items() if k in block_fields}

            # evidence_quotes 처리
            if quote_fields is not None:
                raw_quotes = block.get("evidence_quotes", [])
                qf_set = set(quote_fields)
                filtered_block["evidence_quotes"] = [
                    {k: v for k, v in eq.items() if k in qf_set}
                    for eq in raw_quotes
                ]
            # quote_fields가 None이면 evidence_quotes 자체를 포함하지 않음

            filtered_scene["blocks"].append(filtered_block)

        if filtered_scene["blocks"]:  # 빈 씬은 결과에서 제외
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
        "--input", default=None,
        help="Source script JSON path (default: profile-dependent — see INPUT_DEFAULTS)"
    )
    parser.add_argument(
        "--scenes", default=None,
        help="Comma-separated scene_ids to include (default: all scenes). "
             "Example: --scenes hook,intro_credibility"
    )
    parser.add_argument(
        "--group", default=None, type=int,
        help="Group number (1-based). Each group processes up to "
             f"{BLOCKS_PER_GROUP} blocks sequentially. "
             "Overrides --scenes and auto-sets output path."
    )
    parser.add_argument(
        "--output", default=None,
        help="Output path (default: tmp/script_{profile}.json)"
    )
    args = parser.parse_args()

    # 프로필별 기본 입력 파일 분기
    if args.input is None:
        args.input = INPUT_DEFAULTS.get(args.profile, os.path.join(DATAS_DIR, "script_output.json"))

    if not os.path.exists(args.input):
        print(json.dumps({"error": f"File not found: {args.input}"}))
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    # --group 옵션: 순차 N-블록 그룹핑
    blocks_filter = None
    scenes_filter = None
    if args.group is not None:
        blocks_filter = resolve_group_blocks(data, args.group)
        if not blocks_filter:
            print(f"[filter_script] Warning: Group {args.group} resolved to 0 blocks.")
            sys.exit(1)
        if args.output is None:
            args.output = os.path.join(TMP_DIR, f"script_{args.profile}_group{args.group}.json")
    else:
        # 기존 --scenes 옵션 파싱: 쉼표 구분 scene_id 리스트
        scenes_filter = args.scenes.split(",") if args.scenes else None

    # 출력 경로 폴백
    if args.output is None:
        args.output = os.path.join(TMP_DIR, f"script_{args.profile}.json")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    filtered = filter_script(data, PROFILES[args.profile], scenes=scenes_filter, blocks=blocks_filter)

    # 필터링 결과 표시
    total_blocks = sum(len(s.get("blocks", [])) for s in filtered.get("scenes", []))
    if blocks_filter:
        print(
            f"[filter_script] Block filter: {total_blocks} blocks in "
            f"{len(filtered['scenes'])} scenes",
            file=sys.stderr,
        )
    elif scenes_filter:
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

