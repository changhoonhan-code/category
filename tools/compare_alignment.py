"""
Word Alignment Quality Comparison: base.en vs medium.en
base.en으로 별도 정렬 후 medium.en 결과와 비교 분석.
"""
import json
import os
import sys
import stable_whisper

AUDIO_DIR = "data/narration_audio/"
MANIFEST_PATH = "data/narration_audio/manifest.json"
SCRIPT_PATH = "data/script_output.json"
MEDIUM_TIMESTAMPS_PATH = "data/word_timestamps.json"
BASE_TIMESTAMPS_PATH = "data/word_timestamps_base.json"


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


def align_all(model, blocks, manifest):
    results = {}
    for block in blocks:
        block_id = block["block_id"]
        audio_path = manifest[block_id].get("audio_path", "")
        if not os.path.exists(audio_path):
            results[block_id] = []
            continue
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
            results[block_id] = timestamps
            print(f"  ✅ [{block_id}] {len(timestamps)} words", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"  ❌ [{block_id}] {e}", file=sys.stderr, flush=True)
            results[block_id] = []
    return results


def compare(base_ts, medium_ts):
    """블록별/단어별 타이밍 차이 분석."""
    report = {"blocks": [], "summary": {}}
    total_diff_start = 0.0
    total_diff_end = 0.0
    total_words = 0
    max_diff = 0.0
    max_diff_word = ""
    max_diff_block = ""
    blocks_with_mismatch = 0

    all_block_ids = sorted(set(list(base_ts.keys()) + list(medium_ts.keys())))

    for block_id in all_block_ids:
        b_words = base_ts.get(block_id, [])
        m_words = medium_ts.get(block_id, [])

        block_report = {
            "block_id": block_id,
            "base_word_count": len(b_words),
            "medium_word_count": len(m_words),
            "word_count_match": len(b_words) == len(m_words),
            "diffs": [],
        }

        if len(b_words) != len(m_words):
            blocks_with_mismatch += 1

        # 단어 수가 같을 때만 1:1 비교
        min_len = min(len(b_words), len(m_words))
        block_diffs_start = []
        block_diffs_end = []

        for i in range(min_len):
            bw, mw = b_words[i], m_words[i]
            ds = abs(bw["start"] - mw["start"])
            de = abs(bw["end"] - mw["end"])
            total_diff_start += ds
            total_diff_end += de
            total_words += 1
            block_diffs_start.append(ds)
            block_diffs_end.append(de)

            bigger = max(ds, de)
            if bigger > max_diff:
                max_diff = bigger
                max_diff_word = bw["word"]
                max_diff_block = block_id

            # 큰 차이만 기록 (50ms 이상)
            if ds > 0.05 or de > 0.05:
                block_report["diffs"].append({
                    "idx": i,
                    "word": bw["word"],
                    "base_start": bw["start"],
                    "medium_start": mw["start"],
                    "base_end": bw["end"],
                    "medium_end": mw["end"],
                    "diff_start_ms": round(ds * 1000, 1),
                    "diff_end_ms": round(de * 1000, 1),
                })

        if block_diffs_start:
            block_report["avg_diff_start_ms"] = round(
                sum(block_diffs_start) / len(block_diffs_start) * 1000, 1
            )
            block_report["avg_diff_end_ms"] = round(
                sum(block_diffs_end) / len(block_diffs_end) * 1000, 1
            )
            block_report["significant_diffs"] = len(block_report["diffs"])

        report["blocks"].append(block_report)

    if total_words > 0:
        report["summary"] = {
            "total_blocks": len(all_block_ids),
            "total_words_compared": total_words,
            "blocks_with_word_count_mismatch": blocks_with_mismatch,
            "avg_start_diff_ms": round(total_diff_start / total_words * 1000, 1),
            "avg_end_diff_ms": round(total_diff_end / total_words * 1000, 1),
            "max_diff_ms": round(max_diff * 1000, 1),
            "max_diff_word": max_diff_word,
            "max_diff_block": max_diff_block,
        }

    return report


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

    # ── Step 1: base.en 정렬 (CPU) ──
    print("\n[compare] === base.en (CPU) 정렬 시작 ===", file=sys.stderr, flush=True)
    base_model = stable_whisper.load_model('base.en', device='cpu')
    base_results = align_all(base_model, pending, manifest)
    del base_model  # 메모리 해제

    with open(BASE_TIMESTAMPS_PATH, "w", encoding="utf-8") as f:
        json.dump(base_results, f, indent=2, ensure_ascii=False)
    print(f"[compare] base.en 결과 저장: {BASE_TIMESTAMPS_PATH}", file=sys.stderr, flush=True)

    # ── Step 2: medium.en 결과 로드 ──
    with open(MEDIUM_TIMESTAMPS_PATH, "r", encoding="utf-8") as f:
        medium_results = json.load(f)
    print(f"[compare] medium.en 결과 로드: {MEDIUM_TIMESTAMPS_PATH}", file=sys.stderr, flush=True)

    # ── Step 3: 비교 ──
    report = compare(base_results, medium_results)

    output_path = "data/alignment_comparison.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 콘솔 요약
    s = report["summary"]
    print(f"\n{'='*60}")
    print(f"  Word Alignment Quality Comparison")
    print(f"  base.en (CPU) vs medium.en (GPU/CUDA)")
    print(f"{'='*60}")
    print(f"  총 블록: {s['total_blocks']}")
    print(f"  비교 단어 수: {s['total_words_compared']}")
    print(f"  단어 수 불일치 블록: {s['blocks_with_word_count_mismatch']}")
    print(f"  평균 start 차이: {s['avg_start_diff_ms']:.1f} ms")
    print(f"  평균 end 차이: {s['avg_end_diff_ms']:.1f} ms")
    print(f"  최대 차이: {s['max_diff_ms']:.1f} ms ({s['max_diff_block']} / \"{s['max_diff_word']}\")")
    print(f"{'='*60}")

    # 블록별 유의미한 차이 요약
    print(f"\n  블록별 유의미한 차이 (>50ms):")
    for b in report["blocks"]:
        if b.get("significant_diffs", 0) > 0:
            print(f"    [{b['block_id']}] {b['significant_diffs']}건 "
                  f"(avg start: {b['avg_diff_start_ms']}ms, avg end: {b['avg_diff_end_ms']}ms)")

    print(f"\n  상세 리포트: {output_path}")


if __name__ == "__main__":
    main()
