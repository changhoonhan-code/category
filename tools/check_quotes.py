"""summary.json의 evidence_quotes 품질 분석 스크립트

사용법:
    python tools/check_quotes.py
"""
import json
import os
import pandas as pd
from collections import Counter
import statistics

from config import DATAS_DIR

# summary.json 로드
with open(os.path.join(DATAS_DIR, "summary.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

# CSV 로드
df = pd.read_csv(os.path.join(DATAS_DIR, "buying_guide_extracted.csv"))

print("=" * 60)
print("evidence_quotes 품질 진단 리포트")
print("=" * 60)

# 1. 테마별 인용구 수
print("\n### 1. 테마별 인용구 수")
for t in data["themes"]:
    eq_count = len(t.get("evidence_quotes", []))
    print(f"  {t['theme_name']}: {eq_count}개 (전체 {t['mention_count']}개 리뷰 중)")

# 2. sentiment 분포 vs 인용구 sentiment
print("\n### 2. sentiment 불일치 분석")
for t in data["themes"]:
    dist = t["sentiment_distribution"]
    dominant = max(dist, key=dist.get)
    eq_sentiments = [e["sentiment"].lower() for e in t.get("evidence_quotes", [])]
    dominant_in_eq = eq_sentiments.count(dominant)
    print(f"  {t['theme_name']}: 주력={dominant}({dist[dominant]}건), 인용구 중 {dominant} = {dominant_in_eq}/{len(eq_sentiments)}")

# 3. 리뷰 중복 검사
print("\n### 3. 교차 테마 review_id 중복")
all_eq_rids = []
for t in data["themes"]:
    rids = [e["review_id"] for e in t.get("evidence_quotes", [])]
    all_eq_rids.extend(rids)
dup_rids = {k: v for k, v in Counter(all_eq_rids).items() if v > 1}
if dup_rids:
    print(f"  중복 review_id {len(dup_rids)}개 발견:")
    for rid, cnt in list(dup_rids.items())[:10]:
        themes_with_rid = [t["theme_name"] for t in data["themes"] if any(e["review_id"] == rid for e in t.get("evidence_quotes", []))]
        print(f"    {rid} ({cnt}회): {themes_with_rid}")
else:
    print("  없음")

# 4. 인용구가 테마와 관련 없는 사례
print("\n### 4. 첫 번째 테마 인용구 vs core_aspect (관련성 점검)")
first_theme = data["themes"][0]
theme_name = first_theme["theme_name"]
print(f"  테마: {theme_name}")
theme_aspects = df[df["canonical_theme"] == theme_name]["core_aspect"].value_counts().head(5)
print(f"  주요 core_aspect: {dict(theme_aspects)}")
for eq in first_theme.get("evidence_quotes", []):
    rid = eq["review_id"]
    matching = df[(df["review_id"] == rid) & (df["canonical_theme"] == theme_name)]
    aspects = matching["core_aspect"].tolist() if not matching.empty else ["N/A"]
    print(f"  Quote: \"{eq['text'][:60]}...\"")
    print(f"    -> review_id={rid}, aspect={aspects}, sentiment={eq['sentiment']}")

# 5. 미디어 보유 인용구 비율
print("\n### 5. 미디어 보유 인용구 비율")
total_eq = sum(len(t.get("evidence_quotes", [])) for t in data["themes"])
media_eq = sum(1 for t in data["themes"] for eq in t.get("evidence_quotes", []) if eq.get("has_media"))
print(f"  전체 인용구: {total_eq}개, 미디어 보유: {media_eq}개 ({media_eq/total_eq*100:.1f}%)")

# 6. 인용구 길이 분포
print("\n### 6. 인용구 텍스트 길이 분포")
eq_lens = [len(eq["text"]) for t in data["themes"] for eq in t.get("evidence_quotes", [])]
print(f"  평균: {statistics.mean(eq_lens):.1f}자, 중위: {statistics.median(eq_lens):.1f}자")
print(f"  최소: {min(eq_lens)}자, 최대: {max(eq_lens)}자")
short = sum(1 for l in eq_lens if l < 30)
print(f"  30자 미만(약한 인용): {short}개")

# 7. 비영어 인용구 감지
print("\n### 7. 비영어 인용구 감지")
non_eng = []
for t in data["themes"]:
    for eq in t.get("evidence_quotes", []):
        txt = eq["text"]
        ascii_ratio = sum(1 for c in txt if ord(c) < 128) / max(len(txt), 1)
        if ascii_ratio < 0.8:
            non_eng.append((t["theme_name"], txt[:60]))
if non_eng:
    print(f"  비영어 인용구 {len(non_eng)}개 발견:")
    for tn, txt in non_eng:
        print(f"    [{tn}] \"{txt}...\"")
else:
    print("  없음")
