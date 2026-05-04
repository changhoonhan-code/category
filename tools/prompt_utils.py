"""
prompt_utils.py -- tts_prompt 파일 파싱 공통 유틸리티.

audit tool (audit_prompt_quality.py), scene_handoff_manager.py 등에서 공유.

변경 이력:
  - Delivery 추출: 단일 라인 → 멀티라인 (다음 필드 헤더 직전까지 전체 캡처)
    → Jaccard/bigram 유사도 검사 정확도 향상
  - last_sentence: 마지막 나레이션 라인 전체 → 마지막 문장(sentence) 단위
    → 핸드오프 컨텍스트 토큰 낭비 방지
  - Archetype 필드 삭제: TTS 엔진에 영향 없는 메타데이터. Jaccard 검사가 톤 다양성 커버.
"""
import os
import re





def extract_prompt_info(prompt_path: str) -> dict:
    """tts_prompt_{block_id}.txt에서 핵심 정보를 추출.

    Returns:
        dict: block_id, delivery, first_bracket,
              last_sentence, all_brackets, transcript_lines
    """
    block_id = os.path.basename(prompt_path).replace("tts_prompt_", "").replace(".txt", "")

    with open(prompt_path, "r", encoding="utf-8") as f:
        content = f.read()

    result = {
        "block_id": block_id,
        "delivery": "",
        "first_bracket": "",
        "last_sentence": "",
        "all_brackets": [],
        "transcript_lines": [],
    }



    # Delivery 멀티라인 추출
    # 다음 필드 헤더(- FieldName: 패턴) 또는 ## Transcript: / #### TRANSCRIPT 직전까지 전체를 캡처.
    # 에이전트가 커스텀 필드명(Emotional arc, Key moments 등)을 사용할 수 있으므로
    # 특정 필드명을 하드코딩하지 않고, "- 대문자로 시작하는 단어(들):" 패턴으로 일반화.
    delivery_match = re.search(
        r"-\s*(?:Style|Delivery):\s*(.*?)(?=\n\s*-\s+[A-Z][^:]*:|## (?:Scene|Sample Context|Transcript):|#### TRANSCRIPT|\Z)",
        content,
        re.DOTALL,
    )
    if delivery_match:
        # 멀티라인 → 단일 공백으로 정규화 (비교 용이)
        result["delivery"] = " ".join(delivery_match.group(1).split())

    # TRANSCRIPT 섹션 분리 (new format: "## Transcript:" / legacy: "#### TRANSCRIPT")
    if "## Transcript:" in content:
        transcript_section = content.split("## Transcript:")[-1]
    elif "#### TRANSCRIPT" in content:
        transcript_section = content.split("#### TRANSCRIPT")[-1]
    else:
        transcript_section = content

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
        # Full transcript text for prosody cap checks (§5)
        result["transcript"] = all_transcript_text

    return result
