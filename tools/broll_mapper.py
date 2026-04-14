"""
B-roll Mapper CLI Tool — 대본 블록에 미디어 에셋을 매칭·주입하는 도구.

Migrated from:
  - pipeline/agents/media_mapping.py (BaseAgent 래퍼)
  - pipeline/skills/broll.py (매칭/주입 핵심 로직)
  - pipeline/broll_mapper.py (단독 실행 스크립트)

핵심 변경:
  - BaseAgent 의존성 제거, argparse CLI로 전환
  - AI 이미지/비디오 생성 폴백 제거 (TO-BE에서 쇼러너가 직접 판단)
  - 매칭 로직만 보존: 키워드 1차 → LLM 2차 토너먼트

사용법:
    python tools/broll_mapper.py \\
        --script       data/script_output.json \\
        --media-dir    data/ \\
        --output       data/script_with_media.json

    python tools/broll_mapper.py \\
        --script       data/script_output.json \\
        --media-dir    data/ \\
        --theme-analysis data/theme_analysis.json \\
        --model        gemini-3.1-flash-lite-preview \\
        --output       data/script_with_media.json
"""
import argparse
import glob
import json
import os
import sys
from typing import Dict, List, Optional, Set, Tuple

from google import genai

from config import MODELS


# ── 상수 ──────────────────────────────────────────────────────────────────────

DEFAULT_MODEL = MODELS["analysis"]

# LLM 매칭 설정
_LLM_BATCH_SIZE = 20
_MIN_MATCH_SCORE = 5
_EARLY_EXIT_SCORE = 9




# ── 미디어 풀 구축 ───────────────────────────────────────────────────────────

def _parse_mmss(ts) -> float:
    """MM:SS 문자열 또는 숫자값을 float 초 단위로 변환."""
    if ts is None:
        return 0.0
    try:
        if isinstance(ts, (int, float)):
            return float(ts)
        parts = str(ts).split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except Exception:
        return 0.0


def build_media_pool(
    movies_meta_glob: str,
    photos_meta_glob: str,
) -> Dict[str, Dict]:
    """영상/사진 메타데이터를 통합 풀 딕셔너리로 로드.

    사이드카 파일 하나에 여러 feature가 있을 수 있으므로,
    filename (idx 0) 또는 filename_N (idx > 0) 키로 구분.
    """
    pool: Dict[str, Dict] = {}

    # 영상 메타 로드
    for path in glob.glob(movies_meta_glob):
        try:
            with open(path, "r", encoding="utf-8") as f:
                m_data = json.load(f)
            items = m_data if isinstance(m_data, list) else ([m_data] if isinstance(m_data, dict) else [])
            for idx, m in enumerate(items):
                if not m:
                    continue
                vid = m.get("video_filename")
                if vid:
                    pool_key = vid if idx == 0 else f"{vid}_{idx}"
                    pool[pool_key] = {
                        "id": pool_key,
                        "type": "video",
                        "path": f"movies/{vid}",
                        "desc": m.get("broll_description", ""),
                        "keywords": m.get("search_keywords", []),
                        "start": _parse_mmss(m.get("broll_start_time")),
                        "end": _parse_mmss(m.get("broll_end_time")) or 5.0,
                    }
        except Exception as e:
            print(f"[broll_mapper] 경고: 영상 메타 로드 실패 {path}: {e}", file=sys.stderr)

    # 사진 메타 로드
    for path in glob.glob(photos_meta_glob):
        try:
            with open(path, "r", encoding="utf-8") as f:
                m_data = json.load(f)
            items = m_data if isinstance(m_data, list) else ([m_data] if isinstance(m_data, dict) else [])
            for idx, m in enumerate(items):
                if not m:
                    continue
                pid = m.get("image_filename")
                if pid:
                    pool_key = pid if idx == 0 else f"{pid}_{idx}"
                    pool[pool_key] = {
                        "id": pool_key,
                        "type": "photo",
                        "path": f"photos/{pid}",
                        "desc": m.get("text_in_image", m.get("visual_evidence", "")),
                        "keywords": m.get("search_keywords", []),
                        "core_aspects": m.get("core_aspect", []) if isinstance(m.get("core_aspect"), list) else ([m.get("core_aspect")] if m.get("core_aspect") else []),
                        "start": 0.0,
                        "end": 0.0,
                    }
        except Exception as e:
            print(f"[broll_mapper] 경고: 사진 메타 로드 실패 {path}: {e}", file=sys.stderr)

    return pool


def build_evidence_media_map(theme_analysis_path: str) -> Dict[str, Dict]:
    """theme_analysis.json의 evidence_quotes에서 review_id → {paths, descs} 매핑 추출."""
    media_map: Dict[str, Dict] = {}
    if not os.path.exists(theme_analysis_path):
        return media_map
    try:
        with open(theme_analysis_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # summary.json인 경우 'themes' 키 아래에 리스트가 있음
            themes = data.get("themes", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        for theme in themes:
            for eq in theme.get("evidence_quotes", []):
                rid = eq.get("review_id", "")
                if rid and eq.get("has_media", False):
                    media_map[rid] = {
                        "paths": eq.get("media_paths", []),
                        "descs": eq.get("media_descriptions", []),
                    }
    except Exception as e:
        print(f"[broll_mapper] 경고: evidence media 로드 실패: {e}", file=sys.stderr)
    return media_map


# ── 매칭 (키워드 → LLM 2단계) ────────────────────────────────────────────────

def match_broll_keyword_first(
    narration: str,
    pool: Dict[str, Dict],
    used_ids: Set[str],
) -> Optional[str]:
    """키워드 기반 1차 매칭 (무료, API 호출 없음)."""
    narration_lower = narration.lower()
    best_match: Optional[str] = None
    best_score = 0

    for m_id, m in pool.items():
        if m_id in used_ids:
            continue
        score = 0
        for kw in m.get("keywords", []):
            if kw.lower() in narration_lower:
                score += 2
        for word in str(m.get("desc", "")).lower().split():
            if len(word) > 3 and word in narration_lower:
                score += 1
        # core_aspect 필드도 매칭에 활용
        for aspect in m.get("core_aspects", []):
            if aspect.lower() in narration_lower:
                score += 2
        if score > best_score:
            best_score = score
            best_match = m_id

    return best_match if best_score >= 2 else None


_LLM_MATCHER_PROMPT = """You are a video editor matching narration to B-roll footage.
Given the narration line below, select the SINGLE best matching media item from the provided candidate list.
Criteria:
1. Semantic relevance (e.g., if talking about battery, pick a charging video or close-up photo).
2. Judge purely by content relevance — do NOT prefer videos over photos or vice versa.
3. If no candidate is even remotely relevant, return null and set score to 0.

Target Narration:
"{narration}"

Available Candidates:
{candidates_text}

Output ONLY valid JSON. No markdown blocks. Format:
{{
  "selected_media_id": "ID of the best match, or null if nothing fits",
  "score": <integer 0-10 indicating relevance; 0 if no match>,
  "reason": "Very brief 1 sentence reason"
}}
"""


def _format_candidate_line(m_id: str, m: Dict) -> str:
    """LLM 프롬프트용 후보 에셋 한 줄 포맷."""
    m_type = "V" if m["type"] == "video" else "P"
    desc = str(m.get("desc", "")).replace("\n", " ")
    kws = ", ".join(m.get("keywords", []))
    return f"[{m_id}] ({m_type}) Desc: {desc} | Keywords: {kws}"


def match_broll_using_llm(
    narration: str,
    pool: Dict[str, Dict],
    used_ids: Set[str],
    client: genai.Client,
    model_id: str,
) -> Optional[str]:
    """LLM 기반 2차 매칭 — 토너먼트 방식.

    Pass 1: 배치별 우승자 수집. 점수 >= _EARLY_EXIT_SCORE면 즉시 반환.
    Pass 2: 배치 우승자끼리 결승전으로 최종 선택.
    """
    candidates = [(m_id, m) for m_id, m in pool.items() if m_id not in used_ids]
    if not candidates:
        return None

    # Pass 1: 배치별 우승자 수집
    batch_winners: List[Tuple[str, int]] = []

    for batch_idx, batch_start in enumerate(range(0, len(candidates), _LLM_BATCH_SIZE)):
        batch = candidates[batch_start:batch_start + _LLM_BATCH_SIZE]
        lines = [_format_candidate_line(m_id, m) for m_id, m in batch]
        candidates_text = "\n".join(lines)
        prompt = _LLM_MATCHER_PROMPT.format(narration=narration, candidates_text=candidates_text)

        try:
            response = client.models.generate_content(model=model_id, contents=prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            m_id = result.get("selected_media_id")
            score = int(result.get("score", 0))
            if m_id and m_id in pool and m_id not in used_ids and score > 0:
                # 매우 높은 확신도면 즉시 반환
                if score >= _EARLY_EXIT_SCORE:
                    print(f"(early exit, score={score})", end=" ", file=sys.stderr)
                    return m_id if score >= _MIN_MATCH_SCORE else None
                batch_winners.append((m_id, score))
        except Exception as e:
            print(f"  -> LLM 매칭 오류 (배치 {batch_idx + 1}): {e}", file=sys.stderr)

    if not batch_winners:
        return None

    # 우승자가 1명이면 결승전 불필요
    if len(batch_winners) == 1:
        m_id, score = batch_winners[0]
        return m_id if score >= _MIN_MATCH_SCORE else None

    # Pass 2: 결승전 — 배치 우승자끼리 재대결
    finals_lines = [_format_candidate_line(m_id, pool[m_id]) for m_id, _ in batch_winners]
    candidates_text = "\n".join(finals_lines)
    prompt = _LLM_MATCHER_PROMPT.format(narration=narration, candidates_text=candidates_text)

    try:
        response = client.models.generate_content(model=model_id, contents=prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        m_id = result.get("selected_media_id")
        score = int(result.get("score", 0))
        if m_id and m_id in pool and m_id not in used_ids and score >= _MIN_MATCH_SCORE:
            return m_id
    except Exception as e:
        print(f"  -> LLM 결승전 오류: {e}", file=sys.stderr)

    # 결승전 실패 시 배치 우승자 중 최고 점수 반환
    batch_winners.sort(key=lambda x: x[1], reverse=True)
    best_id, best_score = batch_winners[0]
    return best_id if best_score >= _MIN_MATCH_SCORE else None


# ── 스크립트 주입 ─────────────────────────────────────────────────────────────

def _make_broll_asset(media: Dict, fallback_duration: float) -> Dict:
    """매칭된 미디어 에셋을 broll_asset 포맷으로 변환."""
    asset = {
        "type": media["type"],
        "filepath": media["path"],
        "start_time_sec": media["start"],
        "end_time_sec": media["end"] if media["type"] == "video" else fallback_duration,
        "fallback_used": media["type"] == "photo",
    }
    
    if media["type"] == "photo":
        import random
        pattern = random.choice(["zoom_in", "pan_right", "pan_left", "zoom_out"])
        dur = fallback_duration
        
        if pattern == "zoom_in":
            keyframes = [
                {"time_sec": 0, "x": 960, "y": 540, "scale": 1.0},
                {"time_sec": dur, "x": 960, "y": 540, "scale": 1.15}
            ]
        elif pattern == "zoom_out":
            keyframes = [
                {"time_sec": 0, "x": 960, "y": 540, "scale": 1.2},
                {"time_sec": dur, "x": 960, "y": 540, "scale": 1.0}
            ]
        elif pattern == "pan_right":
            keyframes = [
                {"time_sec": 0, "x": 860, "y": 540, "scale": 1.1},
                {"time_sec": dur, "x": 1060, "y": 540, "scale": 1.1}
            ]
        else: # pan_left
            keyframes = [
                {"time_sec": 0, "x": 1060, "y": 540, "scale": 1.1},
                {"time_sec": dur, "x": 860, "y": 540, "scale": 1.1}
            ]
        asset["camera_keyframes"] = keyframes
        
    return asset


def _find_related_photos(
    narration: str,
    pool: Dict[str, Dict],
    used_ids: Set[str],
    top_k: int = 5,
) -> List[str]:
    """나레이션과 관련된 사진을 점수 기반으로 top_k개 선별."""
    scored: List[Tuple[str, int]] = []
    narration_lower = narration.lower()

    for m_id, m in pool.items():
        if m_id in used_ids or m["type"] != "photo":
            continue
        score = 0
        for kw in m.get("keywords", []):
            if kw.lower() in narration_lower:
                score += 2
        for aspect in m.get("core_aspects", []):
            if aspect.lower() in narration_lower:
                score += 2
        for word in str(m.get("desc", "")).lower().split():
            if len(word) > 3 and word in narration_lower:
                score += 1
        if score > 0:
            scored.append((m_id, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [m_id for m_id, _ in scored[:top_k]]


def _make_montage_asset(photos: List[str], pool: Dict[str, Dict], duration: float) -> Dict:
    """사진 몽타주 에셋 생성. 카드 프레임 안에서 순차 전환."""
    return {
        "type": "photo_montage",
        "filepath": pool[photos[0]]["path"],  # 대표 경로 (첫 번째 사진)
        "photos": [pool[pid]["path"] for pid in photos],
        "photo_duration_sec": 1.5,  # 기본값, 쇼러너가 블록별 오버라이드 가능
        "start_time_sec": 0.0,
        "end_time_sec": duration,
        "fallback_used": True,
    }


def inject_broll_into_script(
    script: dict,
    pool: Dict[str, Dict],
    evidence_media: Dict[str, Dict],
    client: genai.Client,
    model_id: str,
) -> Tuple[dict, int]:
    """대본 블록에 broll_asset을 주입. (수정된 대본, 매핑 수) 반환.

    매칭 우선순위:
      1순위: 영상/사진 개별 매칭 (키워드 → LLM)
      2순위: 사진 몽타주 폴백 (관련 사진 3~8장)
      3순위: (AI 생성은 쇼러너가 별도 판단)

    used_ids는 씬 단위로 리셋 (같은 에셋이 다른 씬에서 재사용 가능).
    """
    mapped_count = 0
    kw_hits = 0
    llm_hits = 0
    montage_hits = 0
    misses = 0

    if isinstance(script, list):
        script = {"scenes": script}
    if "scenes" not in script:
        print("[broll_mapper] 오류: 잘못된 대본 형식. 'scenes' 키 없음.", file=sys.stderr)
        return script, 0

    if not pool:
        print("[broll_mapper] 경고: 미디어 풀이 비어있음. B-roll 주입 불가.", file=sys.stderr)

    # 역참조: pool path → pool key (evidence_media 직접 주입용)
    path_to_id: Dict[str, str] = {m["path"]: m_id for m_id, m in pool.items()}

    for scene in script["scenes"]:
        used_ids: Set[str] = set()  # 씬 단위 리셋

        for block in scene.get("blocks", []):
            block_id = block.get("block_id", "unknown")
            narration = block.get("narration", "")
            fallback_dur = block.get("duration_sec", 5.0)

            # ── evidence_quotes: 3단계 매칭 ──
            evidence_quotes = block.get("evidence_quotes", [])
            if not evidence_quotes:
                eq_text = block.get("evidence_quote")
                if eq_text:
                    import re
                    rid_match = re.search(r"R[A-Z0-9]{10,}", f"{narration} {eq_text}")
                    evidence_quotes = [{"review_id": rid_match.group(0) if rid_match else "", "has_media": True}]

            for eq in (evidence_quotes or []):
                if not (isinstance(eq, dict) and eq.get("has_media", False) and "broll_asset" not in block):
                    continue

                matched_id = None

                # 1단계: evidence_media 맵에서 직접 조회
                rid = eq.get("review_id", "")
                if rid and rid in evidence_media:
                    for path in evidence_media[rid].get("paths", []):
                        candidate = path_to_id.get(path)
                        if candidate and candidate not in used_ids:
                            matched_id = candidate
                            break

                # 2단계: 인용문 텍스트로 키워드 매칭
                if not matched_id:
                    eq_text = eq.get("text", "")
                    if eq_text:
                        matched_id = match_broll_keyword_first(eq_text, pool, used_ids)

                # 3단계: 인용문 텍스트로 LLM 매칭
                if not matched_id:
                    eq_text = eq.get("text", "")
                    if eq_text:
                        matched_id = match_broll_using_llm(eq_text, pool, used_ids, client, model_id)

                if matched_id and matched_id in pool:
                    block["broll_asset"] = _make_broll_asset(pool[matched_id], fallback_dur)
                    used_ids.add(matched_id)
                    mapped_count += 1
                    print(f"  -> Evidence 미디어 주입 '{block_id}': {matched_id}", file=sys.stderr)

            if "broll_asset" in block:
                continue
            if not narration:
                continue

            # ── 나레이션 블록: 3단계 매칭 (영상/사진 → 사진 몽타주 폴백) ──
            print(f"  -> 매칭 '{block_id}'...", end=" ", file=sys.stderr, flush=True)

            # 1순위: 키워드 매칭
            matched_id = match_broll_keyword_first(narration, pool, used_ids)
            if matched_id:
                kw_hits += 1
                print(f"KW: {matched_id}", file=sys.stderr)
            else:
                # 2순위: LLM 매칭
                matched_id = match_broll_using_llm(narration, pool, used_ids, client, model_id)
                if matched_id:
                    llm_hits += 1
                    print(f"LLM: {matched_id}", file=sys.stderr)

            if matched_id and matched_id in pool:
                block["broll_asset"] = _make_broll_asset(pool[matched_id], fallback_dur)
                used_ids.add(matched_id)
                mapped_count += 1
            else:
                # 3순위: 사진 몽타주 폴백 — 관련 사진 여러 장 수집
                related = _find_related_photos(narration, pool, used_ids, top_k=5)
                if len(related) >= 2:
                    block["broll_asset"] = _make_montage_asset(related, pool, fallback_dur)
                    for pid in related:
                        used_ids.add(pid)
                    mapped_count += 1
                    montage_hits += 1
                    print(f"MONTAGE: {len(related)}장", file=sys.stderr)
                else:
                    misses += 1
                    print("매칭 실패.", file=sys.stderr)

    total = kw_hits + llm_hits + montage_hits + misses
    print(
        f"\n  [B-roll] KW: {kw_hits} | LLM: {llm_hits} | 몽타주: {montage_hits} | 실패: {misses} / {total} 블록",
        file=sys.stderr,
    )
    return script, mapped_count


# ── CLI 진입점 ───────────────────────────────────────────────────────────────

# ── 쇼러너 매핑 주입 모드 ────────────────────────────────────────────────────

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


# ── CLI 진입점 ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens B-roll Mapper — 대본 블록에 미디어 에셋을 매칭·주입하는 도구. (키워드 1차 → LLM 2차 토너먼트)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""사용 예시:
  python tools/broll_mapper.py \\
      --script data/script_output.json \\
      --media-dir data/ \\
      --output data/script_with_media.json

출력 (stdout):
  {"output_path": "data/script_with_media.json", "mapped_count": 15, "pool_size": 20}
""",
    )
    parser.add_argument(
        "--script", required=True,
        help="입력 대본 JSON 파일 경로 (예: data/script_output.json)",
    )
    parser.add_argument(
        "--media-dir", required=True,
        help="미디어 메타 디렉터리. movies_meta/*_meta.json, photos_meta/*_meta.json을 여기서 탐색",
    )
    parser.add_argument(
        "--output", required=True,
        help="B-roll 주입된 최종 대본 저장 경로",
    )
    parser.add_argument(
        "--theme-analysis", default=None,
        help="theme_analysis.json 경로 (evidence 미디어 매핑용). 미지정 시 evidence 매칭 건너뜀",
    )
    parser.add_argument(
        "--mapping", default=None,
        help="block_visual_mapping.json 경로. 제공 시 쇼러너 선택 기반 주입 모드로 동작 (레거시 자동 매칭 건너뜀)",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"LLM 매칭용 모델 ID (기본값: {DEFAULT_MODEL})",
    )

    args = parser.parse_args()

    # 입력 검증
    if not os.path.exists(args.script):
        print(f"[broll_mapper] ERROR: 대본 파일을 찾을 수 없음: {args.script}", file=sys.stderr)
        sys.exit(1)

    # 대본 로드
    print(f"[broll_mapper] 대본 로드: {args.script}", file=sys.stderr, flush=True)
    with open(args.script, "r", encoding="utf-8") as f:
        script = json.load(f)

    # ── 모드 분기: --mapping 제공 시 쇼러너 매핑 주입 모드 ──
    if args.mapping:
        if not os.path.exists(args.mapping):
            print(f"[broll_mapper] ERROR: 매핑 파일을 찾을 수 없음: {args.mapping}", file=sys.stderr)
            sys.exit(1)

        print(f"[broll_mapper] 쇼러너 매핑 주입 모드: {args.mapping}", file=sys.stderr, flush=True)
        with open(args.mapping, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        final_script, mapped_count, ai_blocks = inject_from_mapping(
            script, mapping, args.media_dir
        )

        # 결과 저장
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(final_script, f, indent=2, ensure_ascii=False)

        print(f"[broll_mapper] ✅ 매핑 주입 완료: {args.output} (매핑 {mapped_count}건)", file=sys.stderr, flush=True)
        if ai_blocks:
            print(f"[broll_mapper] ⚠️ AI 생성 대상 블록 ({len(ai_blocks)}개): {', '.join(ai_blocks)}", file=sys.stderr, flush=True)

        result = {
            "output_path": args.output,
            "mapped_count": mapped_count,
            "mode": "showrunner_mapping",
            "ai_generation_blocks": ai_blocks,
        }
        print(json.dumps(result, ensure_ascii=False))
        return

    # ── 레거시 자동 매칭 모드 ──
    # 미디어 풀 구축
    movies_glob = os.path.join(args.media_dir, "movies_meta", "*_meta.json")
    photos_glob = os.path.join(args.media_dir, "photos_meta", "*_meta.json")
    pool = build_media_pool(movies_glob, photos_glob)
    n_videos = sum(1 for m in pool.values() if m["type"] == "video")
    n_photos = sum(1 for m in pool.values() if m["type"] == "photo")
    print(f"[broll_mapper] 미디어 풀: {len(pool)}개 에셋 (영상 {n_videos}, 사진 {n_photos})", file=sys.stderr, flush=True)

    # Evidence 미디어 맵 구축 (선택)
    evidence_media: Dict[str, Dict] = {}
    if args.theme_analysis:
        if not os.path.exists(args.theme_analysis):
            print(f"[broll_mapper] 경고: theme_analysis 파일 없음: {args.theme_analysis}", file=sys.stderr)
        else:
            evidence_media = build_evidence_media_map(args.theme_analysis)
            if evidence_media:
                print(f"[broll_mapper] Evidence 미디어: {len(evidence_media)}개 리뷰", file=sys.stderr, flush=True)

    # B-roll 매칭 + 주입 (영상/사진 → 사진 몽타주 → AI 생성은 쇼러너 판단)
    print("[broll_mapper] B-roll 매칭 시작 (키워드 → LLM → 사진 몽타주 3단계)...", file=sys.stderr, flush=True)
    client = genai.Client()
    final_script, mapped_count = inject_broll_into_script(
        script,
        pool,
        evidence_media,
        client,
        args.model,
    )

    # 결과 저장
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(final_script, f, indent=2, ensure_ascii=False)
    print(f"[broll_mapper] ✅ 저장 완료: {args.output} (매핑 {mapped_count}건)", file=sys.stderr, flush=True)

    # stdout에 결과 JSON 출력 (쇼러너가 파싱)
    result = {
        "output_path": args.output,
        "mapped_count": mapped_count,
        "pool_size": len(pool),
        "mode": "legacy_auto",
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
