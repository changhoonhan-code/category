"""
Word Alignment CLI Tool — Gemini STT로 단어별 타임스탬프를 추출하는 도구.

Migrated from pipeline/agents/word_alignment.py + pipeline/skills/narration.py (STT part)
핵심 변경: SKILL.md 정규식 파싱 제거, STT 프롬프트 내장, 출력 검증 로직 추가.

사용법:
    python tools/word_align.py \
        --audio-dir    data/narration_audio/ \
        --manifest     data/narration_audio/manifest.json \
        --script       data/script_output.json \
        --output       data/word_timestamps.json \
        --updated-script data/final_script_with_narration.json \
        --model        gemini-3.1-flash-lite-preview
"""
import argparse
import asyncio
import difflib
import json
import mimetypes
import os
import sys
import time
from typing import Any, Dict, List

from google import genai

from config import MODELS, MAX_CONCURRENT, MAX_RETRIES, RETRY_BASE_DELAY


# ── 상수 ──────────────────────────────────────────────────────────────────────

DEFAULT_STT_MODEL = MODELS["stt"]
DURATION_PADDING_SEC = 0.5

# ── STT 프롬프트 (하드코딩) ───────────────────────────────────────────────────
# 기존 pipeline에서 사용하던 forced-alignment 프롬프트.
# 기계적 단어 정렬 작업이므로 맥락 의존성 없음 → 도구 내부에 고정.

STT_PROMPT_TEMPLATE = """\
You are an expert audio-to-text alignment assistant. 
Your task is to perform forced-alignment between the provided audio and the exact narration text below:

`{narration_text}`

[CRITICAL RULES]
1. VERBATIM ALIGNMENT: You must include every single word from the text above in the exact same order. Do NOT skip, summarize, or add words even if you hear slight differences in the audio.
2. TIMESTAMP PRECISION: Provide start and end times in seconds (3 decimal places). 
3. WORD TOKENIZATION: Treat each space-separated word as a token. Remove punctuation (commas, periods, etc.) from the "word" field value.
4. ENERGY-BASED: 'start' is the exact onset of vocal energy; 'end' is the offset.
5. NO HALLUCINATION: If a word is repeated or added in the audio but NOT in the text, IGNORE it in the output. If a word is in the text but silent in the audio, estimate its position based on context.

[OUTPUT FORMAT]
Respond ONLY with a valid JSON array of objects. No markdown, no pre-amble.
[
  {{"word": "word1", "start": 0.000, "end": 0.350}},
  ...
]
"""


# ── 블록 추출 ─────────────────────────────────────────────────────────────────

def extract_narration_blocks(script: Dict) -> List[Dict]:
    """스크립트 JSON에서 나레이션이 있는 블록을 추출한다.

    Returns:
        list of dict: block_id, narration, scene_idx, block_idx
    """
    blocks = []
    for si, scene in enumerate(script.get("scenes", [])):
        for bi, block in enumerate(scene.get("blocks", [])):
            narration = (block.get("narration") or "").strip()
            if narration:
                blocks.append({
                    "scene_idx": si,
                    "block_idx": bi,
                    "block_id": block.get("block_id", f"s{si}_b{bi}"),
                    "narration": narration,
                })
    return blocks


# ── STT 타임스탬프 추출 ──────────────────────────────────────────────────────

async def extract_word_timestamps(
    audio_path: str,
    narration_text: str,
    client: genai.Client,
    model: str = DEFAULT_STT_MODEL,
    temperature: float = 0.0,
) -> List[Dict[str, Any]]:
    """Gemini 멀티모달로 단어별 타임스탬프를 추출한다.

    WAV 파일과 알려진 나레이션 텍스트를 함께 전달하여
    자유 전사(transcription) 대신 forced alignment 방식으로 정렬.

    Returns:
        list of {"word": str, "start": float, "end": float}, 실패 시 빈 리스트
    """
    uploaded = None
    try:
        # 오디오 파일 업로드 (MIME 타입 동적 감지)
        mime_type = mimetypes.guess_type(audio_path)[0] or "audio/wav"
        uploaded = await asyncio.to_thread(
            client.files.upload,
            file=audio_path,
            config={"mime_type": mime_type},
        )

        # 프롬프트 조립
        prompt = STT_PROMPT_TEMPLATE.format(narration_text=narration_text)

        # Gemini 호출 (Temperature 설정 및 JSON 모드)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=[uploaded, prompt],
            config=genai.types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
            )
        )

        # 응답 파싱
        raw = response.text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)
        timestamps = [
            {
                "word": str(item["word"]),
                "start": float(round(float(item["start"]), 3)),
                "end": float(round(float(item["end"]), 3)),
            }
            for item in data
            if str(item.get("word", "")).strip()
        ]

        return timestamps

    except Exception as e:
        print(f"[word_align] WARNING: Gemini STT 실패 ({audio_path}): {e}", file=sys.stderr, flush=True)
        return []

    finally:
        # 서버 파일 정리
        if uploaded:
            try:
                await asyncio.to_thread(client.files.delete, name=uploaded.name)
            except Exception:
                pass


# ── 출력 검증 ─────────────────────────────────────────────────────────────────

def validate_timestamps(
    timestamps: List[Dict], narration_text: str, block_id: str,
    similarity_threshold: float = 0.90,
) -> List[str]:
    """타임스탬프 품질 검증. 경고 메시지 리스트를 반환한다."""
    warnings = []

    if not timestamps:
        warnings.append(f"[{block_id}] 타임스탬프가 비어있음")
        return warnings

    # 1. 단조증가(monotonic) 및 세부 수치 검증
    for i in range(len(timestamps)):
        ts = timestamps[i]
        start, end = ts["start"], ts["end"]
        duration = end - start

        # 너무 짧은 단어 (환각 의심)
        if duration < 0.05:
            warnings.append(f"[{block_id}] 너무 짧은 단어: '{ts['word']}' ({duration:.3f}s)")

        if i > 0:
            prev_end = timestamps[i - 1]["end"]
            # 겹침 확인
            if start < prev_end - 0.01:
                warnings.append(
                    f"[{block_id}] 비단조 타임스탬프: word[{i-1}] end={prev_end} > word[{i}] start={start}"
                )
            # 너무 큰 공백 확인 (환각 의심)
            gap = start - prev_end
            if gap > 2.0:
                 warnings.append(f"[{block_id}] 큰 공백 감지: {gap:.1f}s (환각 가능성)")

    # 2. 단어 유사도 및 개수 비교
    expected_words = narration_text.lower().split()
    actual_words = [ts["word"].lower() for ts in timestamps]
    
    # SequenceMatcher를 이용한 텍스트 유사도 검증
    similarity = difflib.SequenceMatcher(None, expected_words, actual_words).ratio()
    if similarity < similarity_threshold:
        warnings.append(
            f"[{block_id}] 낮은 텍스트 유사도: {similarity*100:.1f}% (임계값 {similarity_threshold*100:.0f}%)"
        )

    if abs(len(expected_words) - len(actual_words)) > max(3, int(len(expected_words) * 0.2)):
        warnings.append(
            f"[{block_id}] 단어 수 불일치: 예상 ~{len(expected_words)}개, 실제 {len(actual_words)}개"
        )

    # 3. 비정상 길이 검증 (한 단어가 5초 이상)
    for ts in timestamps:
        if (ts["end"] - ts["start"]) > 5.0:
            warnings.append(
                f"[{block_id}] 비정상 단어 길이: '{ts['word']}' = {(ts['end'] - ts['start']):.1f}초"
            )
            break

    return warnings


# ── 스크립트 업데이트 ─────────────────────────────────────────────────────────

def update_script_with_narration(
    script: Dict, manifest: Dict[str, Dict], duration_padding_sec: float = 0.5,
) -> Dict:
    """매니페스트의 오디오/타임스탬프 정보를 스크립트 블록에 주입한다.

    duration_sec을 actual + padding으로 갱신하고, 원래 추정치는 보존.
    """
    for scene in script.get("scenes", []):
        for block in scene.get("blocks", []):
            block_id = block.get("block_id", "")
            if block_id not in manifest:
                continue

            entry = manifest[block_id]
            estimated = block.get("duration_sec", 0)
            actual = entry.get("actual_duration_sec", estimated)

            block["narration_audio"] = {
                "path": entry.get("audio_path", ""),
                "actual_duration_sec": round(float(actual), 3),
                "format": "wav",
            }
            block["duration_sec"] = round(float(actual) + duration_padding_sec, 3)

    return script


def compute_absolute_timeline(script: Dict) -> Dict:
    """블록별 absolute_start_sec / absolute_end_sec 누적 계산.
    외부 렌더러가 absolute_start_sec * fps → frame number로 변환해서 사용.
    """
    cursor = 0.0

    for scene in script.get("scenes", []):
        scene_start = cursor
        for block in scene.get("blocks", []):
            block["absolute_start_sec"] = round(cursor, 3)
            cursor += block.get("duration_sec", 0)
            block["absolute_end_sec"] = round(cursor, 3)
        scene["duration_sec"] = round(cursor - scene_start, 3)

    script["total_duration_sec"] = round(cursor, 3)
    return script


# ── 비동기 병렬 정렬 ─────────────────────────────────────────────────────────

async def run_alignment(
    blocks: List[Dict],
    manifest: Dict,
    client: genai.Client,
    model: str,
    max_concurrent: int,
) -> Dict[str, List[Dict]]:
    """모든 블록에 대해 병렬로 STT 타임스탬프를 추출한다."""
    semaphore = asyncio.Semaphore(max_concurrent)
    all_warnings = []

    async def align_one(block: Dict) -> tuple:
        block_id = block["block_id"]
        audio_path = manifest[block_id].get("audio_path", "")

        if not os.path.exists(audio_path):
            print(f"[word_align] ❌ 오디오 파일 없음: {audio_path}", file=sys.stderr, flush=True)
            return block_id, []

        for attempt in range(1, MAX_RETRIES + 1):
            # 시도마다 온도를 조금씩 상향 (0.0 -> 0.1 -> 0.2 ...)
            current_temp = 0.1 * (attempt - 1)
            
            async with semaphore:
                timestamps = await extract_word_timestamps(
                    audio_path=audio_path,
                    narration_text=block["narration"],
                    client=client,
                    model=model,
                    temperature=current_temp,
                )

            if timestamps:
                # 검증
                warns = validate_timestamps(timestamps, block["narration"], block_id)
                if warns:
                    all_warnings.extend(warns)
                print(f"[word_align]   ✅ [{block_id}] {len(timestamps)} words aligned", file=sys.stderr, flush=True)
                return block_id, timestamps

            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * attempt
                print(f"[word_align]   ⚠️ [{block_id}] 시도 {attempt} 실패, {delay}초 후 재시도...", file=sys.stderr, flush=True)
                await asyncio.sleep(delay)

        print(f"[word_align]   ❌ [{block_id}] {MAX_RETRIES}회 시도 후 최종 실패", file=sys.stderr, flush=True)
        return block_id, []

    results = await asyncio.gather(*[align_one(b) for b in blocks])

    # 검증 경고 출력
    if all_warnings:
        print(f"\n[word_align] ⚠️ 검증 경고 {len(all_warnings)}건:", file=sys.stderr, flush=True)
        for w in all_warnings:
            print(f"  - {w}", file=sys.stderr, flush=True)

    return dict(results)


# ── CLI 진입점 ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens Word Alignment Tool — Gemini STT로 단어별 타임스탬프를 추출한다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""사용 예시:
  python tools/word_align.py \\
      --audio-dir    data/narration_audio/ \\
      --manifest     data/narration_audio/manifest.json \\
      --script       data/script_output.json \\
      --output       data/word_timestamps.json \\
      --updated-script data/final_script_with_narration.json

출력 (stdout):
  {"total_blocks": 12, "aligned_blocks": 12, "failed_blocks": 0, "total_words": 847}
""",
    )
    parser.add_argument("--audio-dir", required=True, help="WAV 오디오 파일들이 있는 디렉터리")
    parser.add_argument("--manifest", required=True, help="TTS 매니페스트 JSON 경로 (block_id → audio_path 매핑)")
    parser.add_argument("--script", required=True, help="입력 스크립트 JSON 경로")
    parser.add_argument("--output", required=True, help="단어 타임스탬프 출력 JSON 경로")
    parser.add_argument("--updated-script", default=None, help="(선택) 타임스탬프+타임라인이 주입된 최종 스크립트 저장 경로")
    parser.add_argument("--model", default=DEFAULT_STT_MODEL, help=f"STT 모델 ID (기본값: {DEFAULT_STT_MODEL})")
    parser.add_argument("--max-concurrent", type=int, default=MAX_CONCURRENT, help=f"동시 STT 요청 수 (기본값: {MAX_CONCURRENT})")
    parser.add_argument("--padding", type=float, default=DURATION_PADDING_SEC, help=f"블록별 duration 패딩 초 (기본값: {DURATION_PADDING_SEC})")

    args = parser.parse_args()

    # ── 입력 파일 검증 ──────────────────────────────────────────────────────
    for path, name in [(args.script, "스크립트"), (args.manifest, "매니페스트")]:
        if not os.path.exists(path):
            print(f"[word_align] ERROR: {name} 파일을 찾을 수 없음: {path}", file=sys.stderr)
            sys.exit(1)

    # 스크립트 로드
    with open(args.script, "r", encoding="utf-8") as f:
        script = json.load(f)

    # 매니페스트 로드
    with open(args.manifest, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 오디오 경로 보정: 매니페스트의 상대 경로를 audio-dir 기준으로 절대 경로로 변환
    for block_id, entry in manifest.items():
        audio_path = entry.get("audio_path", "")
        if not os.path.isabs(audio_path):
            # audio_path가 "data/narration_audio/xxx.wav" 형태일 수 있음
            # 또는 단순 파일명일 수 있음 → audio-dir와 결합
            basename = os.path.basename(audio_path)
            candidate = os.path.join(args.audio_dir, basename)
            if os.path.exists(candidate):
                entry["audio_path"] = os.path.abspath(candidate)
            elif os.path.exists(audio_path):
                entry["audio_path"] = os.path.abspath(audio_path)

    # 나레이션 블록 추출
    blocks = extract_narration_blocks(script)
    if not blocks:
        print("[word_align] ERROR: 나레이션 블록을 찾을 수 없음", file=sys.stderr)
        sys.exit(1)

    # 오디오가 있는 블록만 필터
    pending = [b for b in blocks if b["block_id"] in manifest and "audio_path" in manifest[b["block_id"]]]
    # 이미 타임스탬프가 있는 블록 제외
    pending = [b for b in pending if not manifest[b["block_id"]].get("word_timestamps")]

    print(f"[word_align] 전체 블록: {len(blocks)}개, 정렬 대상: {len(pending)}개, 캐시됨: {len(blocks) - len(pending)}개", file=sys.stderr, flush=True)

    # ── STT 실행 ────────────────────────────────────────────────────────────
    client = genai.Client()
    start_time = time.time()

    if pending:
        results = asyncio.run(run_alignment(
            blocks=pending,
            manifest=manifest,
            client=client,
            model=args.model,
            max_concurrent=args.max_concurrent,
        ))

        # 매니페스트에 타임스탬프 병합
        for block_id, timestamps in results.items():
            if timestamps:
                manifest[block_id]["word_timestamps"] = timestamps
    else:
        results = {}
        print("[word_align] 모든 블록이 이미 정렬됨 — 스킵", file=sys.stderr, flush=True)

    elapsed = time.time() - start_time

    # ── 결과 저장 ───────────────────────────────────────────────────────────
    # 1. word_timestamps.json 저장 (블록별 타임스탬프만)
    timestamps_output = {}
    for block_id, entry in manifest.items():
        if "word_timestamps" in entry and entry["word_timestamps"]:
            timestamps_output[block_id] = entry["word_timestamps"]

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(timestamps_output, f, indent=2, ensure_ascii=False)
    print(f"[word_align] 타임스탬프 저장 → {args.output}", file=sys.stderr, flush=True)

    # 2. 매니페스트 갱신 (타임스탬프 포함)
    with open(args.manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # 3. (선택) 최종 스크립트 업데이트
    if args.updated_script:
        # 오디오 경로를 data/ 기준 상대 경로로 변환
        manifest_relative = {}
        for block_id, entry in manifest.items():
            rel_entry = {**entry}
            abs_path = rel_entry.get("audio_path", "")
            if os.path.isabs(abs_path):
                try:
                    rel_entry["audio_path"] = os.path.relpath(abs_path, "datas").replace("\\", "/")
                except ValueError:
                    pass  # 다른 드라이브일 경우
            manifest_relative[block_id] = rel_entry

        script = update_script_with_narration(script, manifest_relative, args.padding)
        script = compute_absolute_timeline(script)

        os.makedirs(os.path.dirname(args.updated_script) or ".", exist_ok=True)
        with open(args.updated_script, "w", encoding="utf-8") as f:
            json.dump(script, f, indent=2, ensure_ascii=False)
        print(f"[word_align] 최종 스크립트 저장 → {args.updated_script}", file=sys.stderr, flush=True)
        print(f"[word_align] 총 길이: {script.get('total_duration_sec', 0):.1f}초", file=sys.stderr, flush=True)

    # ── 요약 출력 (stdout JSON) ─────────────────────────────────────────────
    total_words = sum(len(ts) for ts in timestamps_output.values())
    aligned_count = len(timestamps_output)
    failed_count = len(blocks) - aligned_count

    summary = {
        "total_blocks": len(blocks),
        "aligned_blocks": aligned_count,
        "failed_blocks": failed_count,
        "total_words": total_words,
        "elapsed_sec": round(elapsed, 1),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
