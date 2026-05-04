"""
TTS Prompt Quality Audit — TTS 출력 품질에 직접 영향을 주는 항목만 검사.

모든 tts_prompt_*.txt 파일을 스캔하여
크로스 씬 Anti-Pattern 위반을 검사한다.

검사 항목:
  CHECK 1: 동일한 Style 설명 (Jaccard similarity > 50%, 근접 4블록 이내)
  CHECK 3: TRANSCRIPT delivery marker compliance (persona-inappropriate tags) [§3]
  CHECK 5: pacing_profile 준수 (breathe 블록에서 fast 태그 부적합) [§2]
  CHECK 6: Synthesis preamble 존재 여부 [§2]


Usage:
    python tools/audit_prompt_quality.py
    python tools/audit_prompt_quality.py --threshold 0.5

출력: tmp/prompt_audit_report.json
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
    """tts_prompt 파일에서 Delivery 설명, bracket 목록을 추출.

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


def check_similar_deliveries(
    entries: list[dict],
    threshold: float,
    block_order: dict[str, int] | None = None,
    proximity: int = 4,
) -> list[dict]:
    """Anti-Pattern #1: 유사한 Delivery 설명 쌍 검출.

    근접 검사: block_order가 있으면 proximity 블록 이내의 쌍만 비교.
    시청자 습관화(habituation)는 근접 효과이므로 멀리 떨어진 블록은 면제.
    block_order가 없으면 전체 비교 (레거시 호환).
    """
    violations = []
    for a, b in combinations(entries, 2):
        # 근접 필터: block_order가 있으면 proximity 이내만 비교
        if block_order:
            pos_a = block_order.get(a["block_id"], -1)
            pos_b = block_order.get(b["block_id"], -1)
            if pos_a >= 0 and pos_b >= 0 and abs(pos_a - pos_b) > proximity:
                continue
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
                "suggestion": f"Revise one Delivery description to reduce Jaccard similarity below {int(threshold*100)}%",
            })
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





# §3 TRANSCRIPT Delivery Layer: Permitted delivery markers (Google-official audio tags)
# Core + Situational tags from the Consumer Navigator persona-safe palette.
# See SKILL.md §3 Audio Tag Palette for the full project-specific catalog.
PERMITTED_AUDIO_TAGS = {
    # Core (use freely)
    "[sighs]", "[serious]", "[curious]", "[whispers]", "[tired]",
    # Situational (use with care)
    "[bored]", "[reluctantly]", "[slow]", "[gasp]",
}
# Persona-inappropriate tags: engine supports them but Consumer Navigator persona doesn't.
# Flagged as WARNING (not error) — they don't break the engine, just the persona.
PERSONA_INAPPROPRIATE_TAGS = {
    "[excitedly]", "[panicked]", "[shouting]", "[amazed]",
    "[giggles]", "[laughs]", "[mischievously]", "[trembling]",
}

# Common all-caps words that are NOT emphasis markers
CAPS_EXCEPTIONS = {
    "I", "ANC", "AirPods", "BSR", "USB", "IP", "EQ", "AAC", "LDAC",
    "NOT", "AND", "OR", "THE", "A",  # common short words sometimes caps in titles
}





def check_tag_whitelist(entries: list[dict]) -> list[dict]:
    """TRANSCRIPT delivery marker compliance.

    The TTS engine accepts any natural language tag — creative/descriptive tags
    are encouraged per the Gemini TTS Prompting Guide. Only persona-inappropriate
    tags (those that break the Consumer Navigator character) are flagged as warnings.
    """
    violations = []
    for entry in entries:
        bid = entry["block_id"]
        all_tags = entry.get("all_brackets", [])
        for tag in all_tags:
            tag_lower = tag.lower()
            if tag_lower in {t.lower() for t in PERMITTED_AUDIO_TAGS}:
                continue  # Core tag — always OK
            elif tag_lower in {t.lower() for t in PERSONA_INAPPROPRIATE_TAGS}:
                violations.append({
                    "type": "persona_inappropriate_tag",
                    "anti_pattern": "#3",
                    "severity": "warning",
                    "block_id": bid,
                    "tag": tag,
                    "suggestion": (
                        f"Block '{bid}' uses persona-inappropriate tag '{tag}'. "
                        f"Consumer Navigator persona doesn't use this emotion. "
                        f"Consider replacing with a core tag or a descriptive alternative."
                    ),
                })
            # Creative/descriptive tags (e.g. [like reading bad news]) — pass silently.
            # The TTS engine accepts any natural language description as a tag.
    return violations


PREAMBLE_PREFIX = "Read the following transcript"


def check_synthesis_preamble(entries: list[dict], prompt_files: list[str]) -> list[dict]:
    """CHECK 6: 각 프롬프트 파일이 synthesis preamble으로 시작하는지 확인.

    SKILL.md §2: Preamble MUST be the first content in every prompt file.
    """
    violations = []
    for pf in prompt_files:
        bid = os.path.basename(pf).replace("tts_prompt_", "").replace(".txt", "")
        with open(pf, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        if not first_line.startswith(PREAMBLE_PREFIX):
            violations.append({
                "type": "missing_preamble",
                "anti_pattern": "#6",
                "block_id": bid,
                "first_line": first_line[:60],
                "suggestion": (
                    f"Block '{bid}' is missing synthesis preamble. "
                    f"First line must start with '{PREAMBLE_PREFIX}...'"
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
        description="ReviewLens: TTS Prompt Quality Audit - cross-scene anti-pattern detection"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.5,
        help="Jaccard similarity threshold for delivery comparison (default: 0.5)"
    )
    parser.add_argument(
        "--output", default=os.path.join(TMP_DIR, "prompt_audit_report.json"),
        help="Output path (default: tmp/prompt_audit_report.json)"
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
    for pf in prompt_files:
        entry = extract_delivery_and_bracket(pf)
        entries.append(entry)
        print(
            f"  [{entry['block_id']}] delivery={entry['delivery'][:50]}...",
            file=sys.stderr,
        )

    # pacing_profile 데이터 로드 (script_narration.json 기반)
    pacing_profiles = get_pacing_profiles_from_script()
    if pacing_profiles:
        print(f"[audit] Loaded pacing profiles for {len(pacing_profiles)} blocks.", file=sys.stderr)
    else:
        print("[audit] WARNING: No pacing profiles found. Skipping pacing compliance check.", file=sys.stderr)

    # Anti-Pattern 검사 (TTS 출력 품질에 직접 영향을 주는 항목만)
    violations = []
    violations.extend(check_similar_deliveries(entries, args.threshold, block_order))
    # pacing_profile 준수 검사 (#5)
    if pacing_profiles:
        violations.extend(check_pacing_profile_compliance(entries, pacing_profiles))
    # Delivery marker compliance (persona filter only — creative tags pass)
    violations.extend(check_tag_whitelist(entries))
    # Synthesis preamble 존재 여부 (#6)
    violations.extend(check_synthesis_preamble(entries, prompt_files))

    # 결과 구성
    status = "PASS" if not violations else "NEEDS_REVISION"
    report = {
        "violations": violations,
        "summary": {
            "total_blocks": len(entries),
            "violations_found": len(violations),
            "by_type": {
                "similar_delivery": sum(1 for v in violations if v["type"] == "similar_delivery"),
                "pacing_profile_violation": sum(1 for v in violations if v["type"] == "pacing_profile_violation"),
                "tag_violation": sum(1 for v in violations if v["type"] in {
                    "persona_inappropriate_tag"
                }),
                "missing_preamble": sum(1 for v in violations if v["type"] == "missing_preamble"),
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
