"""
prompt_utils.py -- tts_prompt 파일 파싱 공통 유틸리티.

audit_opening_brackets.py, scene_handoff_manager.py 등에서 공유.
아키타입 코드는 프롬프트 파일의 `Archetype:` 선언값을 직접 읽는다.
키워드 기반 역추론은 하지 않는다.

변경 이력:
  - Delivery 추출: 단일 라인 → 멀티라인 (다음 필드 헤더 직전까지 전체 캡처)
    → Jaccard/bigram 유사도 검사 정확도 향상
  - last_sentence: 마지막 나레이션 라인 전체 → 마지막 문장(sentence) 단위
    → 핸드오프 컨텍스트 토큰 낭비 방지
"""
import os
import re


# 유효한 아키타입 코드 목록
VALID_ARCHETYPES = {"A", "B", "C", "D", "E", "F", "G"}


def extract_prompt_info(prompt_path: str) -> dict:
    """tts_prompt_{block_id}.txt에서 핵심 정보를 추출.

    Archetype 코드는 DIRECTOR'S NOTES의 `- Archetype:` 선언값을 직접 파싱.
    에이전트가 명시적으로 선언한 값을 그대로 사용하므로
    키워드 기반 역추론이 필요 없다.

    Returns:
        dict: block_id, delivery, archetype_code, first_bracket,
              last_sentence, all_brackets, transcript_lines
    """
    block_id = os.path.basename(prompt_path).replace("tts_prompt_", "").replace(".txt", "")

    with open(prompt_path, "r", encoding="utf-8") as f:
        content = f.read()

    result = {
        "block_id": block_id,
        "delivery": "",
        "archetype_code": "",
        "first_bracket": "",
        "last_sentence": "",
        "all_brackets": [],
        "transcript_lines": [],
    }

    # Archetype 선언값 파싱 (최우선)
    arch_match = re.search(r"-\s*Archetype:\s*([A-G])\b", content)
    if arch_match:
        result["archetype_code"] = arch_match.group(1)

    # Delivery 멀티라인 추출
    # 다음 필드 헤더(- Context:, - BGM/bgm_mood, - Visual Read, #### TRANSCRIPT)
    # 직전까지 전체를 캡처한다. 단일 라인만 읽으면 실질적인 directing 내용의
    # 대부분을 놓쳐 Jaccard/bigram 유사도 검사가 부정확해진다.
    # 참고: bgm_mood 패턴 추가 — 에이전트가 `- bgm_mood alignment:` 형태로
    #       작성할 경우에도 Delivery 종료 경계로 인식하도록 확장.
    delivery_match = re.search(
        r"-\s*Delivery:\s*(.*?)(?=\n\s*-\s+(?:Context|BGM|bgm_mood|Visual)|#### TRANSCRIPT|\Z)",
        content,
        re.DOTALL,
    )
    if delivery_match:
        # 멀티라인 → 단일 공백으로 정규화 (비교 용이)
        result["delivery"] = " ".join(delivery_match.group(1).split())

    # TRANSCRIPT 섹션 분리
    transcript_section = (
        content.split("#### TRANSCRIPT")[-1]
        if "#### TRANSCRIPT" in content
        else content
    )

    # 첫 bracket 추출
    bracket_match = re.search(r"\[([^\]]+)\]", transcript_section)
    if bracket_match:
        result["first_bracket"] = f"[{bracket_match.group(1)}]"

    # TRANSCRIPT 내 모든 bracket 태그 수집 + 나레이션 텍스트 라인 분리
    narration_lines = []
    for line in transcript_section.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # bracket 태그 수집
        brackets_in_line = re.findall(r"\[([^\]]+)\]", line)
        if brackets_in_line:
            result["all_brackets"].extend(f"[{b}]" for b in brackets_in_line)
        # bracket 제거 후 텍스트만 남으면 나레이션 라인으로 수집
        clean = re.sub(r"\[[^\]]*\]\s*", "", line).strip()
        if clean:
            result["transcript_lines"].append(clean)
            narration_lines.append(clean)

    # 마지막 나레이션 문장 (문장 단위 분리)
    # 이전: narration_lines[-1] → 단락 전체가 한 줄이면 수백 단어가 담겨
    #        핸드오프 컨텍스트 필드 last_sentence 토큰 낭비 발생
    # 현재: TRANSCRIPT 전체 텍스트에서 마지막 문장(문장부호 기준)만 추출
    if narration_lines:
        all_transcript_text = " ".join(narration_lines)
        # 문장 경계: 마침표/느낌표/물음표 + 공백으로 분리
        sentences = re.split(r'(?<=[.!?])\s+', all_transcript_text.strip())
        result["last_sentence"] = sentences[-1].strip() if sentences else ""

    return result
