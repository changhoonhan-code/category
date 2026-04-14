"""
블록별 미디어 후보를 사전 필터링하는 CLI 도구.

스크립트 블록의 narration/theme 키워드와 미디어 메타데이터의
search_keywords, core_aspect, broll_description 간 키워드 오버랩을 계산하여
블록당 관련도 순으로 정렬된 후보 리스트를 생성한다.

사용법:
    python tools/filter_media.py \\
        --script data/script_output.json \\
        --movies-meta data/movies_meta/movie_metadata_extracted.json \\
        --photos-meta data/photos_meta/photos_metadata_extracted.json \\
        --output data/media_candidates.json

출력:
    블록별 비디오 top 5 + 사진 top 10 후보 리스트 (data/media_candidates.json)
"""
import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

from config import DATAS_DIR


# ── 키워드 추출 ──────────────────────────────────────────────────────────────

def _extract_keywords(text: str) -> Set[str]:
    """텍스트에서 의미 있는 키워드를 추출 (3글자 이상, 소문자)."""
    if not text or not isinstance(text, str):
        return set()
        
    # 일반적인 불용어 목록
    stopwords = {
        "the", "and", "but", "for", "are", "was", "were", "has", "have", "had",
        "this", "that", "with", "from", "they", "been", "will", "would", "could",
        "should", "into", "than", "then", "when", "what", "which", "where", "who",
        "how", "not", "all", "can", "her", "his", "its", "our", "your", "out",
        "about", "just", "more", "also", "very", "most", "some", "only", "over",
        "such", "here", "there", "these", "those", "each", "every", "both",
        "after", "before", "between", "under", "again", "does", "did", "doing",
    }
    words = set(re.findall(r"[a-zA-Z]{3,}", text.lower()))
    return words - stopwords


def _compute_relevance(
    block_keywords: Set[str],
    media_keywords: List[str],
    media_desc: str,
    media_aspects: List[str],
    media_themes: List[str] = None,
    block_theme: str = "",
    matching_block_ids: List[str] = None,
    block_id: str = "",
) -> int:
    """블록 키워드와 미디어 메타데이터 간 관련도 점수 계산."""
    score = 0

    # -1. matching_block_ids 직접 매칭 (가중치 20 — 최우선 시그널: 나레이션 컨텍스트 기반 모델 태깅)
    if matching_block_ids and block_id and block_id in matching_block_ids:
        score += 20

    # 0. related_themes 테마 직접 매칭 (가중치 15 — 가장 강력한 시그널)
    if media_themes and block_theme:
        # 블록 테마 정규화 (예: "Camera Performance" -> "camera performance")
        block_theme_norm = block_theme.lower().replace("_", " ").strip()
        for mt in media_themes:
            mt_norm = mt.lower().replace("_", " ").strip()
            if mt_norm == block_theme_norm:
                score += 15  # 완전 일치
            elif mt_norm in block_theme_norm or block_theme_norm in mt_norm:
                score += 8   # 부분 일치

    # 1. search_keywords 매칭 (가중치 3)
    for kw in media_keywords:
        if not kw or not isinstance(kw, str):
            continue
        kw_words = set(kw.lower().split())
        if kw_words & block_keywords:
            score += 3

    # 2. core_aspect 매칭 (가중치 2)
    for aspect in media_aspects:
        if not aspect or not isinstance(aspect, str):
            continue
        aspect_words = set(aspect.lower().split())
        if aspect_words & block_keywords:
            score += 2

    # 3. broll_description / text_in_image 단어 매칭 (가중치 1)
    if media_desc:
        desc_words = _extract_keywords(media_desc)
        overlap = desc_words & block_keywords
        score += len(overlap)

    return score


# ── 미디어 메타데이터 로드 ───────────────────────────────────────────────────

def _load_media_meta(path: str, media_type: str) -> List[Dict]:
    """미디어 메타 JSON 파일을 로드하여 정규화된 리스트 반환."""
    if not os.path.exists(path):
        print(f"[filter_media] 경고: 파일 없음: {path}", file=sys.stderr)
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[filter_media] 오류: {path} 로드 실패: {e}", file=sys.stderr)
        return []

    items = data if isinstance(data, list) else [data]
    result = []

    for item in items:
        if not item or not isinstance(item, dict):
            continue

        if media_type == "video":
            filename = item.get("video_filename", "")
            if not filename:
                continue
            result.append({
                "filename": filename,
                "type": "video",
                "review_id": item.get("review_id", ""),
                "core_aspect": item.get("core_aspect", ""),
                "broll_description": item.get("broll_description", ""),
                "search_keywords": item.get("search_keywords", []),
                "related_themes": item.get("related_themes", []),
                "matching_block_ids": item.get("matching_block_ids", []),
                "sentiment": item.get("sentiment", ""),
                "start_time": item.get("broll_start_time", "0:00"),
                "end_time": item.get("broll_end_time", "0:05"),
            })
        elif media_type == "photo":
            filename = item.get("image_filename", "")
            if not filename:
                continue
            result.append({
                "filename": filename,
                "type": "photo",
                "core_aspect": item.get("core_aspect", ""),
                "text_in_image": item.get("text_in_image", ""),
                "visual_evidence": item.get("visual_evidence", ""),
                "search_keywords": item.get("search_keywords", []),
                "related_themes": item.get("related_themes", []),
                "matching_block_ids": item.get("matching_block_ids", []),
                "sentiment": item.get("sentiment", ""),
                "is_helpful_for_guide": item.get("is_helpful_for_guide", False),
            })

    return result


# ── 메인 로직 ────────────────────────────────────────────────────────────────

def build_candidates(
    script: dict,
    videos: List[Dict],
    photos: List[Dict],
    video_top_k: int = 5,
    photo_top_k: int = 10,
) -> Dict[str, Dict]:
    """스크립트 블록별 미디어 후보를 생성."""
    candidates = {}

    # 스크립트에서 블록 추출
    blocks = []
    for scene in script.get("scenes", []):
        scene_id = scene.get("scene_id", "")
        for block in scene.get("blocks", []):
            blocks.append({
                "block_id": block.get("block_id", ""),
                "narration": block.get("narration", ""),
                "scene_id": scene_id,
                "evidence_quotes": block.get("evidence_quotes", []),
            })

    for block in blocks:
        block_id = block["block_id"]
        narration = block["narration"]

        # 블록 키워드 구성: narration + scene_id + evidence_quotes 텍스트
        block_text = narration
        block_text += " " + block["scene_id"].replace("_", " ")
        for eq in block.get("evidence_quotes", []):
            hp = eq.get("highlight_phrase", "")
            if hp:
                block_text += " " + hp

        block_keywords = _extract_keywords(block_text)

        # 비디오 후보 점수 계산
        video_scored = []
        for v in videos:
            desc = v.get("broll_description") or ""
            kws = v.get("search_keywords") or []
            aspects = [v.get("core_aspect")] if v.get("core_aspect") else []
            themes = v.get("related_themes") or []
            score = _compute_relevance(block_keywords, kws, desc, aspects, themes, block["scene_id"], v.get("matching_block_ids", []), block_id)
            if score > 0:
                video_scored.append({
                    "filename": v["filename"],
                    "review_id": v.get("review_id") or "",
                    "core_aspect": v.get("core_aspect") or "",
                    "broll_description": desc[:200],
                    "sentiment": v.get("sentiment") or "",
                    "start_time": v.get("start_time") or "0:00",
                    "end_time": v.get("end_time") or "0:05",
                    "related_themes": themes,
                    "matching_block_ids": v.get("matching_block_ids", []),
                    "relevance_score": score,
                })

        video_scored.sort(key=lambda x: x["relevance_score"], reverse=True)

        # 사진 후보 점수 계산
        photo_scored = []
        for p in photos:
            text_in = p.get("text_in_image") or ""
            visual_ev = p.get("visual_evidence") or ""
            desc = text_in + " " + visual_ev
            kws = p.get("search_keywords") or []
            aspects = [p.get("core_aspect")] if p.get("core_aspect") else []
            themes = p.get("related_themes") or []
            score = _compute_relevance(block_keywords, kws, desc, aspects, themes, block["scene_id"], p.get("matching_block_ids", []), block_id)
            if score > 0:
                photo_scored.append({
                    "filename": p["filename"],
                    "core_aspect": p.get("core_aspect") or "",
                    "sentiment": p.get("sentiment") or "",
                    "is_helpful_for_guide": p.get("is_helpful_for_guide", False),
                    "related_themes": themes,
                    "relevance_score": score,
                })

        photo_scored.sort(key=lambda x: x["relevance_score"], reverse=True)

        # evidence_quotes에 has_media=true인 항목이 있는지 확인
        has_evidence_media = any(
            eq.get("has_media", False) for eq in block.get("evidence_quotes", [])
        )

        candidates[block_id] = {
            "narration_excerpt": narration[:100] + ("..." if len(narration) > 100 else ""),
            "theme": block["scene_id"].replace("theme_breakdown_", "").replace("_", " ").title(),
            "video_candidates": video_scored[:video_top_k],
            "photo_candidates": photo_scored[:photo_top_k],
            "has_evidence_media": has_evidence_media,
        }

    return candidates


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: 블록별 미디어 후보 사전 필터링 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""사용 예시:
  python tools/filter_media.py \\
      --script data/script_output.json \\
      --movies-meta data/movies_meta/movie_metadata_extracted.json \\
      --photos-meta data/photos_meta/photos_metadata_extracted.json \\
      --output data/media_candidates.json

출력 (stdout):
  {"output_path": "...", "block_count": 18, "video_pool": 15, "photo_pool": 40}
""",
    )
    parser.add_argument(
        "--script", default=os.path.join(DATAS_DIR, "final_script_with_narration.json"),
        help="입력 대본 JSON 파일 경로 (기본값: data/final_script_with_narration.json)",
    )
    parser.add_argument(
        "--movies-meta", required=True,
        help="영상 메타데이터 JSON 파일 경로",
    )
    parser.add_argument(
        "--photos-meta", required=True,
        help="사진 메타데이터 JSON 파일 경로",
    )
    parser.add_argument(
        "--output", default=os.path.join(DATAS_DIR, "media_candidates.json"),
        help="출력 파일 경로 (기본값: data/media_candidates.json)",
    )
    parser.add_argument(
        "--video-top-k", type=int, default=5,
        help="블록당 비디오 후보 수 (기본값: 5)",
    )
    parser.add_argument(
        "--photo-top-k", type=int, default=10,
        help="블록당 사진 후보 수 (기본값: 10)",
    )

    args = parser.parse_args()

    # 입력 검증
    if not os.path.exists(args.script):
        print(f"[filter_media] ERROR: 대본 파일 없음: {args.script}", file=sys.stderr)
        sys.exit(1)

    # 스크립트 로드
    print(f"[filter_media] 대본 로드: {args.script}", file=sys.stderr, flush=True)
    with open(args.script, "r", encoding="utf-8") as f:
        script = json.load(f)

    # 미디어 메타 로드
    videos = _load_media_meta(args.movies_meta, "video")
    photos = _load_media_meta(args.photos_meta, "photo")
    print(f"[filter_media] 미디어 풀: 비디오 {len(videos)}개, 사진 {len(photos)}개", file=sys.stderr, flush=True)

    # 후보 생성
    candidates = build_candidates(
        script, videos, photos,
        video_top_k=args.video_top_k,
        photo_top_k=args.photo_top_k,
    )

    # 저장
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)

    # 통계 요약
    total_video_matches = sum(
        len(c["video_candidates"]) for c in candidates.values()
    )
    total_photo_matches = sum(
        len(c["photo_candidates"]) for c in candidates.values()
    )
    blocks_with_evidence = sum(
        1 for c in candidates.values() if c["has_evidence_media"]
    )

    print(
        f"[filter_media] ✅ 저장 완료: {args.output} "
        f"({len(candidates)} 블록, 비디오 매치 {total_video_matches}건, 사진 매치 {total_photo_matches}건, "
        f"evidence 미디어 {blocks_with_evidence}건)",
        file=sys.stderr, flush=True,
    )

    # stdout에 결과 JSON 출력 (쇼러너가 파싱)
    result = {
        "output_path": args.output,
        "block_count": len(candidates),
        "video_pool": len(videos),
        "photo_pool": len(photos),
        "total_video_matches": total_video_matches,
        "total_photo_matches": total_photo_matches,
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
