"""
Word Alignment CLI Tool — stable-ts(Whisper)로 단어별 타임스탬프를 강제 정렬(Forced-Align)하는 도구.

사용법:
    python tools/word_align.py \
        --audio-dir    data/narration_audio/ \
        --manifest     data/narration_audio/manifest.json \
        --script       data/script_output.json \
        --output       data/word_timestamps.json \
        --updated-script data/final_script_with_narration.json
"""
import argparse
import json
import os
import sys
import time
import re
from typing import Dict, List, Any

# stable-ts 패키지 (PyTorch 기반)
import stable_whisper

# ── 상수 ──────────────────────────────────────────────────────────────────────
DURATION_PADDING_SEC = 0.5


# ── 블록 추출 ─────────────────────────────────────────────────────────────────

def extract_narration_blocks(script: Dict) -> List[Dict]:
    """스크립트 JSON에서 나레이션이 있는 블록을 추출한다."""
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


# ── 출력 검증 ─────────────────────────────────────────────────────────────────

def validate_timestamps(
    timestamps: List[Dict], narration_text: str, block_id: str,
) -> List[str]:
    """타임스탬프 품질 검증. 강제 정렬 결과이므로 주로 비정상적인 길이만 확인한다."""
    warnings = []

    if not timestamps:
        warnings.append(f"[{block_id}] 타임스탬프가 비어있음")
        return warnings

    for ts in timestamps:
        duration = ts["end"] - ts["start"]
        # 너무 긴 단어
        if duration > 5.0:
            warnings.append(
                f"[{block_id}] 비정상 단어 길이: '{ts['word']}' = {duration:.1f}초"
            )
            
    return warnings


# ── 정렬 로직 (stable-ts) ─────────────────────────────────────────────────────

def align_one(model, block: Dict, audio_path: str):
    """주어진 오디오와 텍스트를 stable-ts로 강제 정렬한다."""
    block_id = block["block_id"]

    try:
        # 모델의 align 함수 호출 (언어를 영어로 고정하여 성능 극대화)
        result = model.align(audio_path, block["narration"], language='en', fast_mode=True)
        
        timestamps = []
        # result.segments -> result.words 형태에서 모든 단어 추출
        for segment in result.segments:
            for word in segment.words:
                # 원본 텍스트(구두점 포함) 유지
                clean_word = word.word.strip()
                if not clean_word:
                    continue
                    
                timestamps.append({
                    "word": clean_word,
                    "start": round(float(word.start), 3),
                    "end": round(float(word.end), 3),
                })
                
        return timestamps
    except Exception as e:
        print(f"[word_align] ❌ [{block_id}] 정렬 실패: {e}", file=sys.stderr, flush=True)
        return []


def run_alignment(
    blocks: List[Dict],
    manifest: Dict,
) -> Dict[str, List[Dict]]:
    """모든 블록에 대해 로컬 Whisper 모델로 정렬을 수행한다."""
    results = {}
    all_warnings = []
    
    print("[word_align] stable-ts (Whisper base.en) 모델 로드 중... (CPU)", file=sys.stderr, flush=True)
    # Whisper base.en 모델 로드 (상대적으로 가볍고 빠름)
    model = stable_whisper.load_model('base.en')
    
    for block in blocks:
        block_id = block["block_id"]
        audio_path = manifest[block_id].get("audio_path", "")

        if not os.path.exists(audio_path):
            print(f"[word_align] ❌ 오디오 파일 없음: {audio_path}", file=sys.stderr, flush=True)
            results[block_id] = []
            continue

        timestamps = align_one(model, block, audio_path)
        
        if timestamps:
            warns = validate_timestamps(timestamps, block["narration"], block_id)
            if warns:
                all_warnings.extend(warns)
            print(f"[word_align]   ✅ [{block_id}] {len(timestamps)} words aligned (stable-ts)", file=sys.stderr, flush=True)
            results[block_id] = timestamps
        else:
            print(f"[word_align]   ❌ [{block_id}] 정렬 실패", file=sys.stderr, flush=True)
            results[block_id] = []

    if all_warnings:
        print(f"\n[word_align] ⚠️ 검증 경고 {len(all_warnings)}건:", file=sys.stderr, flush=True)
        for w in all_warnings:
            print(f"  - {w}", file=sys.stderr, flush=True)

    return results

# ── 스크립트 업데이트 ─────────────────────────────────────────────────────────

def update_script_with_narration(
    script: Dict, manifest: Dict[str, Dict], duration_padding_sec: float = 0.5,
) -> Dict:
    """매니페스트의 오디오/타임스탬프 정보를 스크립트 블록에 주입한다."""
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
    """블록별 absolute_start_sec / absolute_end_sec 누적 계산."""
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


# ── CLI 진입점 ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens Word Alignment Tool — stable-ts(Whisper)로 파싱"
    )
    parser.add_argument("--audio-dir", required=True, help="WAV 오디오 파일들이 있는 디렉터리")
    parser.add_argument("--manifest", required=True, help="TTS 매니페스트 JSON 경로")
    parser.add_argument("--script", required=True, help="입력 스크립트 JSON 경로")
    parser.add_argument("--output", required=True, help="단어 타임스탬프 출력 JSON 경로")
    parser.add_argument("--updated-script", default=None, help="최종 스크립트 저장 경로")
    parser.add_argument("--padding", type=float, default=DURATION_PADDING_SEC, help="패딩 초")
    # 하위 호환성 유지 (무시됨)
    parser.add_argument("--model", default="base.en", help="(무시됨, base.en 고정)")
    parser.add_argument("--max-concurrent", type=int, default=1, help="(무시됨)")

    args = parser.parse_args()

    for path, name in [(args.script, "스크립트"), (args.manifest, "매니페스트")]:
        if not os.path.exists(path):
            print(f"[word_align] ERROR: {name} 파일 없음: {path}", file=sys.stderr)
            sys.exit(1)

    with open(args.script, "r", encoding="utf-8") as f:
        script = json.load(f)

    with open(args.manifest, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 경로 보정
    for block_id, entry in manifest.items():
        audio_path = entry.get("audio_path", "")
        if not os.path.isabs(audio_path):
            basename = os.path.basename(audio_path)
            candidate = os.path.join(args.audio_dir, basename)
            if os.path.exists(candidate):
                entry["audio_path"] = os.path.abspath(candidate)
            elif os.path.exists(audio_path):
                entry["audio_path"] = os.path.abspath(audio_path)

    blocks = extract_narration_blocks(script)
    if not blocks:
        sys.exit(1)

    pending = [b for b in blocks if b["block_id"] in manifest and "audio_path" in manifest[b["block_id"]]]
    # (주의) 강제 정렬 개선을 위해 이번에는 캐시 여부 검사 없이 모두 덮어쓰기 진행
    pending = [b for b in pending]

    print(f"[word_align] 정렬 대상: {len(pending)}개", file=sys.stderr, flush=True)

    start_time = time.time()

    if pending:
        results = run_alignment(
            blocks=pending,
            manifest=manifest,
        )

        for block_id, timestamps in results.items():
            if timestamps:
                manifest[block_id]["word_timestamps"] = timestamps
    else:
        print("[word_align] 정렬 대상 없음", file=sys.stderr, flush=True)

    elapsed = time.time() - start_time

    # 출력 저장
    timestamps_output = {}
    for block_id, entry in manifest.items():
        if "word_timestamps" in entry and entry["word_timestamps"]:
            timestamps_output[block_id] = entry["word_timestamps"]

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(timestamps_output, f, indent=2, ensure_ascii=False)
    
    with open(args.manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    if args.updated_script:
        manifest_relative = {}
        for block_id, entry in manifest.items():
            rel_entry = {**entry}
            abs_path = rel_entry.get("audio_path", "")
            if os.path.isabs(abs_path):
                try:
                    rel_entry["audio_path"] = os.path.relpath(abs_path, "data").replace("\\", "/")
                except ValueError:
                    pass
            manifest_relative[block_id] = rel_entry

        script = update_script_with_narration(script, manifest_relative, args.padding)
        script = compute_absolute_timeline(script)

        os.makedirs(os.path.dirname(args.updated_script) or ".", exist_ok=True)
        with open(args.updated_script, "w", encoding="utf-8") as f:
            json.dump(script, f, indent=2, ensure_ascii=False)

    total_words = sum(len(ts) for ts in timestamps_output.values())
    summary = {
        "total_blocks": len(blocks),
        "aligned_blocks": len(timestamps_output),
        "failed_blocks": len(blocks) - len(timestamps_output),
        "total_words": total_words,
        "elapsed_sec": round(elapsed, 1),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
