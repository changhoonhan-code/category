"""
Filter category data for agent-specific profiles — 무거운 quote 본문과
불필요 필드를 제거하여 에이전트별 토큰 최적화 축소본을 생성.

Usage:
    python tools/filter_category.py --profile blueprint
    python tools/filter_category.py --profile screen --input data/category_candidates.json --output data/category_screen.json
    python tools/filter_category.py --profile intelligence --input data/category_screened.json --output data/category_intelligence.json
    python tools/filter_category.py --profile writer
    python tools/filter_category.py --profile writer --outline data/comparison_outline.json
    python tools/filter_category.py --profile validator

Profiles: blueprint, screen, intelligence, writer, validator
"""
import argparse
import json
import os
import sys


# ── 기본 경로 설정 ──────────────────────────────────────────────────────────
# cross_product_analyzer.py와 동일한 경로 패턴 사용
DEFAULT_INPUT = os.path.join("data", "category_analysis.json")


# ── Profile Definitions ─────────────────────────────────────────────────────
# 각 프로파일은 category_analysis.json에서 어떤 필드를 유지/제거할지 정의.
# 필터 함수(filter_for_*)가 프로파일별 축소 로직을 구현.

PROFILES = {
    "blueprint": {
        "description": "Blueprint Designer 전략 결정용 축소본 — quote 메타 필드 제거, 핵심 데이터 보존",
        "filter_fn": "filter_for_blueprint",
        "output_suffix": "blueprint",
    },
    "screen": {
        "description": "Data Screener Agent 판단용 축소본 — quote 본문 제거, ratio_gap/mention_count 통계만 보존",
        "filter_fn": "filter_for_screen",
        "output_suffix": "screen",
    },
    "intelligence": {
        "description": "Category Analyst Agent 정성 분석용 축소본 — quote text 보존, 불필요 메타 제거",
        "filter_fn": "filter_for_intelligence",
        "output_suffix": "intelligence",
    },
    "writer": {
        "description": "Writer Agent 초안 작성용 축소본 — assigned_themes만 필터링, quote text 보존",
        "filter_fn": "filter_for_writer",
        "output_suffix": "writer",
    },
    "validator": {
        "description": "Data Validator 검증용 축소본 — 모든 테마 유지, 수치와 필수 메타데이터 전부 보존, 불필요 본문 제거",
        "filter_fn": "filter_for_validator",
        "output_suffix": "validator",
    },
}


# ── 범용 Quote / Contradiction Pair 필터 ─────────────────────────────────────
# 프로파일별로 보존할 필드만 다르고 구조는 동일하므로, keep_fields 기반 범용 함수 사용.
# pipeline_contracts.json에서 로드.
from config import contracts

_filter_cfg = contracts()["filter_profiles"]
QUOTE_DEFAULTS = _filter_cfg["quote_defaults"]
QUOTE_KEEP_FIELDS = _filter_cfg["quote_keep_fields"]


def _filter_quote(quote: dict, profile: str) -> dict:
    """
    범용 quote 축소 함수.
    QUOTE_KEEP_FIELDS[profile]에 정의된 필드만 보존하고 나머지는 제거.
    QUOTE_DEFAULTS에 등록된 필드는 원본에 없을 때 기본값 적용.
    """
    if quote is None:
        return None
    keep = QUOTE_KEEP_FIELDS[profile]
    result = {}
    for field in keep:
        if field in QUOTE_DEFAULTS:
            result[field] = quote.get(field, QUOTE_DEFAULTS[field])
        else:
            result[field] = quote.get(field)
    return result


def _filter_contradiction_pair(pair: dict, profile: str) -> dict:
    """
    범용 contradiction_pair 축소 함수.
    type + product_id/product_ids 라우팅 + quote 축소 + resolution_hypothesis 보존.
    """
    result = {"type": pair.get("type")}
    # within_product이면 product_id, cross_product이면 product_ids
    if pair.get("type") == "within_product":
        result["product_id"] = pair.get("product_id")
    else:
        result["product_ids"] = pair.get("product_ids")
    result["positive_quote"] = _filter_quote(pair.get("positive_quote"), profile)
    result["negative_quote"] = _filter_quote(pair.get("negative_quote"), profile)
    result["resolution_hypothesis"] = pair.get("resolution_hypothesis")
    return result


# ── Blueprint Designer Profile ──────────────────────────────────────────────

def filter_for_blueprint(data: dict) -> dict:
    """
    category_analysis.json -> category_blueprint.json 축소본 생성.

    포함 필드:
    - product_count (동적 블록 캡 결정)
    - products[]: product_id, product_name, sold_last_month, all_time_rating_avg,
      all_time_rating_count, recent_review_rating_avg, recent_review_count,
      population_gap, reviews_analyzed_count, trap_candidate
    - common_themes[]: theme_name, category_pattern, category_pattern_type,
      rankings (전체 수치), contradiction_pairs (축소된 quote),
      best_evidence (축소된 quote)
    - unique_strengths[]: 전체 (Standout 매핑에 필요)
    - category_intelligence: 전체 (Verdict 전략에 필요)

    제거 필드:
    - category_name (video_question에서 사용 금지이므로 유혹 제거)
    - dataset_snapshot, previous_snapshot, delta (스냅샷 메타)
    - products[].product_category, summary_path, recent_period_text, recent_days
    - contradiction_pairs 내 quote의 sentiment, review_date, selection_reason,
      has_media, media_info
    - best_evidence 내 quote의 동일한 불필요 메타 필드
    - unique_strengths[].best_quote의 불필요 메타 필드
    """
    result = {}

    # ── product_count (동적 블록 캡 결정에 필수) ──
    result["product_count"] = data.get("product_count")

    # ── products 축소: 핵심 메타만 유지 ──
    result["products"] = []
    for p in data.get("products", []):
        result["products"].append({
            "product_id": p.get("product_id"),
            "product_name": p.get("product_name"),
            "sold_last_month": p.get("sold_last_month"),
            "all_time_rating_avg": p.get("all_time_rating_avg"),
            "all_time_rating_count": p.get("all_time_rating_count"),
            "recent_review_rating_avg": p.get("recent_review_rating_avg"),
            "recent_review_count": p.get("recent_review_count"),
            "population_gap": p.get("population_gap"),
            "reviews_analyzed_count": p.get("reviews_analyzed_count"),
            "trap_candidate": p.get("trap_candidate"),  # 전체 유지 (is_trap 판단)
        })

    # ── common_themes 축소 ──
    result["common_themes"] = []
    for theme in data.get("common_themes", []):
        filtered_theme = {
            "theme_name": theme.get("theme_name"),
            "category_pattern": theme.get("category_pattern"),
            "category_pattern_type": theme.get("category_pattern_type"),
        }

        # rankings: 전체 수치 유지 (positive_ratio, mention_count 등 전략 판단에 필수)
        filtered_theme["rankings"] = [
            {
                "rank": r.get("rank"),
                "product_id": r.get("product_id"),
                "product_name": r.get("product_name"),
                "mention_count": r.get("mention_count"),
                "positive_count": r.get("positive_count"),
                "negative_count": r.get("negative_count"),
                "positive_ratio": r.get("positive_ratio"),
                "insight_level": r.get("insight_level"),
            }
            for r in theme.get("rankings", [])
        ]

        # contradiction_pairs: 범용 함수로 quote 메타 축소
        filtered_theme["contradiction_pairs"] = [
            _filter_contradiction_pair(pair, "blueprint")
            for pair in theme.get("contradiction_pairs", [])
        ]

        # best_evidence: quote 메타 축소
        be = theme.get("best_evidence")
        if be is None:
            filtered_theme["best_evidence"] = None
        else:
            filtered_be = {}
            for key in ("first_place", "last_place"):
                entry = be.get(key)
                if entry is None:
                    filtered_be[key] = None
                else:
                    filtered_be[key] = {
                        "product_id": entry.get("product_id"),
                        "quote": _filter_quote(entry.get("quote"), "blueprint"),
                    }
            filtered_theme["best_evidence"] = filtered_be

        result["common_themes"].append(filtered_theme)

    # ── unique_strengths: best_quote만 축소, 나머지 전체 유지 ──
    result["unique_strengths"] = []
    for us in data.get("unique_strengths", []):
        filtered_us = {
            "product_id": us.get("product_id"),
            "theme_name": us.get("theme_name"),
            "positive_ratio": us.get("positive_ratio"),
            "mention_count": us.get("mention_count"),
            "why_unique": us.get("why_unique"),
            "recommended_use_case": us.get("recommended_use_case"),
            "best_quote": _filter_quote(us.get("best_quote"), "blueprint"),
        }
        result["unique_strengths"].append(filtered_us)

    # ── category_intelligence: 전체 유지 (Verdict 전략에 필수) ──
    result["category_intelligence"] = data.get("category_intelligence")
    if "analyst_notebook" in data:
        result["analyst_notebook"] = data["analyst_notebook"]

    return result


# ── Screen Profile ───────────────────────────────────────────────────────
# Data Screener Agent용 축소본 — quote 본문 불필요, 통계 메타데이터만 추출.
# 판단 기준은 ratio_gap과 mention_count.

def filter_for_screen(data: dict) -> dict:
    """
    category_candidates.json -> category_screen.json 축소본 생성.
    Data Screener Agent의 editorial judgment에 필요한 통계 메타데이터만 보존.

    포함 필드:
    - common_themes[]: theme_name, category_pattern_type,
      rankings (product_id, product_name, mention_count, positive_ratio),
      contradiction_pairs (type, product_id/product_ids, ratio_gap)
    - unique_strengths[]: product_id, theme_name, positive_ratio,
      mention_count, ratio_gap

    제거 필드:
    - products[], category_name, product_count, dataset_snapshot
    - quote 본문 전체 (text, review_id, star_rating 등)
    - best_evidence, resolution_hypothesis, category_intelligence
    """
    result = {}

    # ── common_themes: 통계 메타만 유지 ──
    result["common_themes"] = []
    for theme in data.get("common_themes", []):
        filtered_theme = {
            "theme_name": theme.get("theme_name"),
            "category_pattern_type": theme.get("category_pattern_type"),
        }

        # rankings: mention_count + positive_ratio (통계 신뢰도 판단용)
        filtered_theme["rankings"] = [
            {
                "product_id": r.get("product_id"),
                "product_name": r.get("product_name"),
                "mention_count": r.get("mention_count"),
                "positive_ratio": r.get("positive_ratio"),
            }
            for r in theme.get("rankings", [])
        ]

        # contradiction_pairs: type + product_ids + ratio_gap만 (quote 본문 완전 제거)
        filtered_theme["contradiction_pairs"] = []
        for pair in theme.get("contradiction_pairs", []):
            fp = {"type": pair.get("type")}
            if pair.get("type") == "within_product":
                fp["product_id"] = pair.get("product_id")
            else:
                fp["product_ids"] = pair.get("product_ids")
                fp["ratio_gap"] = pair.get("ratio_gap")
            filtered_theme["contradiction_pairs"].append(fp)

        result["common_themes"].append(filtered_theme)

    # ── unique_strengths: 통계 메타만 유지 ──
    result["unique_strengths"] = [
        {
            "product_id": us.get("product_id"),
            "theme_name": us.get("theme_name"),
            "positive_ratio": us.get("positive_ratio"),
            "mention_count": us.get("mention_count"),
            "ratio_gap": us.get("ratio_gap"),
        }
        for us in data.get("unique_strengths", [])
    ]

    return result


# ── Intelligence Profile ─────────────────────────────────────────────────
# Category Analyst Agent용 축소본 — category_pattern, resolution_hypothesis,
# why_unique, category_intelligence 작성에 필요한 컨텍스트 보존.

def filter_for_intelligence(data: dict) -> dict:
    """
    category_screened.json -> category_intelligence.json 축소본 생성.
    Category Analyst Agent의 qualitative writing에 필요한 데이터 보존.

    포함 필드:
    - products[]: product_id, product_name, sold_last_month, all_time_rating_avg,
      recent_review_rating_avg, population_gap, trap_candidate,
      needs_narrative_anchor, within_contradiction_themes
    - common_themes[]: theme_name, category_pattern_type,
      rankings (전체 통계), contradiction_pairs (quote text 보존)
    - unique_strengths[]: product_id, theme_name, positive_ratio, mention_count,
      is_exclusive_feature, best_quote (text 보존)

    제거 필드:
    - category_name, product_count, dataset_snapshot
    - quote의 review_date, helpful_count, has_media, media_info, selection_reason
    - best_evidence (Analyst가 직접 데이터에서 패턴 도출)
    """
    result = {}

    # ── products: narrative_anchor 체크 + maturity_assessment 작성에 필요 ──
    result["products"] = []
    for p in data.get("products", []):
        result["products"].append({
            "product_id": p.get("product_id"),
            "product_name": p.get("product_name"),
            "sold_last_month": p.get("sold_last_month"),
            "all_time_rating_avg": p.get("all_time_rating_avg"),
            "recent_review_rating_avg": p.get("recent_review_rating_avg"),
            "population_gap": p.get("population_gap"),
            "trap_candidate": p.get("trap_candidate"),
            "needs_narrative_anchor": p.get("needs_narrative_anchor", False),
            "within_contradiction_themes": p.get("within_contradiction_themes", []),
        })

    # ── common_themes: rankings 전체 + contradiction_pairs (quote text 보존) ──
    result["common_themes"] = []
    for theme in data.get("common_themes", []):
        filtered_theme = {
            "theme_name": theme.get("theme_name"),
            "category_pattern_type": theme.get("category_pattern_type"),
        }

        # rankings: 전체 통계 유지 (category_pattern 판단에 필수)
        filtered_theme["rankings"] = [
            {
                "product_id": r.get("product_id"),
                "product_name": r.get("product_name"),
                "mention_count": r.get("mention_count"),
                "positive_count": r.get("positive_count"),
                "negative_count": r.get("negative_count"),
                "positive_ratio": r.get("positive_ratio"),
            }
            for r in theme.get("rankings", [])
        ]

        # contradiction_pairs: 범용 함수로 quote text 보존 (hypothesis 작성에 맥락 필요)
        # intelligence 프로파일은 resolution_hypothesis가 아직 빈 상태이므로 범용 함수 사용
        filtered_theme["contradiction_pairs"] = [
            _filter_contradiction_pair(pair, "intelligence")
            for pair in theme.get("contradiction_pairs", [])
        ]

        result["common_themes"].append(filtered_theme)

    # ── unique_strengths: is_exclusive_feature + best_quote text 보존 ──
    result["unique_strengths"] = []
    for us in data.get("unique_strengths", []):
        result["unique_strengths"].append({
            "product_id": us.get("product_id"),
            "theme_name": us.get("theme_name"),
            "positive_ratio": us.get("positive_ratio"),
            "mention_count": us.get("mention_count"),
            "is_exclusive_feature": us.get("is_exclusive_feature", False),
            "best_quote": _filter_quote(us.get("best_quote"), "intelligence"),
        })

    return result


# ── Writer Agent Profile ────────────────────────────────────────────────────
# comparison_outline.json의 assigned_themes를 기준으로 필요한 테마만 추출.
# Writer는 quote text가 highlight_phrase 추출에 필수이므로 text는 반드시 보존.

DEFAULT_OUTLINE = os.path.join("data", "comparison_outline.json")


def _load_assigned_theme_names(outline_path: str) -> list[str]:
    """
    comparison_outline.json에서 scenes[].assigned_themes 목록을 수집.
    Writer가 실제로 narration을 작성해야 할 테마만 필터링하는 기준.
    """
    if not os.path.exists(outline_path):
        print(json.dumps({"error": f"Outline not found: {outline_path}"}),
              file=sys.stderr)
        sys.exit(1)

    with open(outline_path, "r", encoding="utf-8") as f:
        outline = json.load(f)

    themes = set()
    for scene in outline.get("scenes", []):
        for t in scene.get("assigned_themes", []):
            themes.add(t)
    return list(themes)


def filter_for_writer(data: dict, outline_path: str = None) -> dict:
    """
    category_analysis.json -> category_writer.json 축소본 생성.

    핵심 전략: comparison_outline.json의 assigned_themes 목록을 기준으로
    해당 테마만 필터링하여 excluded 테마 데이터를 완전 제거.
    Writer는 quote text가 highlight_phrase 추출에 필수이므로 text는 반드시 보존.

    포함 필드:
    - category_name (output 복사에 필요)
    - products[]: product_id, product_name, sold_last_month, all_time_rating_avg,
      all_time_rating_count, recent_review_rating_avg, recent_review_count,
      population_gap, reviews_analyzed_count, trap_candidate (is_trap + reason만)
    - common_themes[] (assigned_themes만): theme_name, category_pattern,
      category_pattern_type, rankings (rank/insight_level 제외),
      contradiction_pairs (quote text 보존, 메타 축소),
      best_evidence (quote text 보존, 메타 축소)
    - unique_strengths[]: 전체 (Standout scene에 필요)
    - category_intelligence: 전체 (Verdict scene에 필수)

    제거 필드:
    - dataset_snapshot, previous_snapshot, delta, product_count
    - products[].product_category, summary_path, recent_period_text

    - products[].trap_candidate.signals
    - excluded 테마의 전체 데이터
    - rankings[].rank, insight_level (순위 노출 금지 원칙)
    - quote별: review_date, helpful_count, has_media, media_info (sentiment는 보존)
    """
    # Outline에서 할당된 테마명 로드
    ol_path = outline_path or DEFAULT_OUTLINE
    assigned_names = _load_assigned_theme_names(ol_path)
    assigned_set = set(assigned_names)

    result = {}

    # ── category_name (output에 복사 필요) ──
    result["category_name"] = data.get("category_name")

    # ── products 축소: Writer가 Category Rating Overview에서 필요한 핵심 필드만 ──
    result["products"] = []
    for p in data.get("products", []):
        result["products"].append({
            "product_id": p.get("product_id"),
            "product_name": p.get("product_name"),
            "sold_last_month": p.get("sold_last_month"),
            "all_time_rating_avg": p.get("all_time_rating_avg"),
            "all_time_rating_count": p.get("all_time_rating_count"),
            "recent_review_rating_avg": p.get("recent_review_rating_avg"),
            "recent_review_count": p.get("recent_review_count"),
            "recent_days": p.get("recent_days"),
            "population_gap": p.get("population_gap"),
            "reviews_analyzed_count": p.get("reviews_analyzed_count"),
            "trap_candidate": {
                "is_trap": p.get("trap_candidate", {}).get("is_trap"),
                "reason": p.get("trap_candidate", {}).get("reason"),
            },
        })

    # ── common_themes: assigned_themes에 해당하는 것만 필터링 ──
    result["common_themes"] = []
    for theme in data.get("common_themes", []):
        if theme.get("theme_name") not in assigned_set:
            continue  # excluded 테마 완전 스킵

        filtered_theme = {
            "theme_name": theme.get("theme_name"),
            "category_pattern": theme.get("category_pattern"),
            "category_pattern_type": theme.get("category_pattern_type"),
        }

        # rankings: rank와 insight_level 제거 (순위 노출 금지)
        filtered_theme["rankings"] = [
            {
                "product_id": r.get("product_id"),
                "product_name": r.get("product_name"),
                "mention_count": r.get("mention_count"),
                "positive_count": r.get("positive_count"),
                "negative_count": r.get("negative_count"),
                "positive_ratio": r.get("positive_ratio"),
            }
            for r in theme.get("rankings", [])
        ]

        # contradiction_pairs: 범용 함수로 quote text 보존, 불필요 메타 제거
        filtered_theme["contradiction_pairs"] = [
            _filter_contradiction_pair(pair, "writer")
            for pair in theme.get("contradiction_pairs", [])
        ]

        # best_evidence: quote text 보존, 메타 축소
        be = theme.get("best_evidence")
        if be:
            filtered_be = {}
            for key in ("first_place", "last_place"):
                entry = be.get(key)
                if entry:
                    filtered_be[key] = {
                        "product_id": entry.get("product_id"),
                        "quote": _filter_quote(entry.get("quote"), "writer"),
                    }
            filtered_theme["best_evidence"] = filtered_be

        result["common_themes"].append(filtered_theme)

    # ── unique_strengths: best_quote의 text 보존, 불필요 메타 축소 ──
    result["unique_strengths"] = []
    for us in data.get("unique_strengths", []):
        result["unique_strengths"].append({
            "product_id": us.get("product_id"),
            "theme_name": us.get("theme_name"),
            "positive_ratio": us.get("positive_ratio"),
            "mention_count": us.get("mention_count"),
            "why_unique": us.get("why_unique"),
            "recommended_use_case": us.get("recommended_use_case"),
            "best_quote": _filter_quote(us.get("best_quote"), "writer"),
        })

    # ── category_intelligence: 전체 유지 (Verdict에 필수) ──
    result["category_intelligence"] = data.get("category_intelligence")
    if "analyst_notebook" in data:
        result["analyst_notebook"] = data["analyst_notebook"]

    return result


# ── Validator Profile ───────────────────────────────────────────────────────

def filter_for_validator(data: dict) -> dict:
    """
    category_analysis.json -> category_validator.json 축소본 생성.
    Data Validator는 리뷰의 모든 수치와 메타를 검증하므로 데이터는 유지하되
    최소한으로 불필요한 필드만 제거한다.
    """
    result = {}

    result["category_name"] = data.get("category_name")
    result["product_count"] = data.get("product_count")

    result["products"] = []
    for p in data.get("products", []):
        result["products"].append({
            "product_id": p.get("product_id"),
            "product_name": p.get("product_name"),
            "sold_last_month": p.get("sold_last_month"),
            "all_time_rating_avg": p.get("all_time_rating_avg"),
            "all_time_rating_count": p.get("all_time_rating_count"),
            "recent_review_rating_avg": p.get("recent_review_rating_avg"),
            "recent_review_count": p.get("recent_review_count"),
            "population_gap": p.get("population_gap"),
            "reviews_analyzed_count": p.get("reviews_analyzed_count"),
            "trap_candidate": p.get("trap_candidate"),
        })

    result["common_themes"] = []
    for theme in data.get("common_themes", []):
        filtered_theme = {
            "theme_name": theme.get("theme_name"),
            # category_pattern(자연어 긴 본문)는 Validator 검증에 불필요하여 제거, 
            # 단 수치 검증에 필요한 필드는 전부 유지
            "category_pattern_type": theme.get("category_pattern_type"),
        }

        filtered_theme["rankings"] = [
            {
                "product_id": r.get("product_id"),
                "product_name": r.get("product_name"),
                "mention_count": r.get("mention_count"),
                "positive_count": r.get("positive_count"),
                "negative_count": r.get("negative_count"),
                "positive_ratio": r.get("positive_ratio"),
            }
            for r in theme.get("rankings", [])
        ]

        filtered_theme["contradiction_pairs"] = [
            _filter_contradiction_pair(pair, "validator")
            for pair in theme.get("contradiction_pairs", [])
        ]

        be = theme.get("best_evidence")
        if be:
            filtered_be = {}
            for key in ("first_place", "last_place"):
                entry = be.get(key)
                if entry:
                    filtered_be[key] = {
                        "product_id": entry.get("product_id"),
                        "quote": _filter_quote(entry.get("quote"), "validator"),
                    }
            filtered_theme["best_evidence"] = filtered_be

        result["common_themes"].append(filtered_theme)

    result["unique_strengths"] = []
    for us in data.get("unique_strengths", []):
        result["unique_strengths"].append({
            "product_id": us.get("product_id"),
            "theme_name": us.get("theme_name"),
            "positive_ratio": us.get("positive_ratio"),
            "mention_count": us.get("mention_count"),
            "why_unique": us.get("why_unique"),
            "best_quote": _filter_quote(us.get("best_quote"), "validator"),
        })

    # category_intelligence 전체 유지 (문맥 파악 및 수치 존재 가능성)
    result["category_intelligence"] = data.get("category_intelligence")
    if "analyst_notebook" in data:
        result["analyst_notebook"] = data["analyst_notebook"]

    return result


# ── 프로파일 -> 필터 함수 매핑 ───────────────────────────────────────────────
FILTER_FUNCTIONS = {
    "blueprint": filter_for_blueprint,
    "screen": filter_for_screen,
    "intelligence": filter_for_intelligence,
    "writer": filter_for_writer,
    "validator": filter_for_validator,
}


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: Filter category_analysis.json for agent-specific profiles"
    )
    parser.add_argument(
        "--profile", required=True, choices=list(PROFILES.keys()),
        help="에이전트 프로파일명"
    )
    parser.add_argument(
        "--input", default=DEFAULT_INPUT,
        help=f"입력 category_analysis.json 경로 (기본: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "--output", default=None,
        help="출력 경로 (기본: data/category_{profile}.json)"
    )
    parser.add_argument(
        "--outline", default=DEFAULT_OUTLINE,
        help=f"comparison_outline.json 경로 (writer 프로파일 전용, "
             f"기본: {DEFAULT_OUTLINE})"
    )
    args = parser.parse_args()

    # 기본 출력 경로: data/category_{profile}.json
    if args.output is None:
        suffix = PROFILES[args.profile]["output_suffix"]
        args.output = os.path.join("data", f"category_{suffix}.json")

    # 입력 파일 확인
    if not os.path.exists(args.input):
        print(json.dumps({"error": f"File not found: {args.input}"}))
        sys.exit(1)

    # 데이터 로드
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 프로파일별 필터 적용
    filter_fn = FILTER_FUNCTIONS[args.profile]
    # writer 프로파일은 outline_path 인자가 필요
    if args.profile == "writer":
        filtered = filter_fn(data, outline_path=args.outline)
    else:
        filtered = filter_fn(data)

    # 출력 디렉토리 생성 (없으면)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    # 저장
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    # ── 실행 결과 요약 (machine-parseable) ──
    original_size = os.path.getsize(args.input)
    filtered_json = json.dumps(filtered, ensure_ascii=False, indent=2)
    filtered_size = len(filtered_json.encode("utf-8"))
    reduction = round(100 * (1 - filtered_size / original_size), 1)

    print(json.dumps({
        "profile": args.profile,
        "input": args.input,
        "output": args.output,
        "original_bytes": original_size,
        "filtered_bytes": filtered_size,
        "reduction_pct": reduction,
    }), file=sys.stdout)

    print(
        f"[filter_category] {args.profile}: "
        f"{original_size:,} -> {filtered_size:,} bytes "
        f"({reduction}% reduction)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
