"""
Ensemble Word Alignment — large-v3를 N회 반복 정렬 후 평균 타임스탬프 산출.
"""
import json
import os
import sys
import time
import statistics
from typing import Dict, List

import stable_whisper

# ── 설정 ──
RUNS = 5
MODEL_NAME = "large-v3"
DEVICE = "cuda"
AUDIO_DIR = "data/narration_audio/"
MANIFEST_PATH = "data/narration_audio/manifest.json"
SCRIPT_PATH = "data/script_output.json"
OUTPUT_PATH = "data/word_timestamps.json"
UPDATED_SCRIPT_PATH = "data/final_script_with_narration.json"
DURATION_PADDING_SEC = 0.5


def extract_narration_blocks(script):
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


def align_once(model, block, audio_path):
    try:
        result = model.align(audio_path, block["narration"], language='en')
        timestamps = []
        for seg in result.segments:
            for w in seg.words:
                clean = w.word.strip()
                if clean:
                    timestamps.append({
                        "word": clean,
                        "start": round(float(w.start), 3),
                        "end": round(float(w.end), 3),
                    })
        return timestamps
    except Exception as e:
        print(f"  ❌ [{block['block_id']}] {e}", file=sys.stderr, flush=True)
        return []


def average_timestamps(all_runs: List[List[Dict]]) -> List[Dict]:
    """N회 결과에서 단어별 start/end 평균 + 표준편차 계산."""
    if not all_runs or not all_runs[0]:
        return []

    word_count = len(all_runs[0])
    averaged = []

    for i in range(word_count):
        starts = []
        ends = []
        word_text = all_runs[0][i]["word"]

        for run in all_runs:
            if i < len(run):
                starts.append(run[i]["start"])
                ends.append(run[i]["end"])

        avg_start = round(statistics.mean(starts), 3)
        avg_end = round(statistics.mean(ends), 3)

        entry = {
            "word": word_text,
            "start": avg_start,
            "end": avg_end,
        }

        # 표준편차가 있으면 기록 (디버깅용)
        if len(starts) >= 2:
            entry["start_std_ms"] = round(statistics.stdev(starts) * 1000, 1)
            entry["end_std_ms"] = round(statistics.stdev(ends) * 1000, 1)

        averaged.append(entry)

    return averaged


def update_script_with_narration(script, manifest, padding=0.5):
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
            block["duration_sec"] = round(float(actual) + padding, 3)
    return script


def compute_absolute_timeline(script):
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


def main():
    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        script = json.load(f)
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 경로 보정
    for block_id, entry in manifest.items():
        audio_path = entry.get("audio_path", "")
        if not os.path.isabs(audio_path):
            candidate = os.path.join(AUDIO_DIR, os.path.basename(audio_path))
            if os.path.exists(candidate):
                entry["audio_path"] = os.path.abspath(candidate)

    blocks = extract_narration_blocks(script)
    pending = [b for b in blocks if b["block_id"] in manifest]

    print(f"[ensemble] {MODEL_NAME} x {RUNS}회 앙상블 정렬 시작 ({DEVICE})", file=sys.stderr, flush=True)
    print(f"[ensemble] 대상 블록: {len(pending)}개\n", file=sys.stderr, flush=True)

    # 모델 1회만 로드
    print(f"[ensemble] 모델 로드 중...", file=sys.stderr, flush=True)
    model = stable_whisper.load_model(MODEL_NAME, device=DEVICE)

    # 블록별로 N회 반복
    all_block_runs: Dict[str, List[List[Dict]]] = {b["block_id"]: [] for b in pending}
    total_start = time.time()

    for run_idx in range(RUNS):
        print(f"\n[ensemble] ── Run {run_idx + 1}/{RUNS} ──", file=sys.stderr, flush=True)
        run_start = time.time()

        for block in pending:
            block_id = block["block_id"]
            audio_path = manifest[block_id].get("audio_path", "")
            if not os.path.exists(audio_path):
                continue
            ts = align_once(model, block, audio_path)
            if ts:
                all_block_runs[block_id].append(ts)
                print(f"  ✅ [{block_id}] {len(ts)} words", file=sys.stderr, flush=True)

        elapsed = time.time() - run_start
        print(f"[ensemble] Run {run_idx + 1} 완료: {elapsed:.1f}초", file=sys.stderr, flush=True)

    # 평균 계산
    print(f"\n[ensemble] 평균 타임스탬프 계산 중...", file=sys.stderr, flush=True)
    final_timestamps = {}
    stability_report = []

    for block_id, runs in all_block_runs.items():
        if not runs:
            final_timestamps[block_id] = []
            continue

        averaged = average_timestamps(runs)
        final_timestamps[block_id] = averaged

        # 안정성 통계
        if averaged and "start_std_ms" in averaged[0]:
            stds = [w["start_std_ms"] for w in averaged] + [w["end_std_ms"] for w in averaged]
            avg_std = statistics.mean(stds)
            max_std = max(stds)
            stability_report.append({
                "block_id": block_id,
                "words": len(averaged),
                "avg_std_ms": round(avg_std, 1),
                "max_std_ms": round(max_std, 1),
            })

    # 타임스탬프 저장 (std 필드 제거한 클린 버전)
    clean_timestamps = {}
    for block_id, words in final_timestamps.items():
        clean_timestamps[block_id] = [
            {"word": w["word"], "start": w["start"], "end": w["end"]}
            for w in words
        ]

    # manifest에 word_timestamps 주입
    for block_id, ts in clean_timestamps.items():
        if block_id in manifest and ts:
            manifest[block_id]["word_timestamps"] = ts

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(clean_timestamps, f, indent=2, ensure_ascii=False)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # updated script
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

    script = update_script_with_narration(script, manifest_relative, DURATION_PADDING_SEC)
    script = compute_absolute_timeline(script)

    with open(UPDATED_SCRIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    total_elapsed = time.time() - total_start

    # 결과 출력
    total_words = sum(len(ts) for ts in clean_timestamps.values())
    print(f"\n{'='*60}", flush=True)
    print(f"  Ensemble Alignment Complete", flush=True)
    print(f"  {MODEL_NAME} x {RUNS} runs → averaged", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"  블록: {len(pending)}개", flush=True)
    print(f"  총 단어: {total_words}개", flush=True)
    print(f"  총 소요: {total_elapsed:.1f}초", flush=True)
    print(f"{'='*60}", flush=True)

    if stability_report:
        print(f"\n  블록별 안정성 (표준편차):", flush=True)
        overall_stds = []
        for r in sorted(stability_report, key=lambda x: x["avg_std_ms"], reverse=True):
            print(f"    [{r['block_id']}] avg: {r['avg_std_ms']}ms, max: {r['max_std_ms']}ms", flush=True)
            overall_stds.append(r["avg_std_ms"])

        print(f"\n  전체 평균 표준편차: {statistics.mean(overall_stds):.1f}ms", flush=True)
        print(f"  → 이 값이 낮을수록 정렬이 안정적 (일관성 높음)", flush=True)

    print(f"\n  출력: {OUTPUT_PATH}", flush=True)
    print(f"  스크립트: {UPDATED_SCRIPT_PATH}", flush=True)

    # JSON summary
    summary = {
        "total_blocks": len(pending),
        "aligned_blocks": sum(1 for ts in clean_timestamps.values() if ts),
        "failed_blocks": sum(1 for ts in clean_timestamps.values() if not ts),
        "total_words": total_words,
        "ensemble_runs": RUNS,
        "elapsed_sec": round(total_elapsed, 1),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
