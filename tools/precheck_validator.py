"""
Data Validator Phase 1 -- 기계적 CHECK 자동 수행 도구.

draft_script.json을 category_validator.json과 대조하여
기계적으로 검증/수정 가능한 항목을 자동 처리한다.
LLM 판단이 필요한 항목은 플래그만 기록하여 Phase 2에 전달한다.

수행 CHECK:
  CHECK 3p: Evidence Quote Integrity - 기계적 부분
    - highlight_phrase substring 검증
    - star_rating 매칭
    - review_id 존재 확인
    - highlight_phrase 길이 검증 (12 word ceiling)
  CHECK 4: Theme Coverage (scene vs excluded_themes set 비교)
  CHECK 6p: Small Sample Ratio Guard - 기계적 부분
    - mention_count < 10: 퍼센트 감지 -> 플래그
    - mention_count < 15: count-first 위반 감지 -> 플래그
  CHECK 10: Product Focus Ratio - 나레이션 포커스 제품 vs evidence_quotes 배분 검증
    - 나레이션에서 주요 제품명 감지
    - 해당 제품의 인용문 비율이 60% 미만이면 플래그

Phase 2 LLM 전담 (이 도구에서는 미수행):
  CHECK 1: Source Number Cross-Reference -- narration 숫자의 문맥 판단 필요
  CHECK 2: Numerical Consistency -- 동일 데이터 포인트의 의미적 매칭 필요

Usage:
    python tools/precheck_validator.py
    python tools/precheck_validator.py --input data/draft_script.json --validator data/category_validator.json

Output:
    - data/draft_script.json (기계적 수정 적용 + critique_log 추가)
    - tmp/precheck_report.json (Phase 2 LLM에게 전달할 플래그 리스트)
"""
import argparse
import json
import os
import re
import sys

from config import DATAS_DIR, TMP_DIR

# ── 기본 경로 ──────────────────────────────────────────────────────────────
DEFAULT_SCRIPT = os.path.join(DATAS_DIR, "draft_script.json")
DEFAULT_VALIDATOR = os.path.join(DATAS_DIR, "category_validator.json")
DEFAULT_REPORT = os.path.join(TMP_DIR, "precheck_report.json")




# ═══════════════════════════════════════════════════════════════════════════
# Source of Truth 데이터 구축
# ═══════════════════════════════════════════════════════════════════════════

def build_product_data_map(validator: dict) -> dict:
    """제품별 숫자 데이터 맵 구축.

    Returns:
        { product_id: { field_name: value, ... } }
    """
    product_map = {}
    for p in validator.get("products", []):
        pid = p["product_id"]
        product_map[pid] = {
            "product_name": p.get("product_name", ""),
            "all_time_rating_avg": p.get("all_time_rating_avg"),
            "all_time_rating_count": p.get("all_time_rating_count"),
            "recent_review_rating_avg": p.get("recent_review_rating_avg"),
            "recent_review_count": p.get("recent_review_count"),
            "population_gap": p.get("population_gap"),
            "reviews_analyzed_count": p.get("reviews_analyzed_count"),
            "sold_last_month": p.get("sold_last_month"),
        }
    return product_map


def build_theme_rankings_map(validator: dict) -> dict:
    """테마별 제품 랭킹 데이터 맵 구축.

    Returns:
        { theme_name: { product_id: { mention_count, positive_ratio, ... } } }
    """
    theme_map = {}
    for theme in validator.get("common_themes", []):
        tname = theme["theme_name"]
        theme_map[tname] = {}
        for r in theme.get("rankings", []):
            theme_map[tname][r["product_id"]] = {
                "mention_count": r.get("mention_count"),
                "positive_count": r.get("positive_count"),
                "negative_count": r.get("negative_count"),
                "positive_ratio": r.get("positive_ratio"),
            }
    return theme_map


def build_review_map(validator: dict) -> dict:
    """review_id 기반 인용구 소스 맵 구축.

    동일 review_id가 여러 contradiction_pair에 서로 다른 quote text로
    등장할 수 있으므로, 각 review_id에 대해 모든 소스 인용구를 리스트로 보존한다.

    Returns:
        { review_id: [ { text, star_rating, review_date, product_id, ... }, ... ] }
    """
    review_map = {}

    def _add_quote(q):
        """인용구를 review_map에 추가. 동일 text 중복은 방지."""
        if not (q and isinstance(q, dict) and "review_id" in q):
            return
        rid = q["review_id"]
        if rid not in review_map:
            review_map[rid] = []
        # 동일 text가 이미 있으면 스킵 (best_evidence 등에서 중복 등록 방지)
        if not any(existing.get("text") == q.get("text") for existing in review_map[rid]):
            review_map[rid].append(q)

    for theme in validator.get("common_themes", []):
        # contradiction_pairs에서 인용구 수집 (valid product_id 보유 -- 우선 등록)
        for cp in theme.get("contradiction_pairs", []):
            for key in ["positive_quote", "negative_quote"]:
                _add_quote(cp.get(key))

        # best_evidence에서 인용구 수집 (product_id: null -- 중복 text면 스킵됨)
        be = theme.get("best_evidence", {})
        for key in ["first_place", "last_place"]:
            entry = be.get(key, {})
            _add_quote(entry.get("quote"))

    # unique_strengths에서 인용구 수집
    for us in validator.get("unique_strengths", []):
        _add_quote(us.get("best_quote"))

    # 보충 인용구 등 category_writer.json이 있다면 추가로 읽어서 채운다 (false positive 방지)
    writer_path = os.path.join(DATAS_DIR, "category_writer.json")
    if os.path.exists(writer_path):
        try:
            with open(writer_path, "r", encoding="utf-8") as f:
                writer_data = json.load(f)
            for theme in writer_data.get("common_themes", []):
                for q in theme.get("supplementary_quotes", []):
                    _add_quote(q)
        except Exception as e:
            print(f"[precheck] Failed to read category_writer.json: {e}", file=sys.stderr)

    return review_map


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 구현
# ═══════════════════════════════════════════════════════════════════════════

def check_3_mechanical(script: dict, review_map: dict) -> tuple[int, list, list]:
    """CHECK 3 기계적 부분: highlight_phrase/star_rating/review_id 검증.

    review_map은 { review_id: [quote, ...] } 형태.
    동일 review_id에 여러 quote가 있을 수 있으므로 highlight_phrase 매칭 시
    모든 소스 텍스트를 순회한다.

    Returns:
        (auto_fixed_count, critique_entries, llm_flags)
    """
    fixes = []
    flags = []
    auto_fixed = 0

    for scene in script["scenes"]:
        for block in scene["blocks"]:
            for eq in block.get("evidence_quotes", []):
                rid = eq.get("review_id")
                if not rid:
                    # review_id 자체가 없으면 플래그
                    flags.append({
                        "check": "CHECK 3",
                        "block_id": block["block_id"],
                        "issue": "missing_review_id",
                        "detail": f"evidence_quote에 review_id가 없음",
                    })
                    continue

                if rid not in review_map:
                    # Source of Truth에 없는 review_id -> 플래그
                    flags.append({
                        "check": "CHECK 3",
                        "block_id": block["block_id"],
                        "issue": "unknown_review_id",
                        "detail": f"review_id '{rid}'가 category_validator.json에 없음",
                    })
                    continue

                sources = review_map[rid]

                # ── highlight_phrase substring 검증 ──
                # 동일 review_id에 여러 소스 텍스트가 있을 수 있으므로
                # 하나라도 매치되면 통과 (false positive 방지)
                hp = eq.get("highlight_phrase", "")
                matched_source = None
                if hp:
                    for s in sources:
                        source_text = s.get("text", "")
                        if source_text and source_text.find(hp) != -1:
                            matched_source = s
                            break

                if hp and matched_source is None:
                    # 모든 소스 텍스트에서 highlight_phrase를 찾지 못함
                    all_previews = "; ".join(
                        s.get("text", "")[:100] for s in sources
                    )
                    fixes.append({
                        "editor": "Data Validator",
                        "block_id": block["block_id"],
                        "fix_type": "[Evidence Fix]",
                        "original": hp,
                        "corrected": f"(FLAGGED: not found in source text for {rid})",
                        "reason": f"CHECK 3: highlight_phrase '{hp}' is not a verbatim substring of source text",
                    })
                    flags.append({
                        "check": "CHECK 3",
                        "block_id": block["block_id"],
                        "issue": "highlight_phrase_mismatch",
                        "detail": f"review_id={rid}, phrase='{hp}' not found in source text",
                        "source_text_preview": all_previews[:200],
                    })

                # highlight_phrase 길이 검증 (12-word ceiling)
                if hp:
                    word_count = len(hp.split())
                    if word_count > 12:
                        fixes.append({
                            "editor": "Data Validator",
                            "block_id": block["block_id"],
                            "fix_type": "[Evidence Fix]",
                            "original": hp,
                            "corrected": f"(FLAGGED: {word_count} words, exceeds 12-word ceiling)",
                            "reason": f"CHECK 3: highlight_phrase exceeds 12-word ceiling ({word_count} words)",
                        })
                        flags.append({
                            "check": "CHECK 3",
                            "block_id": block["block_id"],
                            "issue": "highlight_phrase_too_long",
                            "detail": f"'{hp}' is {word_count} words (ceiling: 12)",
                        })

                # 메타데이터 검증용 소스 선택:
                # highlight_phrase가 매치된 소스 우선, 없으면 첫 번째 소스 사용
                source = matched_source if matched_source else sources[0]

                # star_rating 매칭
                if "star_rating" in eq and "star_rating" in source:
                    if eq["star_rating"] != source["star_rating"]:
                        old_val = eq["star_rating"]
                        eq["star_rating"] = source["star_rating"]
                        auto_fixed += 1
                        fixes.append({
                            "editor": "Data Validator",
                            "block_id": block["block_id"],
                            "fix_type": "[Evidence Fix]",
                            "original": f"star_rating={old_val}",
                            "corrected": f"star_rating={source['star_rating']}",
                            "reason": f"CHECK 3: star_rating mismatch for {rid} -- corrected to source value",
                        })

                # product_id 매칭 (null 소스는 auto-fix 대상에서 제외)
                if "product_id" in eq and "product_id" in source:
                    source_pid = source["product_id"]
                    if source_pid is not None and eq["product_id"] != source_pid:
                        old_pid = eq["product_id"]
                        eq["product_id"] = source_pid
                        auto_fixed += 1
                        fixes.append({
                            "editor": "Data Validator",
                            "block_id": block["block_id"],
                            "fix_type": "[Product ID Fix]",
                            "original": f"{rid} product_id: {old_pid}",
                            "corrected": f"{rid} product_id should be: {source_pid}",
                            "reason": f"[Product ID Fix]: Quote {rid} belongs to {source_pid} per source data, but evidence_quotes lists {old_pid}. Corrected automatically.",
                        })

                # review_date 보충/검증
                if "review_date" in source:
                    if "review_date" not in eq:
                        eq["review_date"] = source["review_date"]
                        auto_fixed += 1
                        fixes.append({
                            "editor": "Data Validator",
                            "block_id": block["block_id"],
                            "fix_type": "[Evidence Fix]",
                            "original": f"review_date missing for {rid}",
                            "corrected": source["review_date"],
                            "reason": "CHECK 3: Added missing review_date from source",
                        })
                    elif eq["review_date"] != source["review_date"]:
                        old_val = eq["review_date"]
                        eq["review_date"] = source["review_date"]
                        auto_fixed += 1
                        fixes.append({
                            "editor": "Data Validator",
                            "block_id": block["block_id"],
                            "fix_type": "[Evidence Fix]",
                            "original": f"review_date={old_val}",
                            "corrected": source["review_date"],
                            "reason": f"CHECK 3: review_date mismatch for {rid} -- corrected",
                        })

                # helpful_count 보충
                if "helpful_count" in source and "helpful_count" not in eq:
                    eq["helpful_count"] = source["helpful_count"]
                    auto_fixed += 1
                    # 대량 보충이므로 개별 로그 생략

                # has_media 보충
                if "has_media" in source and "has_media" not in eq:
                    eq["has_media"] = source["has_media"]
                    auto_fixed += 1

    return auto_fixed, fixes, flags


def check_4_theme_coverage(script: dict, validator: dict) -> tuple[list, list]:
    """CHECK 4: 테마 커버리지 검증.

    Returns:
        (critique_entries, llm_flags)
    """
    fixes = []
    flags = []

    # Source of Truth의 모든 테마
    all_themes = {t["theme_name"] for t in validator.get("common_themes", [])}

    # 스크립트에 포함된 테마 (scene_id에서 추출)
    script_scene_ids = {s["scene_id"] for s in script.get("scenes", [])}

    # excluded_themes (dict 배열 — theme_name 필드 추출)
    raw_excluded = script.get("excluded_themes", [])
    if raw_excluded and isinstance(raw_excluded[0], dict):
        excluded = {et.get("theme_name", "") for et in raw_excluded}
    else:
        excluded = set(raw_excluded)

    # scene_id 'theme_XXX' 패턴에서 테마명 추출은 어려우므로
    # 대신: Source의 테마 중 scene에도 없고 excluded에도 없는 것을 감지
    # (테마명 → scene_id 매핑이 정확하지 않으므로 플래그만)
    covered_or_excluded = excluded.copy()

    # scene_id에서 'theme_' 접두사를 가진 것들 수집
    theme_scene_ids = {sid for sid in script_scene_ids if sid.startswith("theme_")}

    # 커버리지 확인: theme_scene이 하나도 없으면 경고
    if not theme_scene_ids:
        flags.append({
            "check": "CHECK 4",
            "block_id": "global",
            "issue": "no_theme_scenes",
            "detail": f"No theme_* scenes found. All themes: {sorted(all_themes)}",
        })
    elif len(theme_scene_ids) + len(excluded) < len(all_themes):
        # 테마 수보다 (씬 + 제외) 합이 적으면 누락 가능
        flags.append({
            "check": "CHECK 4",
            "block_id": "global",
            "issue": "possible_theme_gap",
            "detail": (
                f"{len(all_themes)} themes in source, "
                f"{len(theme_scene_ids)} theme scenes + {len(excluded)} excluded = "
                f"{len(theme_scene_ids) + len(excluded)}. "
                f"Possible gap if themes were silently dropped."
            ),
        })

    return fixes, flags





def check_6_small_sample(script: dict, theme_rankings: dict) -> tuple[int, list, list]:
    """CHECK 6 기계적 부분: mention_count < 10/15인 테마의 퍼센트 사용 감지.

    현재 scene의 테마 랭킹만 참조하여 스코프를 제한한다.
    다른 테마의 small sample 데이터가 노이즈로 섞이는 것을 방지.

    Returns:
        (auto_fixed_count, critique_entries, llm_flags)
    """
    fixes = []
    flags = []
    auto_fixed = 0

    # 퍼센트 패턴 (예: "85.7%", "100%", "zero percent")
    pct_pattern = re.compile(r'\d+\.?\d*\s*%|zero\s+percent', re.IGNORECASE)

    # scene_id -> theme_name 역매핑 구축 (theme_rankings 키에서 변환)
    scene_to_theme = {}
    for tname in theme_rankings:
        sid = "theme_" + tname.lower().replace(" ", "_").replace("-", "_")
        scene_to_theme[sid] = tname

    for scene in script["scenes"]:
        sid = scene["scene_id"]
        if not sid.startswith("theme_"):
            continue

        # 현재 scene의 테마 이름 확인
        current_theme = scene_to_theme.get(sid)
        if not current_theme or current_theme not in theme_rankings:
            continue

        # 현재 테마의 랭킹에서 small sample 제품만 수집 (블록 루프 바깥)
        current_rankings = theme_rankings[current_theme]
        small_sample_products = set()
        for pid, data in current_rankings.items():
            mc = data.get("mention_count", 999)
            if mc < 15:
                small_sample_products.add((current_theme, pid, mc))

        if not small_sample_products:
            continue  # 이 테마에는 small sample 제품 없음 -> 플래그 불필요

        for block in scene["blocks"]:
            bid = block["block_id"]
            narration = block.get("narration", "")

            # narration에 퍼센트가 있는지 확인
            pct_matches = pct_pattern.findall(narration)
            if pct_matches:
                flags.append({
                    "check": "CHECK 6",
                    "block_id": bid,
                    "issue": "percentage_with_possible_small_sample",
                    "detail": (
                        f"Percentages found: {pct_matches}. "
                        f"Small sample products (<15 mentions) in '{current_theme}': "
                        f"{[(t,p,m) for t,p,m in small_sample_products]}"
                    ),
                    "narration_excerpt": narration[:150],
                })

    return auto_fixed, fixes, flags


def check_10_product_focus(script: dict, product_map: dict) -> tuple[list, list]:
    """CHECK 10: 블록별 나레이션 포커스 제품 vs evidence_quotes product_id 배분 검증.

    나레이션에서 가장 많이 언급되는 제품이 포커스 제품이다.
    해당 제품의 인용문이 전체의 60% 미만이면 Placement Warning 플래그.

    Returns:
        (critique_entries, llm_flags)
    """
    fixes = []
    flags = []

    # 제품명 -> product_id 매핑 구축
    name_to_pid = {}
    for pid, pdata in product_map.items():
        pname = pdata.get("product_name", "")
        if pname:
            name_to_pid[pname.lower()] = pid
            # 브랜드명만으로도 매칭 (예: "Apple", "Samsung", "Beats")
            brand = pname.split()[0].lower()
            # 브랜드명이 너무 짧으면 skip (오탐 방지)
            if len(brand) >= 4:
                name_to_pid[brand] = pid

    for scene in script["scenes"]:
        for block in scene["blocks"]:
            eqs = block.get("evidence_quotes", [])
            if len(eqs) < 3:
                # 인용문이 3개 미만이면 비율 검증 무의미 (Hook, Overview, Verdict 등)
                continue

            bid = block["block_id"]

            # _context 블록은 모든 제품 혼합이 정상 (Quote Curator §4: "Mix supplementary quotes across all products")
            if bid.endswith("_context"):
                continue

            narration = block.get("narration", "").lower()

            # 나레이션에서 각 제품 언급 횟수 카운트
            mention_counts = {}
            for name, pid in name_to_pid.items():
                count = narration.count(name)
                if count > 0:
                    mention_counts[pid] = mention_counts.get(pid, 0) + count

            if not mention_counts:
                continue

            # 가장 많이 언급된 제품 = 포커스 제품
            focal_pid = max(mention_counts, key=mention_counts.get)

            # 동률이면 포커스 판정 불확실 -> skip
            counts_sorted = sorted(mention_counts.values(), reverse=True)
            if len(counts_sorted) >= 2 and counts_sorted[0] == counts_sorted[1]:
                continue

            # evidence_quotes에서 포커스 제품 비율 계산
            total_quotes = len(eqs)
            focal_quotes = sum(
                1 for eq in eqs
                if eq.get("product_id") == focal_pid
            )
            # null product_id는 전체 카운트에서 제외
            non_null_quotes = sum(1 for eq in eqs if eq.get("product_id") is not None)
            if non_null_quotes < 3:
                continue

            focal_ratio = focal_quotes / non_null_quotes
            threshold = 0.6

            if focal_ratio < threshold:
                focal_name = product_map.get(focal_pid, {}).get("product_name", focal_pid)
                # product_id별 인용문 수 집계
                pid_dist = {}
                for eq in eqs:
                    p = eq.get("product_id", "null")
                    pid_dist[p] = pid_dist.get(p, 0) + 1

                flags.append({
                    "check": "CHECK 10",
                    "block_id": bid,
                    "issue": "product_focus_violation",
                    "detail": (
                        f"Narration focuses on '{focal_name}' ({focal_pid}), "
                        f"but only {focal_quotes}/{non_null_quotes} quotes "
                        f"({focal_ratio:.0%}) belong to it. "
                        f"Required: >= 60%. "
                        f"Quote distribution: {pid_dist}"
                    ),
                })

    return fixes, flags


# ═══════════════════════════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens Data Validator Phase 1: 기계적 CHECK 자동 수행"
    )
    parser.add_argument(
        "--input", default=DEFAULT_SCRIPT,
        help=f"검증 대상 draft_script.json (기본: {DEFAULT_SCRIPT})"
    )
    parser.add_argument(
        "--validator", default=DEFAULT_VALIDATOR,
        help=f"Source of Truth (기본: {DEFAULT_VALIDATOR})"
    )
    parser.add_argument(
        "--report", default=DEFAULT_REPORT,
        help=f"Phase 2 플래그 리포트 출력 경로 (기본: {DEFAULT_REPORT})"
    )
    args = parser.parse_args()

    # ── 입력 파일 확인 ──
    for path, label in [(args.input, "draft_script"), (args.validator, "category_validator")]:
        if not os.path.exists(path):
            print(json.dumps({"error": f"File not found: {path} ({label})"}))
            sys.exit(1)

    # ── 데이터 로드 ──
    with open(args.input, "r", encoding="utf-8") as f:
        script = json.load(f)
    with open(args.validator, "r", encoding="utf-8") as f:
        validator = json.load(f)

    # ── Source of Truth 맵 구축 ──
    product_map = build_product_data_map(validator)
    theme_rankings = build_theme_rankings_map(validator)
    review_map = build_review_map(validator)

    print(f"[precheck] Source maps: {len(product_map)} products, "
          f"{len(theme_rankings)} themes, {len(review_map)} reviews", file=sys.stderr)

    # ── critique_log 초기화 ──
    if "critique_log" not in script:
        script["critique_log"] = []
        print("[precheck] critique_log 초기화 완료", file=sys.stderr)

    all_fixes = []
    all_flags = []
    total_auto_fixed = 0

    # ── CHECK 3 (기계적) ──
    c3_fixed, c3_fixes, c3_flags = check_3_mechanical(script, review_map)
    total_auto_fixed += c3_fixed
    all_fixes.extend(c3_fixes)
    all_flags.extend(c3_flags)
    print(f"[precheck] CHECK 3: {c3_fixed} auto-fixed, {len(c3_fixes)} logged, {len(c3_flags)} flagged", file=sys.stderr)

    # ── CHECK 4 (테마 커버리지) ──
    c4_fixes, c4_flags = check_4_theme_coverage(script, validator)
    all_fixes.extend(c4_fixes)
    all_flags.extend(c4_flags)
    print(f"[precheck] CHECK 4: {len(c4_flags)} flags", file=sys.stderr)



    # ── CHECK 6 (small sample) ──
    c6_fixed, c6_fixes, c6_flags = check_6_small_sample(script, theme_rankings)
    total_auto_fixed += c6_fixed
    all_fixes.extend(c6_fixes)
    all_flags.extend(c6_flags)
    print(f"[precheck] CHECK 6: {c6_fixed} auto-fixed, {len(c6_flags)} flagged", file=sys.stderr)

    # ── CHECK 10 (Product Focus Ratio) ──
    c10_fixes, c10_flags = check_10_product_focus(script, product_map)
    all_fixes.extend(c10_fixes)
    all_flags.extend(c10_flags)
    print(f"[precheck] CHECK 10: {len(c10_flags)} product focus violations", file=sys.stderr)

    # ── critique_log에 기계적 수정 로그 추가 ──
    script["critique_log"].extend(all_fixes)

    # ── draft_script.json 저장 ──
    with open(args.input, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    # ── Phase 2 플래그 리포트 저장 ──
    os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
    report = {
        "auto_fixed": total_auto_fixed,
        "critique_log_entries": len(all_fixes),
        "flags_for_llm": all_flags,
        "coverage_ok": len(c4_flags) == 0,
    }
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # ── 실행 요약 ──
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  Data Validator Phase 1 (Pre-check) Complete", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    print(f"  Auto-fixed:        {total_auto_fixed}", file=sys.stderr)
    print(f"  Critique log adds: {len(all_fixes)}", file=sys.stderr)
    print(f"  Flags for LLM:     {len(all_flags)}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    # Machine-parseable JSON
    print(json.dumps({
        "status": "success",
        "auto_fixed": total_auto_fixed,
        "critique_log_entries": len(all_fixes),
        "flags_for_llm": len(all_flags),
        "report": args.report,
    }))


if __name__ == "__main__":
    main()
