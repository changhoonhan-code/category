"""
Opening Bracket Audit Tool — 전체 tts_prompt 파일 크로스 씬 Anti-Pattern 검사.

4개 그룹 세션 전체 완료 후, 모든 tts_prompt_*.txt 파일을 스캔하여
크로스 씬 Anti-Pattern 위반을 검사한다.

검사 항목:
  #1: 동일한 Delivery 설명 (Jaccard similarity > 50%)
  #2: 같은 Delivery 패턴 2-gram 3+ 재사용
  #4: 같은 아키타입 3+ 연속
  #5: pacing_profile 준수 (breathe 블록에 [extremely fast] 사용 금지)
  #6: Lineup Equalizer (lineup/verdict_picks 블록에서 제품 항목 간 [short pause] 필요)
  #7: 태그 화이트리스트 (승인된 8개 Pacing/Disfluency 태그만 허용)
  #8: Archetype-BlockType Map 일치 (블록 ID 기반 아키타입 적합성 검사)

Usage:
    python tools/audit_opening_brackets.py
    python tools/audit_opening_brackets.py --threshold 0.5

출력: tmp/bracket_audit_report.json
"""
import argparse
import json
import os
import re
import sys
import glob
from itertools import combinations

from config import TMP_DIR
from prompt_utils import extract_prompt_info


def extract_delivery_and_bracket(prompt_path: str) -> dict:
    """tts_prompt 파일에서 Delivery 설명, bracket 목록, 아키타입 코드를 추출.

    prompt_utils.extract_prompt_info()를 래핑하여 기존 인터페이스를 유지.
    """
    return extract_prompt_info(prompt_path)


def tokenize(text: str) -> set[str]:
    """텍스트를 소문자 단어 집합으로 변환 (불용어 제거).

    일반 불용어 외에 Delivery 설명에서 자연스럽게 반복되는
    메타어/기능어(block, way, you, like 등)를 추가로 제외한다.
    이들은 directing 패턴의 실질적 반복을 나타내지 않으므로
    Jaccard/bigram 검사 대상에서 제외해 false positive를 방지한다.
    """
    stopwords = {
        # 기본 영어 불용어
        "the", "a", "an", "is", "are", "in", "on", "at", "to", "for",
        "of", "and", "or", "not", "no", "this", "that", "with", "from",
        "—", "-", "–", ",", ".", ":", ";",
        # Delivery 설명 메타어: 자기 지시적 표현 ("this block is...", "the way you'd...")
        "block", "way", "you", "your", "it", "its", "as", "by", "be",
        "like", "have", "do", "just", "very", "so", "but", "if", "into",
        "through", "then", "when", "where", "how", "here", "there",
        "what", "which", "who", "they", "them", "their", "we", "our",
        "he", "she", "him", "her", "up", "out", "about", "before",
        "after", "more", "some", "any", "each", "every", "one", "two",
        "first", "last", "next", "same", "all", "both", "few", "most",
    }
    words = re.findall(r'[a-zA-Z]+', text.lower())
    return {w for w in words if w not in stopwords and len(w) > 1}


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """두 집합의 Jaccard 유사도 계산."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def extract_bigrams(text: str) -> list[str]:
    """텍스트에서 2-gram 추출."""
    words = re.findall(r'[a-zA-Z]+', text.lower())
    return [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]


def check_similar_deliveries(entries: list[dict], threshold: float) -> list[dict]:
    """Anti-Pattern #1: 유사한 Delivery 설명 쌍 검출."""
    violations = []
    for a, b in combinations(entries, 2):
        tokens_a = tokenize(a["delivery"])
        tokens_b = tokenize(b["delivery"])
        sim = jaccard_similarity(tokens_a, tokens_b)
        if sim >= threshold:
            violations.append({
                "type": "similar_delivery",
                "anti_pattern": "#1",
                "block_a": a["block_id"],
                "block_b": b["block_id"],
                "similarity": round(sim, 3),
                "delivery_a": a["delivery"][:80],
                "delivery_b": b["delivery"][:80],
                "suggestion": f"Revise one Delivery description to reduce word overlap below {int(threshold*100)}%",
            })
    return violations


def check_repeated_bigrams(entries: list[dict], max_repeats: int = 3) -> list[dict]:
    """Anti-Pattern #2: 같은 2-gram이 3+ Delivery에 등장."""
    violations = []
    # 각 Delivery에서 2-gram 추출, 어떤 블록에서 나왔는지 추적
    bigram_sources: dict[str, list[str]] = {}
    for entry in entries:
        bigrams = set(extract_bigrams(entry["delivery"]))
        for bg in bigrams:
            bigram_sources.setdefault(bg, []).append(entry["block_id"])

    for bigram, blocks in bigram_sources.items():
        if len(blocks) >= max_repeats:
            violations.append({
                "type": "repeated_bigram",
                "anti_pattern": "#2",
                "bigram": bigram,
                "count": len(blocks),
                "blocks": blocks,
                "suggestion": f"The phrase '{bigram}' appears in {len(blocks)} Delivery descriptions. "
                              f"Revise to reduce below {max_repeats}.",
            })

    return violations


def check_consecutive_archetypes(entries: list[dict], max_consecutive: int = 3) -> list[dict]:
    """Anti-Pattern #4: 같은 아키타입 3+ 연속."""
    violations = []
    # 스크립트 순서대로 아키타입 시퀀스 검사
    sequence = [(e["block_id"], e["archetype_code"]) for e in entries if e["archetype_code"]]

    if len(sequence) < max_consecutive:
        return violations

    consecutive_count = 1
    for i in range(1, len(sequence)):
        if sequence[i][1] == sequence[i-1][1]:
            consecutive_count += 1
            if consecutive_count >= max_consecutive:
                # 연속 블록 범위 계산
                start_idx = i - consecutive_count + 1
                consecutive_blocks = [sequence[j][0] for j in range(start_idx, i + 1)]
                violations.append({
                    "type": "consecutive_archetype",
                    "anti_pattern": "#4",
                    "archetype": sequence[i][1],
                    "count": consecutive_count,
                    "blocks": consecutive_blocks,
                    "suggestion": f"Archetype {sequence[i][1]} appears {consecutive_count} times "
                                  f"consecutively. Replace at least one with a different archetype.",
                })
        else:
            consecutive_count = 1

    return violations


def get_pacing_profiles_from_script() -> dict[str, str]:
    """script_narration.json에서 블록별 pacing_profile을 가져오기."""
    narration_path = os.path.join(TMP_DIR, "script_narration.json")
    if not os.path.exists(narration_path):
        return {}

    with open(narration_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    profiles = {}
    for scene in data.get("scenes", []):
        for block in scene.get("blocks", []):
            bid = block.get("block_id", "")
            # pacing_profile 없으면 standard로 간주 (SKILL.md 규칙)
            profiles[bid] = block.get("pacing_profile", "standard")
    return profiles


def check_pacing_profile_compliance(
    entries: list[dict],
    pacing_profiles: dict[str, str],
) -> list[dict]:
    """pacing_profile 준수 검사.

    breathe 프로필 블록에서 [extremely fast] 태그 사용 시 위반으로 플래그.
    - breathe: 여유 있는 배달 의도 -> [extremely fast] 부적합
    - dense 블록에서 [speaking slowly]만 사용하는 것도 검사 (경고 수준)
    """
    violations = []
    # breathe 블록에서 금지되는 태그
    breathe_forbidden = {"[extremely fast]"}

    for entry in entries:
        bid = entry["block_id"]
        profile = pacing_profiles.get(bid, "standard")

        if profile == "breathe":
            # breathe 블록에서 금지 태그 존재 여부 확인
            used_forbidden = [
                tag for tag in entry.get("all_brackets", [])
                if tag in breathe_forbidden
            ]
            if used_forbidden:
                violations.append({
                    "type": "pacing_profile_violation",
                    "anti_pattern": "#5",
                    "block_id": bid,
                    "pacing_profile": profile,
                    "forbidden_tags": used_forbidden,
                    "suggestion": (
                        f"Block '{bid}' has pacing_profile=breathe but uses "
                        f"{', '.join(used_forbidden)}. breathe blocks should use "
                        f"spacious delivery (e.g. [speaking slowly], [long pause]). "
                        f"Replace or remove the fast tag."
                    ),
                })

    return violations


def check_lineup_equalizer(entries: list[dict]) -> list[dict]:
    """Lineup Equalizer 검사 (pure-prose 아키텍처 대응).

    rating_overview_lineup / verdict_use_case_picks 블록에서
    DIRECTOR'S NOTES Delivery 텍스트에 명시적 equalizer 지시가 있는지 확인.

    이전 로직은 TRANSCRIPT의 [short pause] 브래킷을 카운트했으나,
    현재 아키텍처는 TRANSCRIPT에 브래킷을 전면 금지(zero-bracket)하므로
    Delivery 텍스트 키워드 검사로 전환한다.

    equalizer 키워드 중 하나라도 포함되어 있으면 PASS.
    없으면 descending list intonation 위험으로 위반 처리.
    """
    violations = []
    # 명시적 equalizer 지시로 인정되는 키워드 (소문자)
    # 에이전트가 Delivery에 이 표현 중 하나를 사용했어야 함
    EQUALIZER_KEYWORDS = [
        "equal", "identical", "equalizer", "same weight",
        "same rhythm", "equalize", "same vocal", "same energy",
        "same emphasis", "same warmth", "same register",
    ]
    # Lineup Equalizer 적용 대상 블록 ID
    lineup_block_ids = {"rating_overview_lineup", "verdict_use_case_picks"}

    for entry in entries:
        bid = entry["block_id"]
        if bid not in lineup_block_ids:
            continue

        # Delivery 전체 텍스트 (소문자)에서 equalizer 키워드 탐색
        delivery_text = entry.get("delivery", "").lower()
        has_equalizer = any(kw in delivery_text for kw in EQUALIZER_KEYWORDS)

        if not has_equalizer:
            violations.append({
                "type": "lineup_equalizer_violation",
                "anti_pattern": "#6",
                "block_id": bid,
                "suggestion": (
                    f"Block '{bid}' is a lineup block but DIRECTOR'S NOTES Delivery "
                    f"does not contain explicit equalizer direction "
                    f"(e.g., 'identical vocal weight', 'Lineup Equalizer', 'same rhythm'). "
                    f"Add explicit equal-weight direction to prevent descending list intonation."
                ),
            })

    return violations


# Director's Notes Only 패러다임: TRANSCRIPT에 태그 사용 금지
# 모든 디렉팅(페이싱, 호흡, 속도 변화, 정적 등)은 DIRECTOR'S NOTES에 자연어 산문으로 표현
# TRANSCRIPT은 순수 나레이션 텍스트만 포함 -- 브래킷, 태그, 마크업 일체 금지
APPROVED_TAGS: set[str] = set()  # 빈 집합: 어떤 태그든 위반

# Block-Type Map에서 파생된 블록 ID → 허용 아키타입 매핑
# block_id 패턴을 기반으로 해당 블록이 사용할 수 있는 아키타입 코드를 정의
BLOCK_ARCHETYPE_MAP = {
    "hook_contradiction": {"A", "B"},
    "hook_curiosity_loop": {"D", "E"},
    "rating_overview_lineup": {"F"},
    "rating_overview_gap": {"B", "C"},
    # theme comparison: leader/laggard/context 패턴
    "_leader": {"F", "D"},
    "_laggard": {"C", "D"},
    "_context": {"E"},
    "standout_": {"F", "E", "D"},
    # verdict
    "verdict_category_judgment": {"G"},
    "verdict_use_case_picks": {"G"},
    "verdict_outro": {"F"},
}


def _get_allowed_archetypes(block_id: str) -> set[str] | None:
    """블록 ID로부터 허용된 아키타입 코드 집합을 반환.

    정확히 일치하는 규칙 우선, 없으면 접미사/접두사 패턴 매칭.
    매칭 실패 시 None 반환 (검사 대상 아님).
    """
    # 정확한 매칭 우선
    if block_id in BLOCK_ARCHETYPE_MAP:
        return BLOCK_ARCHETYPE_MAP[block_id]
    # 접미사 패턴 매칭 (theme comparison)
    for pattern, allowed in BLOCK_ARCHETYPE_MAP.items():
        if pattern.startswith("_") and block_id.endswith(pattern):
            return allowed
        if pattern.endswith("_") and block_id.startswith(pattern):
            return allowed
    return None


def check_tag_whitelist(entries: list[dict]) -> list[dict]:
    """Anti-Pattern #3: TRANSCRIPT 내 태그/브래킷 사용 검사.

    TRANSCRIPT에 어떤 bracket 태그든 존재하면 위반.
    모든 디렉팅은 DIRECTOR'S NOTES에 자연어 산문으로 표현해야 함.
    """
    violations = []
    for entry in entries:
        bid = entry["block_id"]
        all_tags = entry.get("all_brackets", [])
        for tag in all_tags:
            violations.append({
                "type": "tag_in_transcript",
                "anti_pattern": "#3",
                "block_id": bid,
                "tag": tag,
                "suggestion": (
                    f"Block '{bid}' has tag '{tag}' in TRANSCRIPT. "
                    f"TRANSCRIPT must be clean text only -- zero brackets. "
                    f"Move this direction to DIRECTOR'S NOTES as prose."
                ),
            })
    return violations


def check_archetype_map(entries: list[dict]) -> list[dict]:
    """Anti-Pattern #8: Archetype-BlockType Map 일치 검사.

    선언된 아키타입 코드가 Block-Type Map에서 해당 블록 유형에
    허용된 코드와 일치하는지 확인.
    """
    violations = []
    for entry in entries:
        bid = entry["block_id"]
        declared = entry.get("archetype_code", "")
        if not declared:
            continue  # 선언 없으면 #8 검사 대상 아님 (누락 경고는 별도)
        allowed = _get_allowed_archetypes(bid)
        if allowed is None:
            continue  # 매핑 테이블에 정의 안 된 블록 유형
        if declared not in allowed:
            violations.append({
                "type": "archetype_map_mismatch",
                "anti_pattern": "#8",
                "block_id": bid,
                "declared": declared,
                "allowed": sorted(allowed),
                "suggestion": (
                    f"Block '{bid}' declares Archetype {declared} "
                    f"but Block-Type Map allows {sorted(allowed)}. "
                    f"Revise the Archetype declaration."
                ),
            })
    return violations


def get_block_order_from_script() -> dict[str, int]:
    """script_narration.json에서 블록 순서를 가져오기."""
    narration_path = os.path.join(TMP_DIR, "script_narration.json")
    if not os.path.exists(narration_path):
        return {}

    with open(narration_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    block_order = {}
    idx = 0
    for scene in data.get("scenes", []):
        for block in scene.get("blocks", []):
            block_order[block["block_id"]] = idx
            idx += 1
    return block_order


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: Opening Bracket Audit - cross-scene anti-pattern detection"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.5,
        help="Jaccard similarity threshold for delivery comparison (default: 0.5)"
    )
    parser.add_argument(
        "--output", default=os.path.join(TMP_DIR, "bracket_audit_report.json"),
        help="Output path (default: tmp/bracket_audit_report.json)"
    )
    args = parser.parse_args()

    # 모든 프롬프트 파일 수집
    prompt_files = sorted(glob.glob(os.path.join(TMP_DIR, "tts_prompt_*.txt")))

    if not prompt_files:
        print("[audit] ERROR: No tts_prompt_*.txt files found in tmp/.", file=sys.stderr)
        sys.exit(1)

    print(f"[audit] Found {len(prompt_files)} prompt files.", file=sys.stderr)

    # 블록 순서 기준으로 정렬
    block_order = get_block_order_from_script()
    if block_order:
        prompt_files.sort(
            key=lambda p: block_order.get(
                os.path.basename(p).replace("tts_prompt_", "").replace(".txt", ""),
                999
            )
        )

    # 각 파일에서 데이터 추출
    entries = []
    missing_archetype = []
    for pf in prompt_files:
        entry = extract_delivery_and_bracket(pf)
        entries.append(entry)
        # Archetype 선언 누락 경고 수집
        if not entry["archetype_code"]:
            missing_archetype.append(entry["block_id"])
        print(
            f"  [{entry['block_id']}] arch={entry['archetype_code'] or '?'} "
            f"delivery={entry['delivery'][:50]}...",
            file=sys.stderr,
        )

    if missing_archetype:
        print(
            f"\n[audit] WARNING: {len(missing_archetype)} blocks missing 'Archetype:' declaration: "
            f"{missing_archetype}\n"
            f"  Add '- Archetype: [A-G]' to DIRECTOR'S NOTES. "
            f"Consecutive archetype checks (#4) may be inaccurate.\n",
            file=sys.stderr,
        )

    # pacing_profile 데이터 로드 (script_narration.json 기반)
    pacing_profiles = get_pacing_profiles_from_script()
    if pacing_profiles:
        print(f"[audit] Loaded pacing profiles for {len(pacing_profiles)} blocks.", file=sys.stderr)
    else:
        print("[audit] WARNING: No pacing profiles found. Skipping pacing compliance check.", file=sys.stderr)

    # Anti-Pattern 검사
    violations = []
    violations.extend(check_similar_deliveries(entries, args.threshold))
    violations.extend(check_repeated_bigrams(entries))
    violations.extend(check_consecutive_archetypes(entries))
    # pacing_profile 준수 검사 (#5)
    if pacing_profiles:
        violations.extend(check_pacing_profile_compliance(entries, pacing_profiles))
    # Lineup Equalizer 검사 (#6)
    violations.extend(check_lineup_equalizer(entries))
    # 태그 화이트리스트 검사 (#7)
    violations.extend(check_tag_whitelist(entries))
    # Archetype-Map 일치 검사 (#8)
    violations.extend(check_archetype_map(entries))

    # 결과 구성
    status = "PASS" if not violations else "NEEDS_REVISION"
    report = {
        "violations": violations,
        "summary": {
            "total_blocks": len(entries),
            "violations_found": len(violations),
            "by_type": {
                "similar_delivery": sum(1 for v in violations if v["type"] == "similar_delivery"),
                "repeated_bigram": sum(1 for v in violations if v["type"] == "repeated_bigram"),
                "consecutive_archetype": sum(1 for v in violations if v["type"] == "consecutive_archetype"),
                "pacing_profile_violation": sum(1 for v in violations if v["type"] == "pacing_profile_violation"),
                "lineup_equalizer_violation": sum(1 for v in violations if v["type"] == "lineup_equalizer_violation"),
                "invalid_tag": sum(1 for v in violations if v["type"] == "invalid_tag"),
                "archetype_map_mismatch": sum(1 for v in violations if v["type"] == "archetype_map_mismatch"),
            },
            "status": status,
        },
    }

    # 저장
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 결과 출력
    print(json.dumps(report["summary"]))

    if violations:
        print(f"\n[audit] {len(violations)} violations found:", file=sys.stderr)
        for v in violations:
            print(f"  [{v['anti_pattern']}] {v['type']}: {v.get('suggestion', '')[:80]}", file=sys.stderr)
    else:
        print(f"\n[audit] All {len(entries)} blocks PASSED. No anti-pattern violations.", file=sys.stderr)


if __name__ == "__main__":
    main()
