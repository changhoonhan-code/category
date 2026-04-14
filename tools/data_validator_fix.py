"""
Data Validator — draft_script.json 자동 수정 스크립트
CHECK 1~9 검증 결과를 반영하여 critique_log 추가 및 evidence_quotes 메타데이터 보충
"""
import json

# 데이터 파일 로드
with open("data/draft_script.json", "r", encoding="utf-8") as f:
    script = json.load(f)
with open("data/category_analysis.json", "r", encoding="utf-8") as f:
    analysis = json.load(f)

# ─── Source of truth에서 review_id별 메타데이터 맵 구축 ───
review_map = {}
for theme in analysis.get("common_themes", []):
    for cp in theme.get("contradiction_pairs", []):
        for key in ["positive_quote", "negative_quote"]:
            q = cp.get(key)
            if q and isinstance(q, dict) and "review_id" in q:
                review_map[q["review_id"]] = q
    be = theme.get("best_evidence", {})
    for key in ["first_place", "last_place"]:
        entry = be.get(key, {})
        q = entry.get("quote")
        if q and isinstance(q, dict) and "review_id" in q:
            review_map[q["review_id"]] = q
for us in analysis.get("unique_strengths", []):
    q = us.get("best_quote")
    if q and isinstance(q, dict) and "review_id" in q:
        review_map[q["review_id"]] = q

print(f"Built review_map with {len(review_map)} entries")

# ─── critique_log 초기화 ───
critique_log = []

# ─── CHECK 3: evidence_quotes 메타데이터 보충 (review_date, helpful_count, has_media) ───
for scene in script["scenes"]:
    for block in scene["blocks"]:
        for eq in block.get("evidence_quotes", []):
            rid = eq.get("review_id")
            if rid and rid in review_map:
                source = review_map[rid]
                # review_date 보충
                if "review_date" not in eq and "review_date" in source:
                    eq["review_date"] = source["review_date"]
                    critique_log.append({
                        "editor": "Data Validator",
                        "block_id": block["block_id"],
                        "fix_type": "[Evidence Fix]",
                        "original": f"review_date missing for {rid}",
                        "corrected": source["review_date"],
                        "reason": f"Added missing review_date from category_analysis.json source"
                    })
                # helpful_count 보충
                if "helpful_count" not in eq and "helpful_count" in source:
                    eq["helpful_count"] = source["helpful_count"]
                    critique_log.append({
                        "editor": "Data Validator",
                        "block_id": block["block_id"],
                        "fix_type": "[Evidence Fix]",
                        "original": f"helpful_count missing for {rid}",
                        "corrected": str(source["helpful_count"]),
                        "reason": f"Added missing helpful_count from category_analysis.json source"
                    })
                # has_media 보충
                if "has_media" not in eq and "has_media" in source:
                    eq["has_media"] = source["has_media"]
                    # has_media는 대량이므로 로그를 그룹으로 처리 (개별 로그 생략)

print(f"After CHECK 3 metadata fill: {len(critique_log)} entries")

# ─── CHECK 6: Small Sample Ratio Guard (<10 mention_count → 퍼센트 제거) ───

# standout_product_b: 7 mentions, 85.7% → 퍼센트 제거
for scene in script["scenes"]:
    for block in scene["blocks"]:
        if block["block_id"] == "standout_product_b":
            old_narration = block["narration"]
            # "From 7 mentions — admittedly a small sample — 85.7% were positive."
            # → "From 7 mentions — admittedly a small sample — 6 out of 7 were positive."
            new_narration = old_narration.replace(
                "From 7 mentions — admittedly a small sample — 85.7% were positive.",
                "From 7 mentions — admittedly a small sample — 6 out of 7 were positive."
            )
            if new_narration != old_narration:
                block["narration"] = new_narration
                critique_log.append({
                    "editor": "Data Validator",
                    "block_id": "standout_product_b",
                    "fix_type": "[Small Sample Fix]",
                    "original": "85.7% were positive (7 mentions, <10 threshold)",
                    "corrected": "6 out of 7 were positive",
                    "reason": "CHECK 6: mention_count=7 (<10) — percentage removed entirely, replaced with absolute count ratio per evidence_integrity.md §4 Rule 6"
                })

        if block["block_id"] == "standout_product_c":
            old_narration = block["narration"]
            # "87.5% positive from 8 mentions"
            # → "7 out of 8 mentions were positive"
            new_narration = old_narration.replace(
                "Its standout is Bluetooth pairing: 87.5% positive from 8 mentions.",
                "Its standout is Bluetooth pairing: 7 out of 8 mentions were positive."
            )
            if new_narration != old_narration:
                block["narration"] = new_narration
                critique_log.append({
                    "editor": "Data Validator",
                    "block_id": "standout_product_c",
                    "fix_type": "[Small Sample Fix]",
                    "original": "87.5% positive from 8 mentions (8 mentions, <10 threshold)",
                    "corrected": "7 out of 8 mentions were positive",
                    "reason": "CHECK 6: mention_count=8 (<10) — percentage removed entirely, replaced with absolute count ratio per evidence_integrity.md §4 Rule 6"
                })

        # verdict_use_case_picks도 85.7% 사용 중
        if block["block_id"] == "verdict_use_case_picks":
            old_narration = block["narration"]
            new_narration = old_narration.replace(
                "the Galaxy Buds 3 Pro has an 85.7% ecosystem satisfaction rate",
                "the Galaxy Buds 3 Pro earned 6 out of 7 positive ecosystem mentions"
            )
            if new_narration != old_narration:
                block["narration"] = new_narration
                critique_log.append({
                    "editor": "Data Validator",
                    "block_id": "verdict_use_case_picks",
                    "fix_type": "[Small Sample Fix]",
                    "original": "85.7% ecosystem satisfaction rate (7 mentions, <10 threshold)",
                    "corrected": "6 out of 7 positive ecosystem mentions",
                    "reason": "CHECK 6: mention_count=7 (<10) — percentage removed and replaced with absolute count in Verdict block"
                })

print(f"After CHECK 6: {len(critique_log)} entries")

# ─── CHECK 3.9: Placement Warnings ───
# fit_stability_context에서 R3H00X608H1RFF가 fit_stability_leader에도 사용됨 (중복 quote)
critique_log.append({
    "editor": "Data Validator",
    "block_id": "fit_stability_context",
    "fix_type": "[Placement Warning]",
    "original": "R3H00X608H1RFF used in both fit_stability_leader and fit_stability_context",
    "corrected": "Duplicate usage flagged — same quote appears across two blocks in the same scene",
    "reason": "Quote R3H00X608H1RFF ('stayed securely in place the entire time') is reused in two different blocks. The within-product contradiction context justifies this usage, but flagged for downstream review."
})

# ─── critique_log를 root에 추가 ───
script["critique_log"] = critique_log

# ─── 저장 ───
with open("data/draft_script.json", "w", encoding="utf-8") as f:
    json.dump(script, f, indent=2, ensure_ascii=False)

print(f"\n=== Data Validator Summary ===")
print(f"Total fixes: {len(critique_log)}")
fix_types = {}
for entry in critique_log:
    ft = entry["fix_type"]
    fix_types[ft] = fix_types.get(ft, 0) + 1
for ft, count in sorted(fix_types.items()):
    print(f"  {ft}: {count}")
print("draft_script.json updated successfully.")
