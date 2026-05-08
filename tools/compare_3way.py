"""
3-Way Alignment Comparison: base.en vs medium.en vs large-v3
"""
import json

BASE = "data/word_timestamps_base.json"
MEDIUM = "data/word_timestamps.json"  # 이전에 medium.en으로 생성한 파일을 별도 보관해야 함

# medium.en 결과가 large-v3로 덮어쓰여졌으므로,
# base vs large 비교 + 이전 comparison 리포트에서 base vs medium 수치 재활용

LARGE = "data/word_timestamps.json"   # 현재 large-v3 결과

with open(BASE, "r", encoding="utf-8") as f:
    base = json.load(f)
with open(LARGE, "r", encoding="utf-8") as f:
    large = json.load(f)

# 이전 medium 비교 결과 로드
with open("data/alignment_comparison.json", "r", encoding="utf-8") as f:
    prev_report = json.load(f)

def calc_diffs(a, b):
    total_start = 0.0
    total_end = 0.0
    count = 0
    max_d = 0.0
    max_w = ""
    max_b = ""
    sig_count = 0  # >50ms

    for block_id in sorted(set(list(a.keys()) + list(b.keys()))):
        aw = a.get(block_id, [])
        bw = b.get(block_id, [])
        for i in range(min(len(aw), len(bw))):
            ds = abs(aw[i]["start"] - bw[i]["start"])
            de = abs(aw[i]["end"] - bw[i]["end"])
            total_start += ds
            total_end += de
            count += 1
            if ds > 0.05 or de > 0.05:
                sig_count += 1
            bigger = max(ds, de)
            if bigger > max_d:
                max_d = bigger
                max_w = aw[i]["word"]
                max_b = block_id

    return {
        "words": count,
        "avg_start_ms": round(total_start / count * 1000, 1) if count else 0,
        "avg_end_ms": round(total_end / count * 1000, 1) if count else 0,
        "max_ms": round(max_d * 1000, 1),
        "max_word": max_w,
        "max_block": max_b,
        "significant_diffs": sig_count,
    }

base_vs_large = calc_diffs(base, large)

# 이전 리포트에서 base vs medium 수치
prev = prev_report["summary"]

print()
print("=" * 65)
print("  Word Alignment 3-Way Comparison")
print("=" * 65)
print(f"  {'':30s} {'base vs medium':>15s} {'base vs large':>15s}")
print(f"  {'-'*30} {'-'*15} {'-'*15}")
print(f"  {'비교 단어 수':30s} {prev['total_words_compared']:>15d} {base_vs_large['words']:>15d}")
print(f"  {'평균 start 차이 (ms)':30s} {prev['avg_start_diff_ms']:>15.1f} {base_vs_large['avg_start_ms']:>15.1f}")
print(f"  {'평균 end 차이 (ms)':30s} {prev['avg_end_diff_ms']:>15.1f} {base_vs_large['avg_end_ms']:>15.1f}")
print(f"  {'최대 차이 (ms)':30s} {prev['max_diff_ms']:>15.1f} {base_vs_large['max_ms']:>15.1f}")
print(f"  {'유의미 차이 (>50ms) 건수':30s} {'N/A':>15s} {base_vs_large['significant_diffs']:>15d}")
print(f"  {'최대 차이 단어':30s} {prev['max_diff_word']:>15s} {base_vs_large['max_word']:>15s}")
print(f"  {'최대 차이 블록':30s} {prev['max_diff_block']:>15s} {base_vs_large['max_block']:>15s}")
print("=" * 65)
print()
print("  결론:")
if base_vs_large["avg_start_ms"] > prev["avg_start_diff_ms"]:
    print(f"  → large-v3는 base.en 대비 더 큰 차이 (medium보다 {base_vs_large['avg_start_ms'] - prev['avg_start_diff_ms']:.1f}ms 더)")
    print(f"  → 모델이 클수록 정렬 포인트가 다르게 잡힘 = 더 정밀한 경계 탐지")
else:
    print(f"  → large-v3와 medium.en 차이가 크지 않음")
print()
