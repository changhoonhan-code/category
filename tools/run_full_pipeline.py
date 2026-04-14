"""Phase 2 (TTS + Word Align) → Phase 3-1 (B-roll Mapping) 자동 실행 스크립트.

사용법:
    python tools/run_full_pipeline.py
"""
import json
import os
import subprocess
import sys

from config import PROJ_ROOT, DATAS_DIR, TOOLS_DIR, TMP_DIR, MODELS, TTS_VOICE

SCRIPT = os.path.join(DATAS_DIR, "script_output.json")
OUT_DIR = os.path.join(DATAS_DIR, "narration_audio")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

# 1. 시스템 프롬프트 — 쇼러너가 이미 작성해 둔 파일이 있으면 덮어쓰지 않는다
sys_file = os.path.join(TMP_DIR, "tts_system_base.txt")
if not os.path.exists(sys_file):
    os.makedirs(TMP_DIR, exist_ok=True)
    with open(sys_file, "w", encoding="utf-8") as f:
        f.write("""# AUDIO PROFILE: "The Consumer Data Detective"
You are the narrator for ReviewLens, a data-driven YouTube consumer investigation channel.
Character ID: An analyst who spent hours deep in the reviews and found a pattern nobody else noticed — and wants to walk you through exactly what the data reveals. Genuinely curious, methodical, always following the evidence trail.
Motto: "Every review. Every pattern. Here's what I found."

## VOCAL CHARACTERISTICS
- Default Register: Mid-range, centered. The "analyst sharing a discovery" register — not a news anchor, not a podcast bro.
- Soft Palate: Naturally raised to maintain clarity and subtle brightness, even when delivering negative data. Never nasally.
- Consonants: Clean and precise, especially on numbers and technical terms. Punchy without being aggressive.
- Vowels: Natural duration — elongate only when Director's Notes specifically call for emphasis.
- The "Data Detective" quality: Curiosity lives in the pitch variation; precision lives in the consonants. You're genuinely interested in what the patterns reveal — and sometimes genuinely surprised.

## THE SCENE: An Intimate Late-Night Lab
You are at a desk, 18 inches from a high-end condenser microphone. The room is quiet and dimly lit — it's late, you've been deep in the data for hours, and you just found the pattern. You're recording this for one person: the viewer who is about to spend their money on this product. You are not performing for an audience. You are telling one person the truth. That urgency is in your voice — not as stress, but as purpose.""")
    print(f"[run_full_pipeline] tts_system_base.txt 생성 완료: {sys_file}", flush=True)
else:
    print(f"[run_full_pipeline] tts_system_base.txt 기존 파일 유지 (쇼러너 작성본): {sys_file}", flush=True)

# 2. 대본 로드
with open(SCRIPT, "r", encoding="utf-8") as f:
    script_data = json.load(f)

blocks = [b for s in script_data["scenes"] for b in s["blocks"]]

# 3. TTS 실행 (Phase 2) — stdout을 캡처해 manifest 빌드
manifest = {}
prev_narration = ""
for i, b in enumerate(blocks):
    bid = b["block_id"]
    narration = b["narration"]

    # 감독 노트 생성
    style = "Conversational, precise. Curious skeptic sharing findings."
    if i == 0:
        style = "Hook energy — intrigued, not dramatic. Drop one surprising number, then pause."
    elif i == len(blocks) - 1:
        style = "Measured, fair assessment. Trusted advisor tone. Calm finality."

    prompt_content = f"### DIRECTOR'S NOTES\n- Style: {style}\n\n"
    if prev_narration:
        prompt_content += f"### SAMPLE CONTEXT\n{prev_narration}\n\n"
    prompt_content += f"#### TRANSCRIPT\n{narration}\n"

    p_file = os.path.join(TMP_DIR, f"p_{bid}.txt")
    with open(p_file, "w", encoding="utf-8") as f:
        f.write(prompt_content)

    out_wav = os.path.join(OUT_DIR, f"{bid}.wav")
    print(f"--- Synthesizing {bid} ({i+1}/{len(blocks)}) ---")

    proc = subprocess.run(
        ["python", os.path.join(TOOLS_DIR, "tts_synthesize.py"),
         "--prompt-file", p_file, "--system-file", sys_file,
         "--output", out_wav, "--voice", TTS_VOICE, "--model", MODELS["tts"]],
        capture_output=True, text=True, check=False,
    )
    # stderr는 진행 로그 — 그대로 출력
    if proc.stderr:
        print(proc.stderr, end="")
    # stdout은 결과 JSON — manifest에 기록
    try:
        result = json.loads(proc.stdout.strip())
        actual_dur = result.get("actual_duration_sec", 0.0)
        if actual_dur == 0.0:
            print(f"  [ERROR] {bid} TTS duration이 0 — WAV 파일이 비어있거나 API 오류", flush=True)
        manifest[bid] = {
            "audio_path": result.get("audio_path", out_wav),
            "actual_duration_sec": actual_dur,
        }
    except (json.JSONDecodeError, ValueError):
        print(f"  [ERROR] {bid} TTS 결과 파싱 실패 — duration=0으로 기록", flush=True)
        manifest[bid] = {"audio_path": out_wav, "actual_duration_sec": 0.0}

    prev_narration = narration

# manifest 저장 (word_align이 읽어야 함)
manifest_path = os.path.join(OUT_DIR, "manifest.json")
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print(f"--- Manifest saved: {manifest_path} ({len(manifest)} blocks) ---")

# duration=0 블록 검사 — word_align이 0으로 읽는 문제 방지
zero_dur_blocks = [bid for bid, entry in manifest.items() if entry.get("actual_duration_sec", 0.0) == 0.0]
if zero_dur_blocks:
    print(f"\n[FATAL] {len(zero_dur_blocks)} 블록의 duration이 0입니다:", flush=True)
    for bid in zero_dur_blocks:
        print(f"  - {bid}", flush=True)
    print("word_align 실행 시 이 블록들의 타임스탬프가 깨집니다. WAV 파일을 확인 후 재시도하세요.")
    sys.exit(1)

# 4. Word Align / 타임스탬프 생성 (Phase 2 완료)
print("\n--- Running Word Alignment (Phase 2) ---")
subprocess.run(["python", os.path.join(TOOLS_DIR, "word_align.py"),
                "--audio-dir", OUT_DIR, "--manifest", os.path.join(OUT_DIR, "manifest.json"),
                "--script", SCRIPT, "--output", os.path.join(DATAS_DIR, "word_timestamps.json"),
                "--updated-script", os.path.join(DATAS_DIR, "final_script_with_narration.json")], check=False)

# 4.5. Media Indexing (Phase 3-0 Pre-flight)
print("\n--- Running Media Indexing (Phase 3-0 Pre-flight) ---")
subprocess.run([
    "python", os.path.join(TOOLS_DIR, "media_indexer.py"),
    "--input-dir", "one_product/",
    "--output-dir", DATAS_DIR,
    "--themes", os.path.join(DATAS_DIR, "summary.json"),
    "--script", SCRIPT,
], check=False)

# 5. B-roll 매핑 (Phase 3-1)
# block_visual_mapping.json이 존재하면 쇼러너 매핑 모드, 아니면 레거시 자동 매칭
mapping_path = os.path.join(DATAS_DIR, "block_visual_mapping.json")
if os.path.exists(mapping_path):
    print("\n--- Running B-roll Mapping (Phase 3-1C: Showrunner Mapping Mode) ---")
    subprocess.run([
        "python", os.path.join(TOOLS_DIR, "broll_mapper.py"),
        "--script", os.path.join(DATAS_DIR, "final_script_with_narration.json"),
        "--media-dir", PROJ_ROOT,
        "--mapping", mapping_path,
        "--output", os.path.join(DATAS_DIR, "script_with_media.json"),
    ], check=False)
else:
    print("\n--- Running B-roll Mapping (Phase 3-1: Legacy Auto-Matching) ---")
    subprocess.run([
        "python", os.path.join(TOOLS_DIR, "broll_mapper.py"),
        "--script", os.path.join(DATAS_DIR, "final_script_with_narration.json"),
        "--media-dir", PROJ_ROOT,
        "--theme-analysis", os.path.join(DATAS_DIR, "summary.json"),
        "--output", os.path.join(DATAS_DIR, "script_with_media.json"),
    ], check=False)

# ─────────────────────────────────────────────────────────
# 파이프라인 종료 지점 (Phase 3-2)
# AI 미디어 생성은 Showrunner가 수동으로 빈 슬롯을 채운 뒤
# data/script_with_media.json 을 외부 Remotion 프로젝트에 전달한다.
# ─────────────────────────────────────────────────────────
print("\n--- PIPELINE COMPLETE ---")
print("Output: data/script_with_media.json")
print("Next step: Run AI media generation (Phase 3-2) for blocks with missing broll_asset,")
print("           then hand off data/ directory to the external Remotion rendering project.")
