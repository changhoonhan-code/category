"""
TTS Synthesize CLI Tool -- 프롬프트 파일을 받아 Gemini TTS API를 호출하는 순수 도구.

프롬프트 파일에는 System Prompt(Audio Profile) + Director's Notes + TRANSCRIPT이
하나로 합쳐져 있다. API 호출 시 prompt 하나만 전달한다.

사용법:
    python tools/tts_synthesize.py \
        --prompt-file  ./tmp/tts_prompt_block_01.txt \
        --output       data/narration_audio/hook_01.wav \
        --voice        Kore \
        --model        gemini-2.5-pro-preview-tts
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import wave

from google import genai
from google.genai import types

from config import MODELS, TTS_VOICE, TTS_SPEED, TTS_SAMPLE_RATE, TTS_SAMPLE_WIDTH, TTS_CHANNELS, MAX_RETRIES, RETRY_BASE_DELAY


# -- 상수 --

DEFAULT_TTS_MODEL = MODELS["tts"]
DEFAULT_VOICE = TTS_VOICE
DEFAULT_SPEED = TTS_SPEED
SAMPLE_RATE = TTS_SAMPLE_RATE
SAMPLE_WIDTH = TTS_SAMPLE_WIDTH
CHANNELS = TTS_CHANNELS


# -- TTS API 호출 --

async def generate_tts(
    client: genai.Client,
    prompt: str,
    model: str = DEFAULT_TTS_MODEL,
    voice: str = DEFAULT_VOICE,
) -> bytes:
    """Gemini TTS API를 호출하여 raw PCM 바이트를 반환한다.

    prompt에 System Prompt + Director's Notes + TRANSCRIPT이 모두 포함되어 있다.
    Gemini SDK는 동기 전용이므로 asyncio.to_thread로 감싸서 호출.
    """
    config = types.GenerateContentConfig(
        temperature=1.5,
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice,
                )
            )
        ),
    )

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=prompt,
        config=config,
    )

    return response.candidates[0].content.parts[0].inline_data.data


# -- WAV 저장 --

def save_wav(pcm_data: bytes, output_path: str, speed: float = 1.0) -> float:
    """Raw PCM 데이터를 WAV 파일로 저장하고 길이(초)를 반환한다.

    speed > 1.0 이면 FFmpeg atempo 필터로 재생 속도를 높인다.
    speed == 1.0 이면 후처리 없이 그대로 저장.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)

    if speed != 1.0:
        tmp_path = output_path + ".tmp.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", output_path,
             "-filter:a", f"atempo={speed}",
             tmp_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=True,
        )
        os.replace(tmp_path, output_path)
        print(f"[tts_synthesize] atempo={speed} applied", file=sys.stderr, flush=True)

    with wave.open(output_path) as wf:
        return wf.getnframes() / wf.getframerate()


# -- 재시도 포함 메인 로직 --

async def synthesize(
    prompt: str,
    output_path: str,
    voice: str,
    model: str,
    speed: float = 1.0,
) -> dict:
    """TTS 생성을 재시도 로직과 함께 실행하고 결과 dict를 반환한다."""
    client = genai.Client()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[tts_synthesize] attempt {attempt}/{MAX_RETRIES} -- model: {model}, voice: {voice}", file=sys.stderr, flush=True)
            pcm_data = await generate_tts(
                client, prompt,
                model=model,
                voice=voice,
            )
            duration = save_wav(pcm_data, output_path, speed=speed)
            duration_rounded = float(round(duration, 3))
            print(f"[tts_synthesize] saved: {output_path} ({duration:.2f}s)", file=sys.stderr, flush=True)
            return {
                "audio_path": output_path,
                "actual_duration_sec": duration_rounded,
            }
        except Exception as e:
            print(f"[tts_synthesize] attempt {attempt} failed: {e}", file=sys.stderr, flush=True)
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * attempt
                print(f"[tts_synthesize] retrying in {delay}s...", file=sys.stderr, flush=True)
                await asyncio.sleep(delay)
            else:
                print(f"[tts_synthesize] all {MAX_RETRIES} attempts failed.", file=sys.stderr, flush=True)
                sys.exit(1)

    # 여기에 도달할 수 없지만 lint 경고 방지용 명시적 반환
    return {"audio_path": "", "actual_duration_sec": 0.0}


# -- CLI 진입점 --

def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens TTS Synthesize Tool -- prompt 파일로 Gemini TTS API를 호출하여 WAV 오디오를 생성한다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""사용 예시:
  python tools/tts_synthesize.py \\
      --prompt-file ./tmp/tts_prompt.txt \\
      --output data/narration_audio/hook_01.wav

출력 (stdout):
  {"audio_path": "data/narration_audio/hook_01.wav", "actual_duration_sec": 4.2}
""",
    )
    parser.add_argument(
        "--prompt-file", required=True,
        help="System Prompt + Director's Notes + TRANSCRIPT이 합쳐진 프롬프트 파일 경로",
    )
    parser.add_argument(
        "--output", required=True,
        help="생성될 WAV 오디오 파일 저장 경로",
    )
    parser.add_argument(
        "--voice", default=DEFAULT_VOICE,
        help=f"TTS 음성 이름 (기본값: {DEFAULT_VOICE})",
    )
    parser.add_argument(
        "--model", default=DEFAULT_TTS_MODEL,
        help=f"TTS 모델 ID (기본값: {DEFAULT_TTS_MODEL})",
    )
    parser.add_argument(
        "--speed", type=float, default=DEFAULT_SPEED,
        help=f"FFmpeg atempo 재생 속도 배율 (기본값: config.TTS_SPEED={DEFAULT_SPEED}, 예: 1.2)",
    )

    args = parser.parse_args()

    # 프롬프트 파일 읽기 (System Prompt + DN + TRANSCRIPT 통합본)
    if not os.path.exists(args.prompt_file):
        print(f"[tts_synthesize] ERROR: prompt file not found: {args.prompt_file}", file=sys.stderr)
        sys.exit(1)
    with open(args.prompt_file, "r", encoding="utf-8") as f:
        prompt = f.read().strip()
    if not prompt:
        print("[tts_synthesize] ERROR: prompt file is empty", file=sys.stderr)
        sys.exit(1)

    # TTS 실행 (prompt만 전달)
    result = asyncio.run(synthesize(
        prompt=prompt,
        output_path=args.output,
        voice=args.voice,
        model=args.model,
        speed=args.speed,
    ))

    # 결과를 stdout에 JSON으로 출력
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
