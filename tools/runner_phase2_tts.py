"""Phase 2 자동 실행 스크립트 (직접 import 방식).

run_full_pipeline.py와 달리 tts_synthesize를 직접 import하여
subprocess 오버헤드 없이 TTS를 생성한다.

사전 요구사항:
    - tmp/tts_prompt_{block_id}.txt (System Prompt + Director's Notes + TRANSCRIPT 통합본)

사용법:
    python tools/runner_phase2_tts.py
"""
import json
import os
import sys
import asyncio

# Ensure UTF-8 output on Windows terminals (cp949 can't encode emoji)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from config import DATAS_DIR, TOOLS_DIR, TMP_DIR, TTS_SPEED, TTS_TEMPERATURE
import tts_synthesize
from audio_evaluator import validate_audio_quality


# ── 메인 로직 ────────────────────────────────────────────────────────────────

async def run_all():
    script_path = os.path.join(DATAS_DIR, "script_output.json")
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    os.makedirs(TMP_DIR, exist_ok=True)
    audio_dir = os.path.join(DATAS_DIR, "narration_audio")
    os.makedirs(audio_dir, exist_ok=True)


    manifest = {}
    failed_blocks = []

    # 전체 블록 플래튼
    all_blocks = [
        (scene["scene_id"], block)
        for scene in script["scenes"]
        for block in scene["blocks"]
    ]
    total = len(all_blocks)

    for idx, (scene_id, block) in enumerate(all_blocks):
        block_id = block["block_id"]
        tone = "Neutral"  # reserved for future use

        # 프롬프트 파일 필수 — Phase 2에서 작성
        prompt_file = os.path.join(TMP_DIR, f"tts_prompt_{block_id}.txt")
        if not os.path.exists(prompt_file):
            print(f"[runner_phase2] ERROR: {prompt_file} not found", file=sys.stderr)
            print("Phase 2에서 tts_prompt 파일을 먼저 작성하세요.", file=sys.stderr)
            sys.exit(1)

        out_path = os.path.join(audio_dir, f"{block_id}.wav")
        if os.path.exists(out_path):
            print(f"[runner_phase2] Skipping [{idx+1}/{total}] {block_id} (already exists)", flush=True)
            import wave
            try:
                with wave.open(out_path, 'rb') as w:
                    actual_dur = w.getnframes() / float(w.getframerate())
            except Exception:
                actual_dur = 0.0
            manifest[block_id] = {
                "audio_path": out_path,
                "actual_duration_sec": actual_dur,
                "qa_passed": True,
                "qa_reason": "Skipped (already exists)"
            }
            continue

        print(f"[runner_phase2] Synthesizing [{idx+1}/{total}] {block_id} (tone={tone})", flush=True)

        MAX_QA_RETRIES = 3
        actual_dur = 0.0
        final_qa_result = {}

        # retry_block이 True이면 QA 루프를 처음부터 재실행
        while True:
            retry_block = False

            # 매 시도마다 프롬프트 파일을 다시 읽음 (사용자가 수정 후 재시도 가능)
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt = f.read().strip()


            for attempt in range(1, MAX_QA_RETRIES + 1):
                if attempt > 1:
                    print(f"  ↪️ [QA 재시도 {attempt}/{MAX_QA_RETRIES}] {block_id} 재생성 중...", flush=True)

                result = await tts_synthesize.synthesize(
                    prompt=prompt,
                    output_path=out_path,
                    voice=tts_synthesize.DEFAULT_VOICE,
                    model=tts_synthesize.DEFAULT_TTS_MODEL,
                    speed=TTS_SPEED,
                    temperature=TTS_TEMPERATURE,
                )

                actual_dur = result.get("actual_duration_sec", 0.0)
                if actual_dur == 0.0:
                    print(f"[runner_phase2] ERROR: {block_id} duration=0 — WAV가 비어있거나 API 오류", file=sys.stderr, flush=True)
                    break  # API 자체 오류면 QA 없이 종료

                # Audio QA Validation (Gemini 3 Flash)
                clean_text = block.get("narration", "")
                final_qa_result = await validate_audio_quality(out_path, clean_text, prompt)

                if final_qa_result.get("is_valid", False):
                    print(f"  ✅ QA 통과: {final_qa_result.get('reason')}", flush=True)
                    break
                else:
                    print(f"  ⚠️ QA 실패 (시도 {attempt}): {final_qa_result.get('reason')}", file=sys.stderr, flush=True)
                    if attempt < MAX_QA_RETRIES:
                        await asyncio.sleep(1.0) # 재시도 전 약간의 딜레이
                    else:
                        # QA 최대 재시도 초과 -- 사용자에게 판단을 맡김
                        print(f"\n  {'='*60}", flush=True)
                        print(f"  QA {MAX_QA_RETRIES}회 연속 실패: {block_id}", flush=True)
                        print(f"  사유: {final_qa_result.get('reason', 'N/A')}", flush=True)
                        print(f"  {'='*60}", flush=True)
                        print(f"  [c] 현재 오디오로 계속 진행 (continue)", flush=True)
                        print(f"  [r] 이 블록만 재시도 ({MAX_QA_RETRIES}회 추가)", flush=True)
                        print(f"  [a] 파이프라인 중단 (abort)", flush=True)
                        print(f"  {'='*60}", flush=True)

                        # 사용자 입력 대기 (async 컨텍스트에서 블로킹 input 호출)
                        choice = (await asyncio.to_thread(input, "  선택 [c/r/a]: ")).strip().lower()

                        if choice == "a":
                            print("  파이프라인을 중단합니다.", flush=True)
                            sys.exit(1)
                        elif choice == "r":
                            print(f"  {block_id} 재시도를 시작합니다...", flush=True)
                            retry_block = True
                        else:
                            print(f"  QA 실패본으로 계속 진행합니다.", flush=True)

            # retry_block이 False면 while 루프 탈출
            if not retry_block:
                break

        if actual_dur == 0.0:
            failed_blocks.append(block_id)

        manifest[block_id] = {
            "audio_path": result.get("audio_path", out_path),
            "actual_duration_sec": actual_dur,
            "qa_passed": final_qa_result.get("is_valid", False) if actual_dur > 0.0 else False,
            "qa_reason": final_qa_result.get("reason", "") if actual_dur > 0.0 else "API Error"
        }

    # manifest 저장
    manifest_path = os.path.join(audio_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[runner_phase2] Manifest saved: {manifest_path} ({len(manifest)} blocks)", flush=True)

    # 실패 블록 검사
    if failed_blocks:
        print(f"\n[FATAL] {len(failed_blocks)} 블록의 duration이 0입니다:", file=sys.stderr, flush=True)
        for bid in failed_blocks:
            print(f"  - {bid}", file=sys.stderr, flush=True)
        print("word_align 실행 전 해당 블록의 WAV를 재생성하세요.", file=sys.stderr, flush=True)
        sys.exit(1)


def main():
    asyncio.run(run_all())
    print("[runner_phase2] TTS synthesis complete.")

    audio_dir = os.path.join(DATAS_DIR, "narration_audio")
    import subprocess
    cmd = [
        "python", os.path.join(TOOLS_DIR, "word_align.py"),
        "--audio-dir", audio_dir,
        "--manifest", os.path.join(audio_dir, "manifest.json"),
        "--script", os.path.join(DATAS_DIR, "script_output.json"),
        "--output", os.path.join(DATAS_DIR, "word_timestamps.json"),
        "--updated-script", os.path.join(DATAS_DIR, "final_script_with_narration.json"),
    ]
    subprocess.run(cmd, check=True)
    print("[runner_phase2] Phase 2 complete.")


if __name__ == "__main__":
    main()
