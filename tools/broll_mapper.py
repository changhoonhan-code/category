"""
B-roll Mapper CLI Tool — 대본 블록에 확정된 미디어 매핑을 주입하는 도구.

현재는 AI 매칭 로직이 모두 Agent(SKILL.md)로 이관되었으며, 
이 스크립트는 확정된 block_visual_mapping.json을 읽어 대본에 주입(Inject)하는 단순 역할만 수행합니다.

사용법:
    python tools/broll_mapper.py \
        --script       data/script_output.json \
        --media-dir    data/ \
        --mapping      data/block_visual_mapping.json \
        --output       data/script_with_media.json
"""
import argparse
import json
import os
import sys
from typing import Dict, List, Tuple

def inject_from_mapping(
    script: dict,
    mapping: dict,
    media_dir: str,
) -> Tuple[dict, int, List[str]]:
    """block_visual_mapping.json 기반으로 broll_asset을 스크립트에 주입.

    워크플로우 스키마:
    { "block_id": { "media": [...], "ai_generation_hint": "..." } }

    Returns:
        (수정된 스크립트, 매핑된 블록 수, AI 생성 대상 블록 ID 리스트)
    """
    mapped_count = 0
    ai_generation_blocks: List[str] = []

    for scene in script.get("scenes", []):
        for block in scene.get("blocks", []):
            block_id = block.get("block_id", "")
            if block_id not in mapping:
                continue

            entry = mapping[block_id]
            media_list = entry.get("media", [])
            ai_hint = entry.get("ai_generation_hint")
            fallback_dur = block.get("duration_sec", 5.0)

            # AI 생성 대상 (media가 비어 있고 ai_generation_hint만 있는 경우)
            if not media_list and ai_hint:
                ai_generation_blocks.append(block_id)
                continue

            if not media_list:
                continue

            # ── 주성분 결정 및 주입 ──
            # 여러 개의 사진이 있는 경우 몽타주로 처리
            photos = [m for m in media_list if m.get("type") == "photo"]
            videos = [m for m in media_list if m.get("type") == "video"]

            if len(photos) >= 2 and not videos:
                # 사진 몽타주 모드
                primary = photos[0]
                montage_paths = [m.get("path") or m.get("filename") for m in photos if m.get("path") or m.get("filename")]
                
                block["broll_asset"] = {
                    "type": "photo_montage",
                    "filepath": os.path.join(media_dir, montage_paths[0]),
                    "photos": [os.path.join(media_dir, p) for p in montage_paths],
                    "photo_duration_sec": 1.5,
                    "start_time_sec": 0.0,
                    "end_time_sec": fallback_dur,
                    "fallback_used": False,
                    "selection_reason": primary.get("reason", ""),
                    "category": primary.get("category", "thematic"),
                }
                mapped_count += 1
            else:
                # 단일 에셋 모드 (비디오 우선)
                primary = videos[0] if videos else (photos[0] if photos else media_list[0])
                asset_type = primary.get("type", "video")
                source_path = primary.get("path") or primary.get("filename") or ""
                
                # 경로 해석 (media_dir 기준)
                filepath = os.path.join(media_dir, source_path) if source_path else ""

                if asset_type == "photo":
                    block["broll_asset"] = {
                        "type": "photo",
                        "filepath": source_path,
                        "start_time_sec": 0.0,
                        "end_time_sec": fallback_dur,
                        "fallback_used": False,
                        "selection_reason": primary.get("reason", ""),
                        "category": primary.get("category", "context"),
                    }
                else:
                    # 비디오
                    block["broll_asset"] = {
                        "type": "video",
                        "filepath": source_path,
                        "start_time_sec": primary.get("start_time_sec", 0),
                        "end_time_sec": primary.get("end_time_sec", 5),
                        "fallback_used": False,
                        "selection_reason": primary.get("reason", ""),
                        "category": primary.get("category", "evidence"),
                    }
                mapped_count += 1

    return script, mapped_count, ai_generation_blocks

def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens B-roll Mapper — 대본 블록에 확정된 미디어 매핑을 주입하는 도구.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""사용 예시:
  python tools/broll_mapper.py \
      --script data/script_output.json \
      --media-dir data/ \
      --mapping data/block_visual_mapping.json \
      --output data/script_with_media.json
"""
    )
    parser.add_argument("--script", required=True, help="입력 대본 JSON 파일 경로")
    parser.add_argument("--media-dir", required=True, help="미디어 기본 디렉터리 경로")
    parser.add_argument("--mapping", required=True, help="block_visual_mapping.json 경로 (필수)")
    parser.add_argument("--output", required=True, help="B-roll 주입된 최종 대본 저장 경로")

    args = parser.parse_args()

    if not os.path.exists(args.script):
        print(f"[broll_mapper] ERROR: 대본 파일을 찾을 수 없음: {args.script}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.mapping):
        print(f"[broll_mapper] ERROR: 매핑 파일을 찾을 수 없음: {args.mapping}", file=sys.stderr)
        sys.exit(1)

    print(f"[broll_mapper] 대본 로드: {args.script}", file=sys.stderr, flush=True)
    with open(args.script, "r", encoding="utf-8") as f:
        script = json.load(f)

    print(f"[broll_mapper] 매핑 로드: {args.mapping}", file=sys.stderr, flush=True)
    with open(args.mapping, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    # ── 하이브리드 수동 리뷰 검증 로직 ──
    pending_blocks = [bid for bid, entry in mapping.items() if entry.get("requires_expert_review")]
    if pending_blocks:
        print(f"\n[broll_mapper] ❌ ERROR: 파이프라인 중단 - 수동 리뷰가 완료되지 않음", file=sys.stderr)
        print(f"[broll_mapper] 다음 블록들에 대한 전문가 수동 리뷰(Expert Review)가 필요합니다:", file=sys.stderr)
        print(f"[broll_mapper] 대기 중인 블록: {', '.join(pending_blocks)}", file=sys.stderr)
        print(f"[broll_mapper] 수동 리뷰를 마치고 'requires_expert_review' 플래그를 제거한 후 다시 실행하세요.\n", file=sys.stderr)
        sys.exit(1)

    final_script, mapped_count, ai_blocks = inject_from_mapping(script, mapping, args.media_dir)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(final_script, f, indent=2, ensure_ascii=False)

    print(f"[broll_mapper] ✅ 매핑 주입 완료: {args.output} (매핑 {mapped_count}건)", file=sys.stderr, flush=True)
    if ai_blocks:
        print(f"[broll_mapper] ⚠️ AI 생성 대상 블록 ({len(ai_blocks)}개): {', '.join(ai_blocks)}", file=sys.stderr, flush=True)

    result = {
        "output_path": args.output,
        "mapped_count": mapped_count,
        "mode": "injection_only",
        "ai_generation_blocks": ai_blocks,
    }
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
