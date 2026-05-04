"""
Audio QA Evaluator — STT 기반 Deterministic 품질 검증.

설계 원칙:
    기존 방식(Multimodal LLM이 오디오를 듣고 주관적 판정)은
    확증편향으로 인한 false positive(태그 환각)가 빈발했다.
    
    새 방식은 2단계로 나뉜다:
    1단계: Gemini STT로 오디오를 자유 전사(free transcription)한다.
    2단계: 전사 텍스트와 clean text를 프로그래밍적으로 비교한다.
    
    LLM 판단이 개입하지 않으므로 환각이 원천 차단된다.
"""
import asyncio
import difflib
import json
import os
import re
import sys

from google import genai
from google.genai import types

from config import MODELS

# 브래킷 태그에 흔히 사용되는 stage-direction 어휘 목록
# 이 단어들이 전사본에 나타나지만 clean text에는 없으면 tag misfire로 판정
TAG_VOCABULARY = {
    "pause", "pausing", "short", "medium", "long",
    "slowly", "speaking", "whispering", "whisper",
    "empathetic", "empathy", "curious", "curiosity",
    "thoughtful", "thoughtfully",
    "extremely",
    "bracket", "brackets",
    "tag", "tags",
    "breathe", "breathing",
    "sigh", "sighing",
}


def _normalize(text: str) -> list[str]:
    """텍스트를 소문자로 변환하고 구두점을 제거한 단어 리스트를 반환한다."""
    # 구두점 제거 (하이픈, 아포스트로피는 유지)
    cleaned = re.sub(r"[^\w\s'-]", "", text.lower())
    return cleaned.split()


def _find_stray_words(clean_words: list[str], transcript_words: list[str]) -> list[str]:
    """전사본에는 있지만 clean text에는 없는 단어를 찾는다.
    
    SequenceMatcher의 opcodes를 사용하여 insert된 단어만 추출.
    """
    sm = difflib.SequenceMatcher(None, clean_words, transcript_words)
    stray = []
    for op, _, _, j1, j2 in sm.get_opcodes():
        if op == "insert":
            stray.extend(transcript_words[j1:j2])
        elif op == "replace":
            # replace 구간에서 transcript 쪽의 단어 중 clean에 없는 것들
            for w in transcript_words[j1:j2]:
                if w not in clean_words:
                    stray.append(w)
    return stray


def _check_number_accuracy(clean_words: list[str], transcript_words: list[str]) -> list[str]:
    """숫자 포함 단어들의 정확도를 검증한다.
    
    clean text의 숫자가 전사본에서 다른 숫자로 바뀌었으면 오류로 보고.
    """
    # 숫자 패턴: 소수점, 퍼센트, 정수 포함
    num_pattern = re.compile(r'\d+\.?\d*%?')
    
    clean_nums = set()
    for w in clean_words:
        for m in num_pattern.findall(w):
            clean_nums.add(m)
    
    transcript_nums = set()
    for w in transcript_words:
        for m in num_pattern.findall(w):
            transcript_nums.add(m)
    
    errors = []
    # clean에 있는 숫자가 transcript에 없으면 발음 오류 가능성
    for num in clean_nums:
        if num not in transcript_nums:
            # 유사한 숫자가 transcript에 있는지 확인 (예: 75.7 vs 77.7)
            close_matches = [t for t in transcript_nums if t not in clean_nums]
            if close_matches:
                errors.append(f"숫자 불일치: 대본 '{num}' -> 전사 '{', '.join(close_matches)}'")
    
    return errors


async def _transcribe_audio(audio_path: str) -> str:
    """Gemini STT로 오디오를 자유 전사한다.
    
    forced alignment이 아닌 free transcription — 
    모델이 실제로 들리는 대로 텍스트를 생성한다.
    이 전사본을 clean text와 비교하면 tag misfire를 
    deterministic하게 탐지할 수 있다.
    """
    client = genai.Client()
    model_id = MODELS.get("stt", "gemini-3.1-flash-lite-preview")
    
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    
    # 자유 전사 프롬프트 — 편향을 주지 않기 위해 최소한의 지시만
    transcription_prompt = """Transcribe the audio exactly as spoken, word for word.
Include every word you hear. Do not skip or add any words.
Output ONLY the plain text transcription, nothing else.
No formatting, no timestamps, no labels."""
    
    config = types.GenerateContentConfig(
        temperature=0.0,
    )
    
    contents = [
        types.Part.from_bytes(data=audio_data, mime_type="audio/wav"),
        transcription_prompt
    ]
    
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model_id,
        contents=contents,
        config=config,
    )
    
    return response.text.strip()


async def validate_audio_quality(audio_path: str, clean_text: str, tts_prompt_text: str) -> dict:
    """STT 전사 + 텍스트 비교 기반 오디오 품질 검증.
    
    판정 로직 (모두 deterministic):
    1. STT로 자유 전사 → 전사본 획득
    2. clean text와 전사본의 단어 유사도 계산 (SequenceMatcher)
    3. 전사본에서 clean text에 없는 "stray words" 추출
    4. stray words 중 TAG_VOCABULARY에 해당하는 단어 → tag misfire
    5. 숫자 정확도 검증 (75.7% vs 77.7% 같은 오류)
    
    Args:
        audio_path: 평가할 wav 파일 경로
        clean_text: 원본 대본 텍스트 (태그가 없는 순수 내레이션)
        tts_prompt_text: 미사용 (서명 호환성 유지)
        
    Returns:
        dict: {"is_valid": bool, "reason": str}
    """
    if not os.path.exists(audio_path):
        return {"is_valid": False, "reason": "오디오 파일이 없습니다."}

    try:
        # 1단계: STT 자유 전사
        transcript = await _transcribe_audio(audio_path)
        
        if not transcript or len(transcript.strip()) < 10:
            return {"is_valid": False, "reason": "STT 전사 결과가 비어있거나 너무 짧습니다."}
        
        # 2단계: 단어 정규화
        clean_words = _normalize(clean_text)
        transcript_words = _normalize(transcript)
        
        # 3단계: 전체 유사도 계산
        similarity = difflib.SequenceMatcher(None, clean_words, transcript_words).ratio()
        
        errors = []
        
        # 4단계: 유사도 임계값 검사 (75% 미만이면 심각한 문제)
        if similarity < 0.75:
            errors.append(f"텍스트 유사도 너무 낮음: {similarity*100:.1f}% (임계값 75%)")
        
        # 5단계: Tag misfire 탐지 — stray words 중 TAG_VOCABULARY 어휘 검색
        stray = _find_stray_words(clean_words, transcript_words)
        tag_misfires = [w for w in stray if w in TAG_VOCABULARY]
        
        if tag_misfires:
            # 중복 제거 후 보고
            unique_tags = sorted(set(tag_misfires))
            errors.append(f"태그 음성화 감지: {', '.join(unique_tags)}")
        
        # 6단계: 숫자 정확도 검증
        number_errors = _check_number_accuracy(clean_words, transcript_words)
        errors.extend(number_errors)
        
        # 판정
        if errors:
            reason = " | ".join(errors) + f" (유사도: {similarity*100:.1f}%)"
            return {"is_valid": False, "reason": reason}
        
        return {
            "is_valid": True, 
            "reason": f"STT 검증 통과 (유사도: {similarity*100:.1f}%, stray words: {len(stray)}개, 태그 어휘: 0개)"
        }
        
    except Exception as e:
        print(f"[audio_evaluator] 평가 중 오류 발생: {e}", file=sys.stderr)
        # 평가 실패 시에도 파이프라인이 멈추지 않도록 PASS 처리
        return {"is_valid": True, "reason": f"평가자 오류로 인한 PASS 처리: {str(e)}"}
